import asyncio
import aiohttp
from _secrets import *
import pdf2image
from typing import Iterable
from PIL import Image
import io


def combine_and_convert_images(images: Iterable[Image.Image]) -> bytes:
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
	result_img.save(byte_array, format="JPEG")
	return byte_array.getvalue()


async def main():
	async with aiohttp.ClientSession() as session:
		async with session.get(
				"http://geschuetzt.bszet.de/s-lk-vw/Vertretungsplaene/vertretungsplan-bgy.pdf",
				auth=aiohttp.BasicAuth(BSZET_USERNAME, BSZET_PASSWORD)) as substitution_response:
			fd = aiohttp.FormData()
			# maybe memory leak? async implemented properly?
			imgs = pdf2image.convert_from_bytes(await substitution_response.read(), 200)
			fd.add_field("photo", combine_and_convert_images(imgs))
			async with session.get(
				f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendPhoto",
				params={"chat_id": CHAT_ID},
				data=fd
			) as telegram_response:
				print(await telegram_response.text())


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
