# Jetson Nano / JetBot development image with Jupyter Lab.
ARG BASE_IMAGE=nvcr.io/nvidia/l4t-pytorch:r32.7.1-pth1.10-py3
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Etc/UTC

# System dependencies for science stack and camera access.
RUN find /etc/apt/sources.list.d -name '*kitware*' -delete || true \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-opencv \
    python3-matplotlib \
    libgl1 \
    v4l-utils \
    git \
    nano \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Python dependencies.
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools wheel \
 && python3 -m pip install -r /tmp/requirements.txt \
 && rm /tmp/requirements.txt

# Create workspace user for better host-volume ownership.
ARG USERNAME=jetbot
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ${USERNAME} \
 && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

WORKDIR /workspace
USER ${USERNAME}

EXPOSE 8888

# Default command starts Jupyter Lab bound to all interfaces.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--LabApp.token=", "--LabApp.password="]
