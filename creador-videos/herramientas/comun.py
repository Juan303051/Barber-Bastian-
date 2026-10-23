"""Rutas y utilidades compartidas por las herramientas."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EMPRESAS = RAIZ / "empresas"
EXTENSIONES = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
TIPOS = {"referencias": "referencia", "propios": "propio"}


def empresas(filtro: str | None = None) -> list[Path]:
    carpetas = sorted(p for p in EMPRESAS.iterdir() if p.is_dir())
    if filtro:
        elegidas = [p for p in carpetas if p.name == filtro]
        if not elegidas:
            raise SystemExit(f"No existe la empresa '{filtro}'. Opciones: {', '.join(p.name for p in carpetas)}")
        return elegidas
    return carpetas


def nombre(carpeta: Path) -> str:
    ficha = carpeta / "README.md"
    if ficha.exists():
        for linea in ficha.read_text(encoding="utf-8").splitlines():
            if linea.startswith("# "):
                return linea[2:].strip()
    return carpeta.name


def urls(carpeta: Path, tipo: str) -> list[str]:
    """Una URL por línea; lo que va después de '#' es un comentario."""
    archivo = carpeta / f"{tipo}.txt"
    if not archivo.exists():
        return []
    salida = []
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea:
            salida.append(linea)
    return salida


def videos(carpeta: Path, tipo: str) -> list[Path]:
    base = carpeta / "videos" / tipo
    if not base.exists():
        return []
    # Los ".f137.mp4" son restos de una descarga a medias.
    return sorted(
        p for p in base.iterdir()
        if p.suffix.lower() in EXTENSIONES and not re.search(r"\.f\d+\.", p.name)
    )


def carpeta_analisis(carpeta: Path) -> Path:
    destino = carpeta / "analisis"
    destino.mkdir(exist_ok=True)
    return destino


def correr(comando: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(comando, capture_output=True, text=True, errors="replace")
