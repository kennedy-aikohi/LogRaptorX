#!/bin/bash
# LogRaptorX - Unix Build/Dev Script
# Developer: Kennedy Aikohi

set -e

echo "============================================================"
echo "  LogRaptorX - Build Script"
echo "  Developer: Kennedy Aikohi | github.com/kennedy-aikohi"
echo "============================================================"

# Create venv if not present
if [ ! -d ".venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv .venv
fi

echo "[2/4] Activating venv and installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt -q

echo "[3/4] Running app (dev mode)..."
cd src
python main.py
