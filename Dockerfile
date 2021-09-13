FROM python:3.9-alpine

WORKDIR /tmp/fonts
RUN apk add --update --no-cache g++ poppler-utils freetype-dev zlib-dev libjpeg-turbo-dev curl unzip \
 && curl -fsSLo jetbrains-mono.zip https://github.com/JetBrains/JetBrainsMono/releases/download/v2.242/JetBrainsMono-2.242.zip \
 && unzip jetbrains-mono.zip \
 && apk del curl unzip \
 && mkdir /app \
 && mv /tmp/fonts/fonts/ttf/JetBrainsMono-Bold.ttf /app/fonts/JetBrainsMono-Bold.ttf \
 && rm -rf /tmp/fonts

WORKDIR /app
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY util.py .
COPY pdf_converter.py .
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "pdf_converter:app", "--port", "8000", "--host", "0.0.0.0" ]