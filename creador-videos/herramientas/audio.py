"""Medidas de audio con ffmpeg: volumen (LUFS), pico real, rango y silencios. Las usan el análisis, la mezcla y el control de calidad."""
from __future__ import annotations

import re
from pathlib import Path

from comun import correr


def medir(ruta: Path, filtro: str | None = None, umbral_silencio: str = "-35dB", silencio_minimo: float = 0.4) -> dict | None:
    """Volumen integrado, rango, pico real y silencios de un archivo (con un filtro previo opcional). None si no tiene audio."""
    cadena = (f"{filtro}," if filtro else "") + f"ebur128=peak=true:framelog=quiet,silencedetect=noise={umbral_silencio}:d={silencio_minimo}"
    salida = correr(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-vn", "-af", cadena, "-f", "null", "-"])
    resumen = salida.stderr.rsplit("Summary:", 1)[-1]
    lufs = re.search(r"I:\s+(-?[0-9.]+) LUFS", resumen)
    if not lufs:
        return None
    rango = re.search(r"LRA:\s+([0-9.]+) LU", resumen)
    pico = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", resumen)
    inicios = [float(s) for s in re.findall(r"silence_start: (-?[0-9.]+)", salida.stderr)]
    fines = [float(s) for s in re.findall(r"silence_end: ([0-9.]+)", salida.stderr)]
    silencios = []
    for i, inicio in enumerate(inicios):
        silencios.append((max(0.0, inicio), fines[i] if i < len(fines) else None))
    return {
        "lufs": float(lufs.group(1)),
        "rango_lu": float(rango.group(1)) if rango else None,
        "pico_db": float(pico.group(1)) if pico else None,
        "silencios": silencios,
    }


def duracion(ruta: Path) -> float:
    salida = correr(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ruta)])
    try:
        return float(salida.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return 0.0
