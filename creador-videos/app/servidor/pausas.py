"""Quita las pausas largas de un video con voz."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _silencios(video: Path, umbral_db: int, minimo: float) -> list[tuple[float, float]]:
    salida = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-vn", "-af", f"silencedetect=noise={umbral_db}dB:d={minimo}",
                             "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
    inicios = [float(x) for x in re.findall(r"silence_start: (-?[0-9.]+)", salida)]
    fines = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", salida)]
    return list(zip(inicios, fines))


def tramos_a_conservar(duracion: float, silencios: list[tuple[float, float]], margen: float = 0.15) -> list[tuple[float, float]]:
    """Cada silencio se acorta dejando `margen` a cada lado, para que el corte no suene brusco."""
    conservar, cursor = [], 0.0
    for inicio, fin in silencios:
        corte_ini, corte_fin = max(inicio, 0.0) + margen, fin - margen
        if corte_fin - corte_ini < 0.1:
            continue
        if corte_ini > cursor:
            conservar.append((cursor, corte_ini))
        cursor = corte_fin
    if cursor < duracion:
        conservar.append((cursor, duracion))
    return [(a, b) for a, b in conservar if b - a > 0.05]


def quitar(origen: Path, destino: Path, duracion: float, tiene_audio: bool, umbral_db: int = -34, minimo: float = 0.55) -> dict:
    """Escribe `destino` sin las pausas. Devuelve cuántos segundos se quitaron (0 si no había nada que quitar)."""
    if not tiene_audio:
        return {"quitado": 0.0, "cortes": 0, "archivo": origen}
    tramos = tramos_a_conservar(duracion, _silencios(origen, umbral_db, minimo))
    while len(tramos) > 250:  # demasiados cortes: se sube el mínimo de pausa para no saturar el filtro
        minimo += 0.2
        tramos = tramos_a_conservar(duracion, _silencios(origen, umbral_db, minimo))
    nuevo = sum(b - a for a, b in tramos)
    if len(tramos) <= 1 and nuevo >= duracion - 0.05:
        return {"quitado": 0.0, "cortes": 0, "archivo": origen}
    cadena = []
    for i, (a, b) in enumerate(tramos):
        cadena.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[a{i}]")
    union = "".join(f"[v{i}][a{i}]" for i in range(len(tramos)))
    filtro = ";".join(cadena) + f";{union}concat=n={len(tramos)}:v=1:a=1[v][a]"
    resultado = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(origen), "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
                                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                                "-movflags", "+faststart", str(destino)], capture_output=True, text=True, errors="replace")
    if resultado.returncode != 0 or not destino.exists():
        raise RuntimeError("No pude quitar las pausas: " + (resultado.stderr.strip().splitlines() or ["error desconocido"])[-1])
    return {"quitado": round(duracion - nuevo, 2), "cortes": len(tramos) - 1, "archivo": destino}
