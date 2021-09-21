from typing import Iterable
from fastapi import FastAPI, UploadFile, File, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from starlette.background import BackgroundTasks
from util import save_pdf_to_folder, create_cover_sheet, convert_pdf_to_dataframes, ToDictJSONResponse
from pdf_parsing import parse_dataframes
import os
from glob import glob
import asyncio
# import tempfile


auth_key = f'Bearer {os.environ["AUTH_KEY"]}'
image_path = "pictures"

if not os.path.exists(image_path):
    os.mkdir(image_path)
else:
    for _file in glob(os.path.join(image_path, "*.jpg")):
        os.remove(_file)

app = FastAPI()


async def remove_later(uuids: Iterable[str]):
    await asyncio.sleep(600)  # delete file after 10 minutes
    for uuid in uuids:
        file_path = os.path.join(image_path, uuid + ".jpg")
        if os.path.exists(file_path):
            os.remove(file_path)


@app.middleware("http")
async def check_authorization(request: Request, call_next):
    if request.headers.get("Authorization") == auth_key:
        return await call_next(request)
    else:
        return Response(content="Forbidden", status_code=403)


@app.post("/pdf2img")
async def pdf2image(request: Request, background_task: BackgroundTasks, file: UploadFile = File(...)):
    # if True:
    uuids = save_pdf_to_folder(await file.read(), image_path)
    uuids.insert(0, create_cover_sheet(
        image_path,
        request.query_params.get("top-text", None),
        request.query_params.get("top2-text", None),
        request.query_params.get("bottom-text", None)
    ))
    background_task.add_task(remove_later, uuids)
    return JSONResponse(content=uuids,  status_code=200)


@app.get("/img/{uuid}")
async def get_file(uuid: str, background_task: BackgroundTasks):
    # if True:
    file_path = os.path.join(image_path, uuid + ".jpg")
    if os.path.exists(file_path):
        background_task.add_task(os.remove, file_path)
        return FileResponse(path=file_path, media_type="image/jpeg", status_code=200)
    else:
        return Response(content="Not Found", status_code=404)


@app.post("/pdf2json")
async def convert_to_json(background_task: BackgroundTasks, file: UploadFile = File(...)):
    # with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
    #     tmp_file.write(file.file.read())  # maybe read and write in chunks?!
    # try:
    #     tables = camelot.read_pdf(tmp_file.name, flavor="stream", row_tol=30, pages="all")
    #     response = [table.data for table in tables]
    # finally:
    #     background_task.add_task(os.remove, tmp_file.name)
    return JSONResponse([df.to_dict() for df in convert_pdf_to_dataframes(await file.read())])


@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    dfs = convert_pdf_to_dataframes(await file.read())
    if dfs is None:
        return Response("Parsing Failure", status_code=422)
    return ToDictJSONResponse(parse_dataframes(dfs))
