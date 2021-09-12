from typing import Optional
from fastapi import FastAPI, UploadFile, File, Response, Request
from util import convert_pdf_to_img
import os

auth_key = f'Bearer {os.environ["AUTH_KEY"]}'
app = FastAPI()


@app.post("/pdf2img")
async def read_item(request: Request, file: UploadFile = File(...)):
    if request.headers.get("Authorization") == auth_key:
        image = convert_pdf_to_img(await file.read())
        return Response(content=image, media_type="image/jpeg", status_code=200)
    else:
        return Response(content="Forbidden", status_code=403)
