FROM python:3.9-alpine

RUN apk add --update --no-cache g++ poppler zlib-dev libjpeg-turbo-dev

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "pdf_converter:app", "--port", "8000", "--host", "0.0.0.0" ]