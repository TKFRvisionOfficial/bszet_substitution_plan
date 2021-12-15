import requests
import json

with open(r"C:\Users\tkfrv\Downloads\nur_bilder.pdf", "rb") as file:
	response_text = requests.post("***REMOVED***", files={'file': file}, headers={"Authorization": "Bearer ***REMOVED***"}).content.decode("utf-8")

print(response_text)
