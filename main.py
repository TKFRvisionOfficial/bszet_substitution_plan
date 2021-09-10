import asyncio
import aiohttp
from _secrets import *


async def main():
	async with aiohttp.ClientSession() as session:
		while True:
			async with session.get(
					"http://geschuetzt.bszet.de/s-lk-vw/Vertretungsplaene/vertretungsplan-bgy.pdf",
					auth=aiohttp.BasicAuth(BSZET_USERNAME, BSZET_PASSWORD)) as substitution_response:
				fd = aiohttp.FormData()
				# maybe memory leak? async implemented properly?
				fd.add_field("document", await substitution_response.read(), filename="shit.pdf", content_type="application/pdf")
				async with session.get(
					f"https://api.telegram.org/bot{TELEGRAM_API_TOKEN}/sendDocument",
					params={"chat_id": CHAT_ID},
					data=fd
				) as telegram_response:
					print(await telegram_response.text())
			await asyncio.sleep(30*60)


if __name__ == '__main__':
	loop = asyncio.get_event_loop()
	loop.run_until_complete(main())
