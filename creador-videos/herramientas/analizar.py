"""Mide cada video: cortes, ritmo, audio, voz y fotogramas para que Claude pueda verlo."""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

from comun import TIPOS, boveda_empresa, carpeta_analisis, correr, escribir_atomico, nombre, seguro, videos

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


def _voz(ruta: Path, duracion: float, modelo: str, avance=None, idioma: str | None = None) -> dict | None:
    if _whisper["fallo"]:
        return None
    try:
        if _whisper["modelo"] is None:
            from faster_whisper import WhisperModel
            _whisper["modelo"] = WhisperModel(modelo, compute_type="int8")
        generador, info = _whisper["modelo"].transcribe(str(ruta), vad_filter=True, word_timestamps=True, language=idioma)
        segmentos = []
        for segmento in generador:  # se recorre uno a uno para poder avisar del avance
            segmentos.append(segmento)
            if avance and duracion:
                avance(min(1.0, segmento.end / duracion))
        palabras = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segmentos for w in (s.words or [])]
        segmentos = [{"ini": round(s.start, 1), "fin": round(s.end, 1), "texto": s.text.strip()}
                     for s in segmentos]
    except Exception as error:  # sin el paquete, sin modelo descargado o sin internet
        _whisper["fallo"] = True
        print(f"  (sin transcripción: {str(error).splitlines()[0][:120]}; sigo sin ella)")
        return None
    n_palabras = sum(len(s["texto"].split()) for s in segmentos)
    return {
        "idioma": info.language,
        "palabras_por_min": round(n_palabras / duracion * 60) if duracion else None,
        "gancho_texto": " ".join(s["texto"] for s in segmentos if s["ini"] < 3.5),
        "segmentos": segmentos,
        "palabras": palabras,  # [inicio, fin, palabra]: sirve para medir el ritmo de los subtítulos
    }


MAX_PLANOS = 80


def _imagenes(ruta: Path, datos: dict, medios: Path, cortes: list[float], con_planos: bool = True) -> dict:
    """Guarda en la bóveda tres cosas: el gancho, una hoja del video entero y un fotograma por plano."""
    medios.mkdir(parents=True, exist_ok=True)
    ancho = 180 if datos["alto"] > datos["ancho"] else 320
    duracion = datos["duracion"]
    # Seis segundos iniciales, dos fotogramas por segundo: lo que decide si te quedas o deslizas.
    correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-t", "6", "-i", str(ruta), "-vf",
            f"fps=2,scale={ancho}:-2,tile=6x2", "-frames:v", "1", "-q:v", "4", str(medios / "gancho.jpg")])
    # Veinticuatro fotogramas repartidos en todo el video.
    correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(ruta), "-vf",
            f"fps=24/{max(duracion, 1)},scale={ancho}:-2,tile=6x4", "-frames:v", "1",
            "-q:v", "4", str(medios / "hoja.jpg")])
    # Un fotograma por plano, tomado poco después de que empieza.
    limites = [0.0] + cortes + [duracion]
    planos = []
    for n, (ini, fin) in enumerate(list(zip(limites, limites[1:]))[:MAX_PLANOS if con_planos else 0], start=1):
        if fin <= ini:
            continue
        archivo = f"plano-{n:02d}.jpg"
        correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{ini + min(0.4, (fin - ini) / 2):.2f}",
                "-i", str(ruta), "-frames:v", "1", "-vf", f"scale={ancho + 60}:-2", "-q:v", "5", str(medios / archivo)])
        planos.append({"n": n, "ini": round(ini, 2), "fin": round(fin, 2), "imagen": archivo})
    return {"gancho": "gancho.jpg", "hoja": "hoja.jpg", "planos": planos}


def medir_video(ruta: Path, etiqueta: str, archivo: str, umbral: float, con_voz: bool, modelo_voz: str,
                medios: Path, con_planos: bool = True, avance=None, idioma: str | None = None) -> dict | None:
    """Todas las medidas de un video; None si no se puede leer."""
    datos = _sondear(ruta)
    if not datos["duracion"]:
        return None
    cortes = _cortes(ruta, umbral)
    return {
        "id": ruta.stem,
        "tipo": etiqueta,
        "archivo": archivo,
        **{k: datos[k] for k in ("duracion", "ancho", "alto", "fps")},
        "vertical": datos["alto"] > datos["ancho"],
        "ritmo": _ritmo(cortes, datos["duracion"]),
        "audio": _audio(ruta, datos["duracion"]) if datos["tiene_audio"] else None,
        "voz": _voz(ruta, datos["duracion"], modelo_voz, avance, idioma) if con_voz and datos["tiene_audio"] else None,
        "imagenes": _imagenes(ruta, datos, medios, cortes, con_planos),
    }


def analizar(carpeta: Path, umbral: float, con_voz: bool, modelo_voz: str, forzar: bool) -> int:
    destino = carpeta_analisis(carpeta)
    hechos = 0
    for tipo, etiqueta in TIPOS.items():
        for ruta in videos(carpeta, tipo):
            salida = destino / f"{ruta.stem}.analisis.json"
            if salida.exists() and not forzar:
                continue
            print(f"  · {nombre(carpeta)} / {ruta.name}")
            resultado = medir_video(ruta, etiqueta, f"videos/{tipo}/{ruta.name}", umbral, con_voz, modelo_voz,
                                    boveda_empresa(carpeta) / "medios" / seguro(ruta.stem))
            if resultado is None:
                print("    no se pudo leer el video; lo salto")
                continue
            escribir_atomico(salida, json.dumps(resultado, ensure_ascii=False, indent=1))
            hechos += 1
    return hechos
