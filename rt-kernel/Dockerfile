FROM debian:trixie

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bc \
    bison \
    binutils-aarch64-linux-gnu \
    build-essential \
    ca-certificates \
    cpio \
    curl \
    debhelper \
    dpkg-dev \
    dwarves \
    fakeroot \
    flex \
    gcc \
    gcc-aarch64-linux-gnu \
    git \
    kmod \
    libdw-dev \
    libelf-dev \
    lsb-release \
    libssl-dev \
    make \
    pahole \
    python3 \
    rsync \
    zstd \
    && rm -rf /var/lib/apt/lists/*
