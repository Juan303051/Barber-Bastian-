#!/bin/bash
# Instalación única en el Mac: ffmpeg, deno (lo pide YouTube), node (Remotion) y un entorno Python propio.
set -e
cd "$(dirname "$0")"
command -v brew >/dev/null || { echo "Falta Homebrew: https://brew.sh"; exit 1; }
for paquete in ffmpeg deno node; do
  brew list "$paquete" >/dev/null 2>&1 || brew install "$paquete"
done
python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
(cd remotion && npm install --no-audit --no-fund)
echo "Listo. Prueba: ./creador todo --empresa mundial-de-motos"
