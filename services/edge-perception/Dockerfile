# TANTU Edge-Perception — tiered Dockerfile
# Build for Pi5 Hailo-8L (arm64 + HailoRT) or Orin Nano (l4t CUDA)
# Default (cloud dev) stays CPU-only on python:3.11-slim; accel is opt-in via build-arg.
#
# Usage:
#   # Pi5 Hailo-8L (on arm64 host or via buildx):
#   docker buildx build --platform linux/arm64 \
#     --build-arg EDGE_TIER=pi5_hailo -t tantu/edge-perception:pi5-hailo .
#   # Orin Nano (JetPack 6 / L4T):
#   docker build --target edge-orin -t tantu/edge-perception:orin .
#   # Cloud / CI smoke (current behaviour):
#   docker build -t tantu/edge-perception:latest .

ARG EDGE_TIER=pi5_hailo

# ── Stage: base (cloud/dev, CPU-only) ──
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

ARG TARGETARCH
ARG EDGE_TIER

# Fix bookworm: libatlas3-base → libopenblas0. Add GStreamer for hw_decoder tiers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libopenblas0 liblapack3 libgfortran5 libopenjp2-7 \
    curl ca-certificates \
    # GStreamer (needed when hw_decoder=true on Orin/Thor; harmless on Pi5)
    gstreamer1.0-tools libgstreamer1.0-0 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
    libgstreamer-plugins-base1.0-0 \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# HailoRT userspace — only on arm64 + pi5_hailo tier (conditional, cache-safe)
# Host must still have hailo_pci kernel module; this just installs libhailort.so.
# Download is pinned and fails open (no break for orin/cloud builds).
RUN if [ "$TARGETARCH" = "arm64" ] && [ "$EDGE_TIER" = "pi5_hailo" ]; then \
      set -eux; \
      apt-get update && apt-get install -y --no-install-recommends wget gnupg; \
      HAILORT_VER=4.18.0; \
      wget -q -O /tmp/hailort.deb \
        "https://hailo-hailort.s3.eu-west-2.amazonaws.com/${HAILORT_VER}/hailort_${HAILORT_VER}_arm64.deb" \
        || echo "WARN: hailort deb download failed (auth/network) — skipping accel install"; \
      if [ -f /tmp/hailort.deb ] && [ -s /tmp/hailort.deb ]; then \
        dpkg -i /tmp/hailort.deb || apt-get install -f -y; \
        rm /tmp/hailort.deb; \
      fi; \
      apt-get purge -y wget gnupg 2>/dev/null || true; \
      rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

# Optional: hailort Python binding when tier is hailo (no-op if deb missed)
RUN pip install --upgrade pip && \
    if [ "$EDGE_TIER" = "pi5_hailo" ]; then \
      pip install -e ".[hailo]" 2>/dev/null || pip install -e .; \
    else \
      pip install -e .; \
    fi

EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD curl -fsS http://localhost:8002/health || exit 1
CMD ["uvicorn", "edge_perception.api.main:app", "--host", "0.0.0.0", "--port", "8002"]

# ── Stage: edge-orin (Jetson Orin Nano / Thor, L4T CUDA) ──
# Use only when building on/for Jetson. Requires L4T base with CUDA 12.x.
# docker build --target edge-orin -t tantu/edge-perception:orin .
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.4-py3 AS edge-orin
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libopenblas0 gstreamer1.0-tools \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
    libgstreamer-plugins-base1.0-0 libgstreamer1.0-0 v4l-utils curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .
EXPOSE 8002
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD curl -fsS http://localhost:8002/health || exit 1
CMD ["uvicorn", "edge_perception.api.main:app", "--host", "0.0.0.0", "--port", "8002"]
