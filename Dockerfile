# syntax=docker/dockerfile:1.6
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app

COPY server/requirements.txt /opt/app/server/requirements.txt
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --no-cache-dir -r server/requirements.txt

COPY . /opt/app

RUN python3 scripts/download_drawing_spinup_assets.py

ENV DATA_ROOT=/data \
    DRAWING_SPINUP_ROOT=/opt/app/DrawingSpinUp \
    SERVER_GPU_IDS=""

VOLUME ["/data"]

EXPOSE 8080

CMD ["uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
