# 역할: 서비스의 Python·Blender 의존성과 실행 이미지를 구성합니다.
FROM ubuntu:24.04 AS blender-download
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
RUN curl -fSL --retry 3 https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz -o blender.tar.xz \
    && echo '4da1c956673c0485e63054e563ee69198cc8f80d8157dd7592dffc8a6a5592e6  blender.tar.xz' | sha256sum -c - \
    && mkdir -p /opt/blender \
    && tar -xJf blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm blender.tar.xz

FROM ubuntu:24.04 AS common
COPY architecture/install-odbc.sh /tmp/install-odbc.sh
RUN sh /tmp/install-odbc.sh && rm /tmp/install-odbc.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates python3-venv libx11-6 libxrender1 libxfixes3 libxi6 \
    libxkbcommon0 libsm6 libice6 libgl1 libxxf86vm1 libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=blender-download /opt/blender /opt/blender
ENV BLENDER_BIN=/opt/blender/blender \
    GARMENT_TEMPLATE_DIR=/models/garments \
    GARMENT_MODELS_MANIFEST=/opt/fitme/bundled_garments.json \
    GARMENT_MODEL_CACHE_DIR=/models/cache \
    GARMENT_MODELS_ACCOUNT_URL=https://fitmemlstdev.blob.core.windows.net \
    GARMENT_MODELS_CONTAINER=garment-models \
    GARMENT_WORK_DIR=/dev/shm \
    FITME_CONCURRENCY=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/api/bin:$PATH

WORKDIR /app/src
RUN useradd --create-home --uid 10001 fitme && mkdir -p /models/cache && chown fitme:fitme /models/cache && python3 -m venv /opt/api
COPY src/ ./
COPY scripts/ /app/scripts/
COPY models/bundled_garments.json /opt/fitme/bundled_garments.json
RUN chmod -R a+rX /app/src

FROM common AS garment
EXPOSE 8002
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
# compileall runs as root: /app/src is root-owned, so the fitme user cannot write __pycache__ there.
RUN python -m compileall -q /app/src
USER fitme
RUN python -c "from api.garments import app"
CMD ["uvicorn","api.garments:app","--host","0.0.0.0","--port","8002","--workers","1"]
