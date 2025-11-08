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
RUN echo "deb https://repo.download.nvidia.com/jetson/common r32.7 main" > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
 && echo "deb https://repo.download.nvidia.com/jetson/t210 r32.7 main" >> /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
 && apt-key adv --fetch-keys https://repo.download.nvidia.com/jetson/jetson-ota-public.asc \
 && sed -i '/apt\.kitware\.com/d' /etc/apt/sources.list \
 && (find /etc/apt/sources.list.d -name '*kitware*' -delete || true) \
 && apt-get update \
 && mkdir -p /tmp/dt-fake \
 && echo -ne 'nvidia,jetson-nano\0nvidia,tegra210-p3450-0000\0nvidia,tegra210\0' > /tmp/dt-fake/compatible \
 && mount --bind /tmp/dt-fake /sys/firmware/devicetree/base || true \
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
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libgstreamer-plugins-bad1.0-0 \
    nvidia-l4t-gstreamer \
    nvidia-l4t-jetson-multimedia-api \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/dt-fake

# Align container groups with host GIDs for device access (adjust IDs as needed).
RUN groupadd -g 44 video || true \
 && groupadd -g 1002 i2c || true

# Python dependencies.
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && python3 -m pip install --no-cache-dir -r /tmp/requirements.txt \
 && python3 -m pip install --no-cache-dir jetson-utils Jetson.GPIO \
 && rm /tmp/requirements.txt

# Make python/pip resolve to Python 3 for CLI convenience
RUN ln -sf /usr/bin/python3 /usr/local/bin/python \
 && ln -sf /usr/bin/pip3 /usr/local/bin/pip

# Ensure GPIO udev rules exist so the non-root user can access pins.
RUN groupadd -f gpio \
 && cp /usr/local/lib/python3.6/dist-packages/Jetson/GPIO/99-gpio.rules /etc/udev/rules.d/99-gpio.rules \
 && (udevadm control --reload-rules || true) \
 && (udevadm trigger || true)

# Create workspace user for better host-volume ownership; reuse existing IDs if present.
ARG USERNAME=jetbot
ARG USER_UID=1000
ARG USER_GID=1000
RUN if ! getent group ${USER_GID} >/dev/null; then groupadd --gid ${USER_GID} ${USERNAME}; fi \
 && if ! id -u ${USERNAME} >/dev/null 2>&1; then useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}; else usermod --gid ${USER_GID} ${USERNAME}; fi \
 && usermod -aG video,i2c,gpio ${USERNAME}

ENV LD_LIBRARY_PATH=/usr/lib/aarch64-linux-gnu/tegra:/usr/lib/aarch64-linux-gnu/tegra-egl:${LD_LIBRARY_PATH}

WORKDIR /workspace
USER ${USERNAME}

EXPOSE 8888

# Default command starts Jupyter Lab bound to all interfaces.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--no-browser", "--LabApp.token=", "--LabApp.password=", "--allow-root"]