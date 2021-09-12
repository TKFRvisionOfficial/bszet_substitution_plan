from typing import Optional
from fastapi import FastAPI, UploadFile, File, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTasks
from util import save_pdf_to_folder
import os

auth_key = f'Bearer {os.environ["AUTH_KEY"]}'
image_path = "pictures"
app = FastAPI()


@app.post("/pdf2img")
async def read_item(request: Request, file: UploadFile = File(...)):
    # if True:
    if request.headers.get("Authorization") == auth_key:
        uuids = save_pdf_to_folder(await file.read(), image_path)
        return JSONResponse(content=uuids,  status_code=200)
    else:
        return Response(content="Forbidden", status_code=403)


@app.get("/img/{uuid}")
async def get_file(uuid: str, request: Request, background_task: BackgroundTasks):
    # if True:
    if request.headers.get("Authorization") == auth_key:
        file_path = os.path.join(image_path, uuid + ".jpg")
        if os.path.exists(file_path):
            background_task.add_task(os.remove, file_path)
            return FileResponse(path=file_path, media_type="image/jpeg", status_code=200)
        else:
            return Response(content="Not Found", status_code=404)
    else:
        return Response(content="Forbidden", status_code=403)

