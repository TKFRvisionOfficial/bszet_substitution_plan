FROM python:3.9-slim

WORKDIR /tmp/fonts
RUN apt-get update \
 && apt-get install -y g++ poppler-utils libfreetype-dev zlib1g-dev libjpeg-dev ffmpeg libsm6 libxext6 libgl1-mesa-glx curl unzip \
 && python -m pip install --upgrade --no-cache-dir pip setuptools wheel \
 && curl -fsSLo Anton.zip https://fonts.google.com/download?family=Anton \
 && unzip Anton.zip \
 && apt-get purge -y curl unzip \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /app/fonts \
 && mv Anton-Regular.ttf /app/fonts/Anton-Regular.ttf \
 && rm -rf /tmp/fonts

WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY util.py .
COPY pdf_converter.py .
COPY pdf_parsing.py .
COPY img_to_dataframe.py .
EXPOSE 8000

ENTRYPOINT [ "uvicorn", "pdf_converter:app", "--port", "8000", "--host", "0.0.0.0" ]
