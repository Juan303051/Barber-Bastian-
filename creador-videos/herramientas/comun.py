"""Rutas y utilidades compartidas por las herramientas."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EMPRESAS = RAIZ / "empresas"
BOVEDA = Path(os.environ.get("CREADOR_BOVEDA") or RAIZ / "boveda")
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


def seguro(texto: str) -> str:
    """Nombre apto para archivos y enlaces: sin espacios ni acentos."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", texto).strip("-")


def boveda_empresa(carpeta: Path) -> Path:
    return BOVEDA / "02-empresas" / carpeta.name


def nombre(carpeta: Path) -> str:
    ficha = boveda_empresa(carpeta) / "00-ficha.md"
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


def asegurar_carpetas() -> None:
    """Git no guarda carpetas vacías: se crean aquí las que el usuario necesita para soltar videos y recibir resultados."""
    for carpeta in empresas():
        for sub in ("videos/referencias", "videos/propios", "analisis", "formatos", "salidas"):
            (carpeta / sub).mkdir(parents=True, exist_ok=True)


def escribir_atomico(ruta: Path, texto: str) -> None:
    """Escribe en un temporal y lo renombra: si algo falla a medias, el archivo anterior queda intacto."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    temporal.write_text(texto, encoding="utf-8")
    os.replace(temporal, ruta)


def correr(comando: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(comando, capture_output=True, text=True, errors="replace")
