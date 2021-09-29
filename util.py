import tempfile
import camelot
import pdf2image
from PIL import Image, ImageDraw, ImageFont
from starlette.responses import JSONResponse
import io
from uuid import uuid4
from typing import List, Tuple, Any, Union
from pandas import DataFrame
import os
import json
import numpy as np
import cv2
from PyPDF2 import PdfFileReader

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
    byte_array = io.BytesIO()
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


def convert_pdf_to_dataframes(pdf: bytes) -> Union[List[DataFrame], None]:
    # i dont know if this is the right way of doing this
    # the uploadfile object contains a file parameter which is a spooledtemporaryfile
    # maybe there is some better way of converting the spooledtemporaryfile to a namedtemporaryfile
    tables = []
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(pdf)
    try:
        for page_num in range(1, PdfFileReader(io.BytesIO(pdf)).getNumPages()+1):
            try:
                parsed_tables = camelot.read_pdf(
                    tmp_file.name,
                    pages=str(page_num),
                    flavor="stream",
                    row_tol=22,  # not perfect. issues often fixable here
                    table_areas=["30,480,790,100"]  # is the area big enough?
                )
                if len(parsed_tables) == 0:
                    raise _NothingFound
                tables.extend(parsed_tables)
            except Exception:
                continue  # need a way of informing of failure + fallback
    finally:
        os.remove(tmp_file.name)

    data_frames = [table.df for table in tables]
    return data_frames


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
