import pdf2image
from PIL import Image, ImageDraw, ImageFont
import io
from uuid import uuid4
from typing import List, Tuple
import os

_FONT_PATH = r"fonts/Anton-Regular.ttf"
_FONT = ImageFont.truetype(_FONT_PATH, 80)
_FONT_SMALL = ImageFont.truetype(_FONT_PATH, 30)
_BSZET_ORANGE = (238, 104, 35)
_BSZET_GREY = (130, 129, 125)


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
