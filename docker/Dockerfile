# Jetson Nano / JetBot development image with Jupyter Lab.
ARG BASE_IMAGE=nvcr.io/nvidia/l4t-pytorch:r32.7.1-pth1.10-py3
FROM ${BASE_IMAGE}

LABEL maintainer="JetBot Thesis Maintainers" \
      description="JetBot dev container for Jetson Nano with PyTorch, OpenCV, and Jupyter."

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Etc/UTC

# System dependencies for science stack, camera, GPIO, and I2C access; remove stale Kitware repo first.
RUN sed -i '/apt\.kitware\.com/d' /etc/apt/sources.list \
 && (find /etc/apt/sources.list.d -name '*kitware*' -delete || true) \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-opencv \
    python3-matplotlib \
    libgl1 \
    v4l-utils \
    git \
    nano \
    libi2c-dev \
    i2c-tools \
    libjpeg-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies.
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
 && python3 -m pip install --no-cache-dir jetson-utils Jetson.GPIO \
 && rm /tmp/requirements.txt

# Ensure GPIO udev rules exist so the non-root user can access pins.
RUN groupadd -f gpio \
 && cp /usr/local/lib/python3.6/dist-packages/Jetson/GPIO/99-gpio.rules /etc/udev/rules.d/99-gpio.rules \
 && (udevadm control --reload-rules || true) \
 && (udevadm trigger || true)

# Create workspace user for better host-volume ownership.
ARG USERNAME=jetbot
ARG USER_UID=1000
ARG USER_GID=1000
RUN groupadd --gid ${USER_GID} ${USERNAME} \
 && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} \
 && usermod -aG video,i2c,gpio ${USERNAME}

WORKDIR /workspace
USER ${USERNAME}

EXPOSE 8888

# Default command starts Jupyter Lab bound to all interfaces.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--LabApp.token=", "--LabApp.password=", "--allow-root"]
