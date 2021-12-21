import io
import json
import os
import tempfile
from typing import List, Tuple, Any, Union, NamedTuple, Generator
from uuid import uuid4

import camelot
import cv2
import numpy as np
import pdf2image
from PIL import Image, ImageDraw, ImageFont
from PyPDF2 import PdfFileReader, PdfFileWriter
from pandas import DataFrame
from starlette.responses import JSONResponse

from img_to_dataframe import convert_table_img_to_list
from pdf_parsing import parse_date

_FONT_PATH = r"fonts/Anton-Regular.ttf"
_FONT = ImageFont.truetype(_FONT_PATH, 80)
_FONT_SMALL = ImageFont.truetype(_FONT_PATH, 30)
_BSZET_ORANGE = (238, 104, 35)
_BSZET_GREY = (130, 129, 125)


class _NothingFound(Exception):
    pass


def convert_pdf_to_img(pdf: bytes) -> bytes:
    images = pdf2image.convert_from_bytes(pdf, 200)

    widths, heights = zip(*(i.size for i in images))
    max_width = max(widths)
    total_height = sum(heights)
    result_img = Image.new('RGB', (max_width, total_height))

    y_offset = 0
    for image in images:
        result_img.paste(image, (0, y_offset))
        y_offset += image.size[1]

    # annoying workaround
    with io.BytesIO() as byte_array:
        result_img.save(byte_array, format="JPEG", dpi=(200, 200), quality=90)
        return byte_array.getvalue()


def convert_pdf_to_opencv(pdf: bytes, dpi: int = 200) -> List[np.ndarray]:
    images = pdf2image.convert_from_bytes(pdf, dpi)
    return [cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR) for image in images]


def save_pdf_to_folder(pdf: bytes, path: str) -> List[str]:
    if not os.path.exists(path):
        os.mkdir(path)
    uuid_list = []
    images = pdf2image.convert_from_bytes(pdf, 200)
    for image in images:
        cur_uuid = str(uuid4())
        uuid_list.append(cur_uuid)
        image.save(os.path.join(path, cur_uuid + ".jpg"), dpi=(200, 200), quality=90)
    return uuid_list


def create_cover_sheet(path: str = ".", top1: str = None, top2: str = None, bottom: str = None,
                       size_image: Tuple[int, int] = (1280, 904), width_line: int = 30,
                       text_margin: int = 15, border_margin: int = 50) -> str:
    # not using getsize because it measures size from ascender line and not from height to top
    top_size = _FONT.getbbox(top1, anchor="lt")[2:]
    top2_size = _FONT_SMALL.getbbox(top2, anchor="lt")[2:]
    bottom_size = _FONT.getbbox(bottom, anchor="lt")[2:]

    center_image = (size_image[0]/2, size_image[1]/2)
    # the length between the line and the border of the image
    length_to_border_line = (size_image[0]-max(top_size[0], top2_size[0], bottom_size[0]))/2-border_margin
    line_cords = (length_to_border_line, center_image[1], size_image[0]-length_to_border_line, center_image[1])
    top2_text_cords = (center_image[0], line_cords[1]-width_line/2-text_margin)
    top1_text_cords = (center_image[0], top2_text_cords[1]-top2_size[1]-text_margin)
    bottom_text_cords = (center_image[0], line_cords[1]+width_line/2+text_margin)

    img = Image.new('RGB', size_image, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.line(line_cords, fill=_BSZET_ORANGE, width=width_line)
    # anchor documentation: https://pillow.readthedocs.io/en/stable/handbook/text-anchors.html
    draw.text(top1_text_cords, top1 if top1 else "", anchor="ms", font=_FONT, fill=_BSZET_ORANGE)
    draw.text(top2_text_cords, top2 if top2 else "", anchor="ms", font=_FONT_SMALL, fill=_BSZET_GREY)
    draw.text(bottom_text_cords, bottom if bottom else "", anchor="mt", font=_FONT, fill=_BSZET_ORANGE)

    uuid = str(uuid4())
    img.save(os.path.join(path, uuid + ".jpg"))
    return uuid


def convert_pdf_to_dataframes(pdf: bytes, row_tol: int) -> Union[List[DataFrame], None]:
    # i dont know if this is the right way of doing this
    # the uploadfile object contains a file parameter which is a spooledtemporaryfile
    # maybe there is some better way of converting the spooledtemporaryfile to a namedtemporaryfile
    data_frames = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf)
    try:
        with io.BytesIO(pdf) as pdf_stream:
            for page_num in range(1, PdfFileReader(pdf_stream).getNumPages()+1):
                try:
                    parsed_tables = camelot.read_pdf(
                        tmp_file.name,
                        pages=str(page_num),
                        flavor="stream",
                        row_tol=row_tol,  # not perfect. issues often fixable here
                        table_areas=["30,480,790,100"]  # is the area big enough?
                    )
                    if len(parsed_tables) == 0:
                        raise _NothingFound
                    tables = [parsed_table.df for parsed_table in parsed_tables]
                    data_frames.extend(tables)
                except Exception:
                    # ToDo: test exception with table from 2nd school week
                    data_frames.extend(convert_pdf_to_dataframes_fallback(pdf, page_num-1))

    finally:
        os.remove(tmp_file.name)

    return data_frames


def convert_pdf_to_dataframes_fallback(pdf: bytes, page: int) -> Union[List[DataFrame], None]:
    # ToDo: Converting the data every time is inefficent.
    opencv_images = convert_pdf_to_opencv(pdf, 205)  # 96
    img = opencv_images[page]
    return [convert_table_img_to_list(img)]


class _ResultPdfPage(NamedTuple):
    date_str: str
    pdf_data: bytes


def separate_pdf_into_days(pdf: bytes, row_tol: int) -> Generator[_ResultPdfPage, None, None]:
    class PdfPageDate(NamedTuple):
        date_str: str
        pdf_page_num_range: Tuple[int, int]

    data_frames = convert_pdf_to_dataframes(pdf, row_tol)
    if data_frames is None:
        raise ValueError

    date = parse_date(data_frames[0][0])
    if date is None:
        raise ValueError

    dates: List[PdfPageDate] = []
    start_page_index = 0

    # we could make a generator out of this but i don't think it needs it...
    for page_index, pdf_page in enumerate(data_frames[1:]):
        new_date = parse_date(pdf_page)  # let's hope this doesn't produce wrong results
        if new_date is not None:
            dates.append(PdfPageDate(date, (start_page_index, page_index)))
            start_page_index = page_index
    dates.append(PdfPageDate(date, (start_page_index, len(data_frames))))

    with io.BytesIO(pdf) as pdf_input:
        pdf_reader = PdfFileReader(pdf_input)

        for pdf_page_date in dates:
            with io.BytesIO() as pdf_output:
                pdf_writer = PdfFileWriter()
                for page_num in range(*pdf_page_date.pdf_page_num_range):
                    pdf_writer.addPage(pdf_reader.getPage(page_num))
                pdf_writer.write(pdf_output)
                yield _ResultPdfPage(date, pdf_output.getvalue())


class ToDictEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return json.JSONEncoder.default(self, obj)


class ToDictJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            sort_keys=False,  # i don't like sorting things 😂
            separators=(",", ":"),
            cls=ToDictEncoder
        ).encode("utf-8")
