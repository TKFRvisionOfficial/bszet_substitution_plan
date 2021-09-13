import pdf2image
from PIL import Image, ImageDraw, ImageFont
import io
from uuid import uuid4
from typing import List
import os

_FONT = ImageFont.truetype("fonts/JetBrainsMono-Bold.ttf", 100)
_FONT_SMALL = ImageFont.truetype("fonts/JetBrainsMono-Bold.ttf", 50)
_BSZET_ORANGE = (238, 104, 35)


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


def create_cover_sheet(path: str, top: str = None, top2: str = None, bottom: str = None) -> str:
    img = Image.new('RGB', (1280, 904), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.line((150, 489, 1140, 489), fill=_BSZET_ORANGE, width=30)
    draw.text((640, 325), top if top else "", anchor="mm", font=_FONT, fill=_BSZET_ORANGE)
    draw.text((640, 420), top2 if top2 else "", anchor="mm", font=_FONT_SMALL, fill=_BSZET_ORANGE)
    draw.text((640, 589), bottom if bottom else "", anchor="mm", font=_FONT, fill=_BSZET_ORANGE)

    uuid = str(uuid4())
    img.save(os.path.join(path, uuid + ".jpg"))
    return uuid
