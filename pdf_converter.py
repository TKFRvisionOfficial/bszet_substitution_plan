from typing import Optional
from fastapi import FastAPI, UploadFile, File, Response
from util import convert_pdf_to_img

app = FastAPI()


@app.post("/pdf2img")
async def read_item(file: UploadFile = File(...)):
    image = convert_pdf_to_img(await file.read())
    return Response(content=image, media_type="image/jpeg")
