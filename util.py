import pdf2image
from PIL import Image
import io


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
