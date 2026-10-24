"""Control de calidad automático: mide el video terminado y avisa de lo que una persona revisaría antes de publicar.
Solo informa lo que se puede medir (volumen, pico, negros, imagen congelada, zonas seguras, gancho, texto sin respaldo, licencia de la música);
no juzga el gusto. Cada prueba es `ok`, `aviso` o `error`; el veredicto es el peor de ellos."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import audio
import mezcla

from .direccion import plan as planes
from .direccion import rubrica

LICENCIAS = {
    "propia": "Música propia",
    "licenciada": "Licencia comercial comprada",
    "plataforma": "De la biblioteca de la plataforma",
    "sin-confirmar": "Licencia sin confirmar",
}


def _sondear(ruta: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0", str(ruta)], capture_output=True, text=True)
    ancho = alto = 0
    for linea in r.stdout.splitlines():
        partes = linea.split(",")
        if partes[0] == "video" and len(partes) >= 3 and partes[1].isdigit():
            ancho, alto = int(partes[1]), int(partes[2])
    return {"ancho": ancho, "alto": alto, "audio": "audio" in r.stdout}


def _negros_y_congelados(ruta: Path, duracion: float) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(ruta), "-an", "-vf", "blackdetect=d=0.3:pix_th=0.10,freezedetect=n=-60dB:d=1.5",
                        "-f", "null", "-"], capture_output=True, text=True, errors="replace")
    negros = [(float(a), float(b)) for a, b in re.findall(r"black_start:([0-9.]+) black_end:([0-9.]+)", r.stderr)]
    inicios = [float(x) for x in re.findall(r"freeze_start: ([0-9.]+)", r.stderr)]
    duraciones = [float(x) for x in re.findall(r"freeze_duration: ([0-9.]+)", r.stderr)]
    # una imagen que sigue congelada hasta el final del video no imprime duración: llega hasta el final
    return negros, [(ini, ini + duraciones[k] if k < len(duraciones) else duracion) for k, ini in enumerate(inicios)]


def revisar(video: Path, guion: dict, contexto: dict, plan: dict, musica: dict | None, borrador: bool, objetivo: float = mezcla.OBJETIVO_LUFS) -> dict:
    """Devuelve {"veredicto": "listo"|"revisar"|"error", "resumen": str, "pruebas": [{id, nivel, texto}]}."""
    pruebas: list[dict] = []

    def anotar(id_: str, nivel: str, texto: str) -> None:
        pruebas.append({"id": id_, "nivel": nivel, "texto": texto})

    sonda = _sondear(video)
    duracion = audio.duracion(video)
    medida = audio.medir(video) if sonda["audio"] else None
    if medida is None:
        anotar("volumen", "aviso", "El video no tiene audio.")
    else:
        desvio = abs(medida["lufs"] - objetivo)
        anotar("volumen", "ok" if desvio <= 1.0 else "aviso" if desvio <= 2.5 else "error",
               f"Volumen {medida['lufs']:.1f} LUFS (objetivo {objetivo:.0f})" + ("" if desvio <= 1.0 else ": fuera del rango esperado"))
        pico = medida["pico_db"]
        if pico is not None:
            anotar("pico", "ok" if pico <= -1.0 else "aviso" if pico <= -0.3 else "error",
                   f"Pico {pico:.1f} dBTP" + ("" if pico <= -1.0 else ": puede distorsionar al subirlo a una red"))
        if medida["rango_lu"] is not None and medida["rango_lu"] > 14:
            anotar("rango", "aviso", f"El volumen varía mucho ({medida['rango_lu']:.0f} LU): revisa si hay partes muy bajas.")
        silencio_inicial = next((fin for ini, fin in medida["silencios"] if ini <= 0.2 and (fin or 0) > 0.8), None)
        anotar("arranque", "aviso" if silencio_inicial else "ok",
               f"El video arranca en silencio durante {silencio_inicial:.1f} s." if silencio_inicial else "Arranca con sonido, sin silencio muerto")

    negros, congelados = _negros_y_congelados(video, duracion)
    if negros:
        grave = negros[0][0] < 0.5 and negros[0][1] - negros[0][0] >= 0.5
        anotar("negros", "error" if grave else "aviso", f"Hay {len(negros)} tramo(s) en negro (el primero a los {negros[0][0]:.1f} s).")
    else:
        anotar("negros", "ok", "Sin fotogramas en negro")
    anotar("congelado", "aviso" if congelados else "ok",
           f"La imagen se queda congelada {congelados[0][1] - congelados[0][0]:.1f} s desde el segundo {congelados[0][0]:.1f}." if congelados else "Sin imagen congelada")

    if sonda["ancho"] and sonda["alto"]:
        vertical = sonda["alto"] >= sonda["ancho"]
        if borrador:
            anotar("tamano", "aviso", f"Es un borrador de {sonda['ancho']}×{sonda['alto']}: para publicar, créalo sin «Borrador rápido».")
        elif not vertical:
            anotar("tamano", "aviso", "El video es horizontal: en Reels y TikTok se verá con bandas.")
        elif min(sonda["ancho"], sonda["alto"]) < 540:
            anotar("tamano", "aviso", f"{sonda['ancho']}×{sonda['alto']} es poco: TikTok pide al menos 540×960.")
        else:
            anotar("tamano", "ok", f"{sonda['ancho']}×{sonda['alto']}, vertical")
    if duracion > 60:
        anotar("duracion", "aviso", f"Dura {duracion:.0f} s: algunos formatos de anuncio no pasan de 60 s (TikTok).")

    # Lo que sale del guion y del plan
    resultados = {r["id"]: r for r in rubrica.evaluar(plan, guion, contexto)}
    anotar("gancho", "ok" if resultados["gancho_en_3s"]["ok"] else "aviso",
           "Hay mensaje en los 3 primeros segundos" if resultados["gancho_en_3s"]["ok"] else "No hay texto ni voz en los 3 primeros segundos: Meta y TikTok recomiendan el mensaje desde el inicio.")
    anotar("zona_segura", "ok" if resultados["zona_segura"]["ok"] else "aviso",
           "El texto queda fuera de las franjas que tapa la aplicación" if resultados["zona_segura"]["ok"] else "Hay texto en la franja de arriba (14 %) o de abajo (35 %), donde la aplicación pone su interfaz.")
    cifras_mal = not (resultados["sin_cifras_inventadas"]["ok"] and resultados["contadores_dichos"]["ok"])
    anotar("cifras", "error" if cifras_mal else "ok", "Hay una cifra en pantalla que no se dice en el video ni está en el brief." if cifras_mal else "Todas las cifras en pantalla salen de tu video")
    if not resultados["texto_respaldado"]["ok"]:
        anotar("texto", "aviso", "Hay un texto en pantalla que no sale de lo dicho ni del brief: revísalo.")
    if not resultados["sin_prohibidas"]["ok"]:
        anotar("prohibidas", "error", "Aparece una palabra que la marca dijo que nunca debe aparecer.")
    for alerta in plan.get("alertas", []):
        anotar("director", "aviso", f"El director avisa: {alerta}")

    if musica:
        licencia = musica.get("licencia", "sin-confirmar")
        anotar("licencia", "aviso" if licencia == "sin-confirmar" else "ok",
               f"Música «{musica['titulo']}»: " + ("la licencia está sin confirmar. No lo publiques hasta confirmarla." if licencia == "sin-confirmar" else LICENCIAS.get(licencia, licencia)))
        if musica.get("confianza", 1.0) < 0.55 and guion.get("pulso") is None:
            anotar("pulso", "aviso", "El pulso de la canción es poco claro: los acercamientos no se apoyaron en la música.")

    orden = {"ok": 0, "aviso": 1, "error": 2}
    peor = max((orden[p["nivel"]] for p in pruebas), default=0)
    veredicto = ["listo", "revisar", "error"][peor]
    errores = sum(1 for p in pruebas if p["nivel"] == "error")
    avisos = sum(1 for p in pruebas if p["nivel"] == "aviso")
    resumen = ("Listo para revisar: todo lo medible está en orden." if veredicto == "listo"
               else f"{errores} problema(s) a corregir y {avisos} aviso(s)." if errores else f"{avisos} aviso(s) para revisar antes de publicar.")
    return {"veredicto": veredicto, "resumen": resumen, "pruebas": pruebas}
