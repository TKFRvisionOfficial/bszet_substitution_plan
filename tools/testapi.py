import requests
import json

with open(r"C:\Users\tkfrv\Downloads\nur_bilder.pdf", "rb") as file:
	response_text = requests.post("URL", files={'file': file}, headers={"Authorization": "Bearer API_KEY"}).content.decode("utf-8")

print(response_text)
