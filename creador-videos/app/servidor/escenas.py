"""Unión de las escenas de un video: se normalizan (tamaño, cuadros por segundo, sonido) y se unen en una sola toma continua.

Todo lo demás (quitar pausas, transcribir, dirigir, construir) trabaja sobre esa toma, igual que con un video de una sola escena.
Los instantes donde una escena termina y empieza la siguiente se devuelven para colocar transiciones sobre cortes que existen de verdad."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

FPS = 30
MAX_ESCENAS = 24


def sondear(ruta: Path) -> dict:
    """Duración, tamaño visible (con la rotación aplicada) y si tiene audio. Lanza ValueError si no es un video legible."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height:stream_side_data=rotation", "-of", "json", str(ruta)],
                       capture_output=True, text=True)
    try:
        info = json.loads(r.stdout or "{}")
        duracion = float(info.get("format", {}).get("duration", 0))
        videos = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        ancho, alto = int(videos[0]["width"]), int(videos[0]["height"])
        rotacion = next((abs(int(lado.get("rotation", 0))) for lado in videos[0].get("side_data_list", []) if "rotation" in lado), 0)
        tiene_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    except (ValueError, TypeError, KeyError, IndexError):
        raise ValueError("No es un video que pueda leer.") from None
    if duracion <= 0:
        raise ValueError("No es un video que pueda leer.")
    if rotacion in (90, 270):
        ancho, alto = alto, ancho
    return {"duracion": round(duracion, 2), "ancho": ancho, "alto": alto, "vertical": alto >= ancho, "audio": tiene_audio}


def unir(escenas: list[dict], destino: Path, ancho: int = 1080, alto: int = 1920) -> dict:
    """Une las escenas en orden. Cada una es {archivo: Path, duracion: float, audio: bool}. Devuelve {archivo, limites, duracion}:
    `limites` son los segundos donde empieza cada escena después de la primera."""
    if not escenas:
        raise RuntimeError("No hay escenas que unir.")
    entradas: list[str] = []
    cadenas: list[str] = []
    for i, e in enumerate(escenas):
        entradas += ["-i", str(e["archivo"])]
        cadenas.append(f"[{i}:v]scale={ancho}:{alto}:force_original_aspect_ratio=increase,crop={ancho}:{alto},setsar=1,fps={FPS},format=yuv420p[v{i}]")
        if e.get("audio", True):
            cadenas.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{e['duracion']:.3f},asetpts=PTS-STARTPTS[a{i}]")
        else:
            cadenas.append(f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=0:{e['duracion']:.3f},asetpts=PTS-STARTPTS[a{i}]")
    union = "".join(f"[v{i}][a{i}]" for i in range(len(escenas)))
    filtro = ";".join(cadenas) + f";{union}concat=n={len(escenas)}:v=1:a=1[v][a]"
    r = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *entradas, "-filter_complex", filtro, "-map", "[v]", "-map", "[a]",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(destino)],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not destino.exists():
        raise RuntimeError("No pude unir las escenas: " + (r.stderr.strip().splitlines() or ["error desconocido"])[-1])
    limites, acumulado = [], 0.0
    for e in escenas[:-1]:
        acumulado += e["duracion"]
        limites.append(round(acumulado, 3))
    return {"archivo": destino, "limites": limites, "duracion": round(acumulado + escenas[-1]["duracion"], 3)}


def sondear_imagen(ruta: Path) -> dict:
    """Tamaño de una imagen y si trae canal de transparencia. Lanza ValueError si no se puede leer."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,pix_fmt", "-of", "json", str(ruta)], capture_output=True, text=True)
    try:
        flujo = json.loads(r.stdout or "{}")["streams"][0]
        ancho, alto = int(flujo["width"]), int(flujo["height"])
    except (ValueError, KeyError, IndexError, TypeError):
        raise ValueError("No es una imagen que pueda leer.") from None
    if ancho < 16 or alto < 16:
        raise ValueError("La imagen es demasiado pequeña.")
    return {"ancho": ancho, "alto": alto, "transparente": any(x in str(flujo.get("pix_fmt", "")) for x in ("rgba", "bgra", "argb", "abgr", "yuva", "gbrap", "ya8", "ya16"))}
