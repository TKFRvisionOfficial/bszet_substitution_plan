FROM python:3.9-slim

WORKDIR /tmp/fonts
RUN apt update \
 && apt install -y g++ poppler-utils libfreetype-dev zlib1g-dev libjpeg-dev curl unzip \
 && python -m pip install --upgrade pip setuptools wheel \
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