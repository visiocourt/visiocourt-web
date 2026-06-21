#!/usr/bin/env bash
#
# CourtSense Raspberry Pi installer.
# Target: Raspberry Pi 4 or 5 running 64-bit Raspberry Pi OS (Bookworm).
# Run this from the vision/ directory:  bash deploy/install_pi.sh
#
# 64-bit OS matters: PyTorch / Ultralytics ship aarch64 wheels but not 32-bit
# armv7 ones. Check with `uname -m` (expect aarch64).

set -euo pipefail

echo "==> Checking architecture"
ARCH="$(uname -m)"
echo "    uname -m = ${ARCH}"
if [ "${ARCH}" != "aarch64" ]; then
  echo "    WARNING: not aarch64. Ultralytics/PyTorch may not install."
  echo "    Reflash with the 64-bit Raspberry Pi OS for the smoothest path."
fi

echo "==> Installing system packages"
sudo apt update
# python3-picamera2 drives the CSI ribbon camera (libcamera).
# libcap-dev is needed by picamera2; the rest are common build deps.
sudo apt install -y \
  python3-venv python3-pip \
  python3-picamera2 \
  libcap-dev libatlas-base-dev

echo "==> Creating virtual environment (with system site packages)"
# --system-site-packages lets the venv import the apt-installed picamera2.
python3 -m venv --system-site-packages .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip wheel

echo "==> Installing Python dependencies"
# Headless OpenCV: no GUI libs, which is what you want on an appliance.
pip install "numpy>=1.24,<2.2" opencv-python-headless ultralytics

echo "==> Done."
echo "    Activate with:  source .venv/bin/activate"
echo "    Smoke test  :  python selftest.py"
echo "    Next        :  bash deploy/export_model.sh   (faster inference)"
