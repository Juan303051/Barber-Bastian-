"""Convierte un guion JSON en video con Remotion (render) o lo abre para previsualizar (estudio)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from comun import EMPRESAS, RAIZ, corto, nombre
from guion import completar, recursos, revisar

REMOTION = RAIZ / "remotion"
CACHE = REMOTION / ".cache"


def _guion(carpeta: Path, indicado: str) -> Path:
    directo = Path(indicado)
    if directo.is_file():
        return directo
    dentro = carpeta / "formatos" / (indicado if indicado.endswith(".json") else indicado + ".json")
    if dentro.is_file():
        return dentro
    disponibles = sorted(p.stem for p in (carpeta / "formatos").glob("*.json")) if (carpeta / "formatos").exists() else []
    raise SystemExit(f"No encuentro el guion '{indicado}'. En {carpeta.name}/formatos hay: {', '.join(disponibles) or 'ninguno'}")


def preparar(carpeta: Path, indicado: str, cache: Path = CACHE) -> tuple[Path, Path, Path]:
    """Devuelve (props.json, carpeta pública, guion). Solo incluye los archivos que el guion usa."""
    guion = _guion(carpeta, indicado)
    props = json.loads(guion.read_text(encoding="utf-8"))
    ficha = carpeta / "marca.json"
    props["marca"] = {"nombre": nombre(carpeta)} | (json.loads(ficha.read_text(encoding="utf-8")) if ficha.exists() else {}) | props.get("marca", {})
    if not ficha.exists():
        print(f"  (sin {corto(ficha)}: uso colores y fuente por defecto)")
    props.setdefault("escenas", [])
    completar(props)
    errores = revisar(props)
    if errores:
        raise SystemExit(f"El guion {guion.name} tiene problemas:\n  - " + "\n  - ".join(errores))

    publica = cache / "publico"
    shutil.rmtree(publica, ignore_errors=True)
    faltan = []
    for ruta in recursos(props):
        origen = EMPRESAS / ruta
        if not origen.is_file():
            faltan.append(ruta)
            continue
        destino = publica / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:  # Remotion no sirve enlaces simbólicos (404); un enlace duro no ocupa espacio extra
            os.link(origen, destino)
        except OSError:
            shutil.copy2(origen, destino)
    if faltan:
        raise SystemExit("Faltan archivos (rutas relativas a empresas/):\n  " + "\n  ".join(faltan))
    publica.mkdir(parents=True, exist_ok=True)

    archivo = cache / "props.json"
    archivo.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return archivo, publica, guion


def _remotion(args: list[str], capturar: bool = False) -> subprocess.CompletedProcess:
    if not (REMOTION / "node_modules").exists():
        raise SystemExit("Falta instalar Remotion: ejecuta ./instalar.sh (o 'npm install' dentro de remotion/).")
    navegador = os.environ.get("CREADOR_NAVEGADOR")  # opcional: usar un Chrome/Chromium ya instalado
    extra = [f"--browser-executable={navegador}"] if navegador else []
    return subprocess.run(["npx", "remotion", *args, *extra], cwd=REMOTION, capture_output=capturar, text=capturar)


def render(carpeta: Path, indicado: str, salida: Path | None = None, capturar: bool = False) -> subprocess.CompletedProcess:
    props, publica, guion = preparar(carpeta, indicado)
    if salida is None:
        formato = json.loads(props.read_text(encoding="utf-8")).get("formato") or guion.stem
        salida = carpeta / "salidas" / f"{formato}.mp4"
    salida.parent.mkdir(parents=True, exist_ok=True)
    resultado = _remotion(["render", "src/index.ts", "Formato", str(salida),
                           f"--props={props}", f"--public-dir={publica}"], capturar)
    if resultado.returncode == 0 and not capturar:
        print(f"\n  video: {corto(salida)}")
    return resultado


def estudio(carpeta: Path, indicado: str) -> int:
    props, publica, _ = preparar(carpeta, indicado)
    return _remotion(["studio", "src/index.ts", f"--props={props}", f"--public-dir={publica}"]).returncode
