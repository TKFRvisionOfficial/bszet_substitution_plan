FROM python:3.9-alpine

WORKDIR /tmp/fonts
RUN apk add --update --no-cache g++ poppler-utils freetype-dev zlib-dev libjpeg-turbo-dev curl unzip \
 && curl -fsSLo Anton.zip https://fonts.google.com/download?family=Anton \
 && unzip Anton.zip \
 && apk del curl unzip \
 && mkdir -p /app/fonts \
 && mv Anton-Regular.ttf /app/fonts/Anton-Regular.ttf \
 && rm -rf /tmp/fonts

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY util.py .
COPY pdf_converter.py .
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "pdf_converter:app", "--port", "8000", "--host", "0.0.0.0" ]