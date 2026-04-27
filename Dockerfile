FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    GIFSICLE_PATH=/usr/bin/gifsicle

# gifsicle is required by utils/image_utils.py for GIF compression.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gifsicle \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --prefer-binary --no-compile -r /app/requirements.txt

COPY . /app

CMD ["python", "main.py"]
