"""Mezcla final del audio: limpieza de la voz, música que baja cuando se habla y volumen nivelado (EBU R 128, dos pasadas con ffmpeg).

Todo son filtros estándar de ffmpeg; los valores son los usuales en edición de voz para redes y están en un solo lugar para ajustarlos.
No sustituye el oído: es una mezcla correcta y medida, pensada para revisarse."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

import audio
import musica as analisis_musical

OBJETIVO_LUFS = -14.0   # volumen integrado de salida; configurable (la televisión usa −23, las redes suelen estar cerca de −14)
PICO_MAXIMO = -1.0      # dBTP
MUSICA_BAJO_VOZ = 13.0  # la música sin atenuar queda 13 LU por debajo de la voz; al hablar baja unos dB más
RUIDO_DENOISE = -40.0   # si el suelo de ruido de la toma supera esto (dBFS) se aplica un reductor de ruido suave


def piso_de_ruido(ruta: Path, maximo: float = 90.0) -> tuple[float | None, float | None]:
    """(suelo de ruido, nivel de la voz) en dBFS: percentiles 10 y 90 de ventanas de 50 ms. Con pausas, el primero es el ruido de la sala."""
    try:
        y = analisis_musical.decodificar(ruta, hasta=maximo)
    except ValueError:
        return None, None
    n = int(analisis_musical.SR * 0.05)
    trozos = len(y) // n
    if trozos < 20:
        return None, None
    db = 10.0 * np.log10((y[: trozos * n].reshape(trozos, n) ** 2).mean(axis=1) + 1e-12)
    return float(np.percentile(db, 10)), float(np.percentile(db, 90))


def cadena_de_voz(ruido_db: float | None = None, nivel_db: float | None = None) -> str:
    """Filtros de la voz: quitar graves inútiles, reducir ruido solo si hace falta, comprimir y dar presencia."""
    filtros = ["highpass=f=80"]
    hay_pausas = ruido_db is not None and nivel_db is not None and (nivel_db - ruido_db) >= 12.0
    if hay_pausas and ruido_db > RUIDO_DENOISE:
        filtros.append("afftdn=nr=10:nf=-32")
    filtros += ["acompressor=threshold=-21dB:ratio=3:attack=12:release=220:makeup=3", "equalizer=f=3200:t=q:w=1.2:g=2", "aresample=48000"]
    return ",".join(filtros)


def _grafo(cadena: str, duracion: float, ganancia_musica: float | None) -> str:
    """Grafo de filtros. Con música: la voz se divide en dos (una va a la mezcla y otra controla cuánto baja la música)."""
    if ganancia_musica is None:
        return f"[0:a]{cadena},apad,atrim=duration={duracion:.3f}[mix]"
    fin_fundido = max(0.0, duracion - 1.5)
    return (f"[0:a]{cadena},asplit=2[vm][vs];"
            f"[1:a]volume={ganancia_musica:.2f}dB,afade=t=in:st=0:d=0.8,afade=t=out:st={fin_fundido:.3f}:d=1.5,aresample=48000[m0];"
            f"[m0][vs]sidechaincompress=threshold=0.05:ratio=3:attack=15:release=400:makeup=1[md];"
            f"[vm][md]amix=inputs=2:duration=first:normalize=0[mx];"
            f"[mx]apad,atrim=duration={duracion:.3f}[mix]")


def _entradas(voz: Path | None, musica: dict | None) -> list[str]:
    entradas = ["-i", str(voz)] if voz else []
    if musica:
        if musica.get("repetir"):
            entradas += ["-stream_loop", "-1"]
        entradas += ["-ss", f"{musica['inicio']:.3f}", "-i", str(musica["archivo"])]
    return entradas


def masterizar(voz: Path | None, destino: Path, duracion: float, musica: dict | None = None,
               objetivo: float = OBJETIVO_LUFS, pico: float = PICO_MAXIMO) -> dict | None:
    """Escribe el audio final (AAC, 48 kHz) y devuelve lo que hizo. `musica`: {archivo, inicio, repetir, lufs}. None si no hay nada que mezclar."""
    if voz is None and musica is None:
        return None
    informe: dict = {"objetivo_lufs": objetivo, "pico_max": pico, "con_musica": musica is not None, "con_voz": voz is not None}
    if voz is not None:
        ruido, nivel = piso_de_ruido(voz)
        cadena = cadena_de_voz(ruido, nivel)
        informe.update(ruido_db=None if ruido is None else round(ruido, 1), reductor_de_ruido="afftdn" in cadena)
    else:
        cadena = "aresample=48000"
    ganancia = None
    if musica is not None and voz is not None:
        medida_voz = audio.medir(voz, filtro=cadena)
        voz_lufs = medida_voz["lufs"] if medida_voz and medida_voz["lufs"] > -60 else -23.0
        propia = musica.get("lufs") if musica.get("lufs") is not None else -14.0
        ganancia = max(-30.0, min(12.0, (voz_lufs - MUSICA_BAJO_VOZ) - propia))
        informe.update(voz_lufs=round(voz_lufs, 1), musica_ganancia_db=round(ganancia, 1))
    entradas = _entradas(voz, musica)
    if voz is None and musica is not None:  # sin voz: la música sola, a su nivel
        grafo = f"[0:a]afade=t=in:st=0:d=0.8,afade=t=out:st={max(0.0, duracion - 1.5):.3f}:d=1.5,aresample=48000,atrim=duration={duracion:.3f}[mix]"
    else:
        grafo = _grafo(cadena, duracion, ganancia)

    primera = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *entradas, "-filter_complex",
                              f"{grafo};[mix]loudnorm=I={objetivo}:TP={pico}:LRA=11:print_format=json[sal]", "-map", "[sal]", "-f", "null", "-"],
                             capture_output=True, text=True, errors="replace")
    medidas = None
    encontrado = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", primera.stderr, re.S)
    if encontrado:
        try:
            medidas = json.loads(encontrado.group(0))
            if float(medidas["input_i"]) == float("-inf"):
                medidas = None
        except (ValueError, KeyError):
            medidas = None
    if primera.returncode != 0:
        raise RuntimeError("No pude mezclar el audio: " + (primera.stderr.strip().splitlines() or ["error desconocido"])[-1])
    if medidas:
        nivelar = (f"loudnorm=I={objetivo}:TP={pico}:LRA=11:measured_I={medidas['input_i']}:measured_LRA={medidas['input_lra']}:"
                   f"measured_TP={medidas['input_tp']}:measured_thresh={medidas['input_thresh']}:offset={medidas['target_offset']}:linear=true")
        informe["antes_lufs"] = round(float(medidas["input_i"]), 1)
    else:
        nivelar = f"loudnorm=I={objetivo}:TP={pico}:LRA=11"
    segunda = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-nostats", "-v", "error", *entradas, "-filter_complex", f"{grafo};[mix]{nivelar},aresample=48000[sal]",
                              "-map", "[sal]", "-c:a", "aac", "-b:a", "192k", "-t", f"{duracion:.3f}", str(destino)], capture_output=True, text=True, errors="replace")
    if segunda.returncode != 0 or not destino.exists():
        raise RuntimeError("No pude nivelar el audio: " + (segunda.stderr.strip().splitlines() or ["error desconocido"])[-1])
    return informe
