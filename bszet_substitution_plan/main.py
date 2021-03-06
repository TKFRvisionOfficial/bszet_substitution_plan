#  bszet_substitution_plan
#  Copyright (C) 2022 TKFRvision, PBahner, MarcelCoding
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import os
from datetime import datetime
from glob import glob
from typing import Iterable, Optional

import sentry_sdk
from fastapi import FastAPI, UploadFile, File, Response, Request, Header, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.background import BackgroundTasks
from starlette.exceptions import HTTPException as StarletteHTTPException

from bszet_substitution_plan.pdf_parsing import parse_dataframes
from bszet_substitution_plan.util import save_pdf_to_folder, create_cover_sheet, separate_pdf_into_days, \
    convert_pdf_to_dataframes, \
    ToDictJSONResponse

# import tempfile


auth_key = f'Bearer {os.environ["AUTH_KEY"]}'
row_tol = int(os.environ.get("ROW_TOL", 20))
image_path = os.environ["IMAGE_PATH"]
pdf_archive_path = os.environ["PDF_ARCHIVE_PATH"]

if not os.path.exists(pdf_archive_path):
    os.mkdir(pdf_archive_path)

if not os.path.exists(image_path):
    os.mkdir(image_path)
else:
    for _file in glob(os.path.join(image_path, "*.jpg")):
        os.remove(_file)


async def verify_authorization(authorization: Optional[str] = Header(None)):
    if authorization != auth_key:
        raise HTTPException(403, "Forbidden")


app = FastAPI(dependencies=(Depends(verify_authorization),))

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],  # CHANGE HERE
        environment=os.getenv('ENV', 'dev'),  # You should read it from environment variable
    )

    try:
        app.add_middleware(SentryAsgiMiddleware)
    except Exception:
        # pass silently if the Sentry integration failed
        pass


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exception: StarletteHTTPException):
    return PlainTextResponse(str(exception.detail), status_code=exception.status_code)


async def remove_later(uuids: Iterable[str]):
    await asyncio.sleep(600)  # delete file after 10 minutes
    for uuid in uuids:
        file_path = os.path.join(image_path, uuid + ".jpg")
        if os.path.exists(file_path):
            os.remove(file_path)


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
    return JSONResponse(content=uuids, status_code=200)


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
    return JSONResponse([df.to_dict() for df in convert_pdf_to_dataframes(await file.read(), row_tol)])


@app.post("/parse-pdf")
async def parse_pdf(file: UploadFile = File(...)):
    dfs = convert_pdf_to_dataframes(await file.read(), row_tol)
    if dfs is None:
        return Response("Parsing Failure", status_code=422)
    return ToDictJSONResponse(parse_dataframes(dfs))


@app.post("/store-pdf")
async def store_pdf(file: UploadFile = File(...)):
    data = await file.read()
    try:
        for pdf_files in separate_pdf_into_days(data, row_tol):
            with open(os.path.join(pdf_archive_path, pdf_files.date_str + ".pdf"), "wb") as backup_file:
                backup_file.write(pdf_files.pdf_data)
        return JSONResponse({
            "status": "OK",
            "message": None
        })
    except ValueError:
        # maybe add time?
        with open(os.path.join(pdf_archive_path, datetime.now().strftime("failure_%Y-%m-%d") + ".pdf"), "wb") \
                as backup_file:
            backup_file.write(data)
            return JSONResponse({
                "status": "WARN",
                "message": "The date of the PDF could not be parsed. Storing full pdf..."
            })
