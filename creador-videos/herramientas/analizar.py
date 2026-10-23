"""Mide cada video: cortes, ritmo, audio, voz y fotogramas para que Claude pueda verlo."""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from comun import TIPOS, carpeta_analisis, correr, nombre, videos

_whisper = {"modelo": None, "fallo": False}


def _sondear(ruta: Path) -> dict:
    salida = correr(["ffprobe", "-v", "error", "-show_entries",
                     "format=duration:stream=codec_type,width,height,r_frame_rate",
                     "-of", "json", str(ruta)])
    datos = json.loads(salida.stdout or "{}")
    video = next((s for s in datos.get("streams", []) if s["codec_type"] == "video"), {})
    num, _, den = video.get("r_frame_rate", "0/1").partition("/")
    return {
        "duracion": float(datos.get("format", {}).get("duration", 0)),
        "ancho": video.get("width", 0),
        "alto": video.get("height", 0),
        "fps": round(float(num) / float(den or 1), 2) if float(den or 1) else 0,
        "tiene_audio": any(s["codec_type"] == "audio" for s in datos.get("streams", [])),
    }


def _cortes(ruta: Path, umbral: float) -> list[float]:
    salida = correr(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-an",
                     "-vf", f"scale=320:-2,select='gt(scene,{umbral})',showinfo", "-f", "null", "-"])
    tiempos = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", salida.stderr)]
    unidos: list[float] = []
    for t in tiempos:  # dos cortes a menos de 0.25 s son un mismo destello
        if not unidos or t - unidos[-1] >= 0.25:
            unidos.append(round(t, 2))
    return unidos


def _ritmo(cortes: list[float], duracion: float) -> dict:
    limites = [0.0] + cortes + [duracion]
    planos = [b - a for a, b in zip(limites, limites[1:]) if b > a]
    tramos = [0] * (int(duracion // 5) + 1)
    for t in cortes:
        tramos[int(t // 5)] += 1
    return {
        "n_cortes": len(cortes),
        "cortes": cortes,
        "plano_medio": round(statistics.mean(planos), 2) if planos else None,
        "plano_mediano": round(statistics.median(planos), 2) if planos else None,
        "cortes_por_10s": round(len(cortes) / duracion * 10, 2) if duracion else None,
        "primer_corte": cortes[0] if cortes else None,
        "cortes_en_gancho": sum(1 for t in cortes if t < 3),
        "curva_5s": tramos,
    }


def _audio(ruta: Path, duracion: float) -> dict | None:
    salida = correr(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-vn", "-af",
                     "ebur128=peak=true:framelog=quiet,silencedetect=noise=-35dB:d=0.4",
                     "-f", "null", "-"])
    resumen = salida.stderr.rsplit("Summary:", 1)[-1]
    lufs = re.search(r"I:\s+(-?[0-9.]+) LUFS", resumen)
    if not lufs:
        return None
    rango = re.search(r"LRA:\s+([0-9.]+) LU", resumen)
    pico = re.search(r"Peak:\s+(-?[0-9.]+) dBFS", resumen)
    silencio = sum(float(s) for s in re.findall(r"silence_duration: ([0-9.]+)", salida.stderr))
    return {
        "lufs": float(lufs.group(1)),
        "rango_lu": float(rango.group(1)) if rango else None,
        "pico_db": float(pico.group(1)) if pico else None,
        "silencio_pct": round(silencio / duracion * 100, 1) if duracion else None,
    }


def _voz(ruta: Path, duracion: float, modelo: str) -> dict | None:
    if _whisper["fallo"]:
        return None
    try:
        if _whisper["modelo"] is None:
            from faster_whisper import WhisperModel
            _whisper["modelo"] = WhisperModel(modelo, compute_type="int8")
        segmentos, info = _whisper["modelo"].transcribe(str(ruta), vad_filter=True)
        segmentos = [{"ini": round(s.start, 1), "fin": round(s.end, 1), "texto": s.text.strip()}
                     for s in segmentos]
    except Exception as error:  # sin el paquete, sin modelo descargado o sin internet
        _whisper["fallo"] = True
        print(f"  (sin transcripción: {str(error).splitlines()[0][:120]}; sigo sin ella)")
        return None
    palabras = sum(len(s["texto"].split()) for s in segmentos)
    return {
        "idioma": info.language,
        "palabras_por_min": round(palabras / duracion * 60) if duracion else None,
        "gancho_texto": " ".join(s["texto"] for s in segmentos if s["ini"] < 3.5),
        "segmentos": segmentos,
    }


def _imagenes(ruta: Path, datos: dict, destino: Path, stem: str) -> dict:
    ancho = 180 if datos["alto"] > datos["ancho"] else 320
    gancho, hoja = destino / f"{stem}-gancho.jpg", destino / f"{stem}-hoja.jpg"
    # Seis segundos iniciales, dos fotogramas por segundo: lo que decide si te quedas o deslizas.
    correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-t", "6", "-i", str(ruta), "-vf",
            f"fps=2,scale={ancho}:-2,tile=6x2", "-frames:v", "1", "-q:v", "4", str(gancho)])
    # Veinticuatro fotogramas repartidos en todo el video.
    correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(ruta), "-vf",
            f"fps=24/{max(datos['duracion'], 1)},scale={ancho}:-2,tile=6x4", "-frames:v", "1",
            "-q:v", "4", str(hoja)])
    return {"gancho": gancho.name if gancho.exists() else None,
            "hoja": hoja.name if hoja.exists() else None}


def analizar(carpeta: Path, umbral: float, con_voz: bool, modelo_voz: str, forzar: bool) -> int:
    destino = carpeta_analisis(carpeta)
    hechos = 0
    for tipo, etiqueta in TIPOS.items():
        for ruta in videos(carpeta, tipo):
            salida = destino / f"{ruta.stem}.analisis.json"
            if salida.exists() and not forzar:
                continue
            print(f"  · {nombre(carpeta)} / {ruta.name}")
            datos = _sondear(ruta)
            if not datos["duracion"]:
                print("    no se pudo leer el video; lo salto")
                continue
            resultado = {
                "id": ruta.stem,
                "tipo": etiqueta,
                "archivo": f"videos/{tipo}/{ruta.name}",
                **{k: datos[k] for k in ("duracion", "ancho", "alto", "fps")},
                "vertical": datos["alto"] > datos["ancho"],
                "ritmo": _ritmo(_cortes(ruta, umbral), datos["duracion"]),
                "audio": _audio(ruta, datos["duracion"]) if datos["tiene_audio"] else None,
                "voz": _voz(ruta, datos["duracion"], modelo_voz) if con_voz and datos["tiene_audio"] else None,
                "imagenes": _imagenes(ruta, datos, destino, ruta.stem),
            }
            salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
            hechos += 1
    return hechos
