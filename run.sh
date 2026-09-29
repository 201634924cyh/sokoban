#!/usr/bin/env bash
# Sokoban launcher for Linux / macOS
set -e
cd "$(dirname "$0")"

PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done

if [ -z "$PY" ]; then
  echo "[ERROR] Python 3 not found. Please install Python 3.9+."
  exit 1
fi

if ! "$PY" -c "import pygame" >/dev/null 2>&1; then
  echo "[ERROR] pygame is not installed. Run:"
  echo "    $PY -m pip install pygame"
  echo ""
  echo "  On Debian/Ubuntu you may also need CJK fonts:"
  echo "    sudo apt install fonts-noto-cjk"
  exit 1
fi

exec "$PY" sokoban.py
