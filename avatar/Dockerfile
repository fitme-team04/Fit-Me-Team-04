# 역할: 서비스의 Python·Blender 의존성과 실행 이미지를 구성합니다.
FROM ubuntu:24.04 AS blender-download
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /tmp
RUN curl -fSL --retry 3 https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz -o blender.tar.xz \
    && echo '4da1c956673c0485e63054e563ee69198cc8f80d8157dd7592dffc8a6a5592e6  blender.tar.xz' | sha256sum -c - \
    && mkdir -p /opt/blender && tar -xJf blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm blender.tar.xz

# CUDA devel is used to compile Detectron2 for the team's T4 GPU (sm_75).
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel@sha256:0cf3402e946b7c384ba943ee05c90b4c5a4a05227923921f2b0918c011cfaf56 AS avatar
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential ninja-build libx11-6 libxrender1 libxfixes3 libxi6 \
    libxkbcommon0 libsm6 libice6 libxxf86vm1 libgl1 libglib2.0-0 libgomp1 libstdc++6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=blender-download /opt/blender /opt/blender
RUN /opt/blender/4.3/python/bin/python3.11 -m pip install \
       --no-cache-dir --only-binary=:all: --no-deps scipy==1.15.3 \
    && /opt/blender/blender -b --python-exit-code 1 --python-expr \
       "import numpy, scipy; from scipy.sparse.linalg import factorized"
COPY requirements-sam.txt constraints-sam.txt /tmp/
RUN /opt/conda/bin/python -m pip install --no-cache-dir \
    -c /tmp/constraints-sam.txt -r /tmp/requirements-sam.txt
ARG TORCH_CUDA_ARCH_LIST=7.5
RUN FORCE_CUDA=1 TORCH_CUDA_ARCH_LIST="$TORCH_CUDA_ARCH_LIST" MAX_JOBS=2 \
    /opt/conda/bin/python -m pip install --no-cache-dir --no-build-isolation \
    -c /tmp/constraints-sam.txt 'git+https://github.com/facebookresearch/detectron2.git@a1ce2f9'
RUN /opt/conda/bin/python -m pip install --no-cache-dir -c /tmp/constraints-sam.txt \
    'git+https://github.com/microsoft/MoGe.git@925b8ed835a7a9cdb7578ba15c658a0afc969030'
COPY vendor/sam-3d-body/ /opt/sam-body/
ENV BLENDER_BIN=/opt/blender/blender \
    FITME_TEMPLATE=/models/fitme_depth_fixed.blend \
    SAM_PYTHON=/opt/conda/bin/python \
    SAM_CHECKPOINT=/models/sam/model.ckpt \
    SAM_MHR=/models/mhr_model.pt \
    SAM_POSE=/models/a_pose.npz \
    SAM_BINDING=/models/sam_body.npz \
    SAM_DETECTOR_DIR=/models/vitdet \
    SAM_FOV=moge2 \
    SAM_FOV_CHECKPOINT=/models/moge/model.pt \
    MOMENTUM_ENABLED=0 \
    HF_HOME=/models/hf \
    HF_HUB_OFFLINE=1 \
    PYTHONPATH=/opt/sam-body \
    FITME_CONCURRENCY=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR=/tmp/matplotlib \
    XDG_CACHE_HOME=/tmp/fitme-cache
RUN /opt/conda/bin/python -m venv /opt/api
COPY requirements.txt /tmp/requirements-api.txt
RUN /opt/api/bin/python -m pip install --no-cache-dir -r /tmp/requirements-api.txt
RUN useradd --create-home --uid 10001 fitme && mkdir -p /models
WORKDIR /app/src
COPY src/ /app/src/
COPY scripts/ /app/scripts/
RUN chmod -R a+rX /app /opt/sam-body \
    && /opt/conda/bin/python -c 'import torch, cv2, detectron2, moge; from sam_3d_body import SAM3DBodyEstimator; print(torch.__version__)'
ENV PATH=/opt/api/bin:$PATH
USER fitme
RUN python -c 'from api.avatar import app'
EXPOSE 8001
CMD ["uvicorn","api.avatar:app","--host","0.0.0.0","--port","8001","--workers","1"]
