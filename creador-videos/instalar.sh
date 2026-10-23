#!/bin/bash
# Instalación única en el Mac: ffmpeg, deno (lo pide YouTube), node (Remotion), Python 3.12 y un entorno propio.
set -e
cd "$(dirname "$0")"
command -v brew >/dev/null || { echo "Falta Homebrew. Instálalo siguiendo https://brew.sh y vuelve a ejecutar ./instalar.sh"; exit 1; }
for paquete in ffmpeg deno node python@3.12; do
  brew list "$paquete" >/dev/null 2>&1 || brew install "$paquete"
done
PY="$(brew --prefix python@3.12)/bin/python3.12"
rm -rf .venv
"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
(cd remotion && npm install --no-audit --no-fund)
./creador preparar
echo
echo "Instalado. Comprueba que todo funciona con:  ./creador probar"
