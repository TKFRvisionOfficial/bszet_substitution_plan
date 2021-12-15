import requests
import json

with open(r"C:\Users\tkfrv\Downloads\vertretungsplan-bgy06122021.pdf", "rb") as file:
	response_text = requests.post("http://127.0.0.1:8000/parse-pdf", files={'file': file}, headers={"Authorization": "Bearer 123"}).content.decode("utf-8")

print(response_text)
