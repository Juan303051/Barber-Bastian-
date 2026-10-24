"""Lo que Iris aprende de un video de referencia: ritmo, voz, formato y color dominante."""
from __future__ import annotations

import colorsys
import statistics
import subprocess
from pathlib import Path


def color_dominante(video: Path, duracion: float) -> str | None:
    """Color vivo más frecuente en seis fotogramas repartidos. None si el video casi no tiene color."""
    cubos: dict[int, list[float]] = {}
    for k in range(6):
        instante = max(0.0, duracion * (k + 0.5) / 6)
        salida = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{instante:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=32:32",
                                 "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        for i in range(0, len(salida) - 2, 3):
            r, g, b = salida[i] / 255, salida[i + 1] / 255, salida[i + 2] / 255
            tono, saturacion, valor = colorsys.rgb_to_hsv(r, g, b)
            if saturacion > 0.55 and valor > 0.5:
                acumulado = cubos.setdefault(int(tono * 12) % 12, [0.0, 0.0, 0.0, 0.0])
                acumulado[0] += saturacion
                acumulado[1] += r
                acumulado[2] += g
                acumulado[3] += b
    if not cubos:
        return None
    peso, r, g, b = max(cubos.values(), key=lambda c: c[0])
    cantidad = peso / 0.8
    return "#{:02X}{:02X}{:02X}".format(*(round(255 * c / cantidad) if cantidad else 0 for c in (r, g, b)))


def perfil_de(analisis: dict, acento: str | None) -> dict:
    ritmo = analisis["ritmo"]["cortes_por_10s"] or 0
    voz = analisis.get("voz") or {}
    ppm = voz.get("palabras_por_min")
    etiquetas = ["Vertical" if analisis.get("vertical") else "Horizontal", f"{round(analisis['duracion'])} s"]
    etiquetas.append("Ritmo rápido" if ritmo >= 3 else "Ritmo medio" if ritmo >= 1 else "Ritmo pausado")
    if ppm:
        etiquetas.append(("Voz ágil" if ppm > 170 else "Voz natural" if ppm >= 110 else "Voz calmada") + f" · {ppm} palabras por minuto")
    return {"ritmo": ritmo, "ppm": ppm, "vertical": bool(analisis.get("vertical")), "duracion": analisis["duracion"],
            "gancho": voz.get("gancho_texto") or "", "acento": acento,
            "maxPalabras": 2 if (ppm or 0) >= 190 else 3, "zoom_cada": 1 if ritmo >= 3 else 2, "etiquetas": etiquetas}


def agregar(perfiles: list[dict]) -> dict | None:
    """Perfil común de las referencias activas: la mediana de lo medible y el primer color encontrado."""
    perfiles = [p for p in perfiles if p]
    if not perfiles:
        return None
    ppm = [p["ppm"] for p in perfiles if p.get("ppm")]
    ritmo = statistics.median(p["ritmo"] for p in perfiles)
    ppm_mediana = round(statistics.median(ppm)) if ppm else None
    return {"cantidad": len(perfiles), "ritmo": ritmo, "ppm": ppm_mediana,
            "maxPalabras": 2 if (ppm_mediana or 0) >= 190 else 3, "zoom_cada": 1 if ritmo >= 3 else 2,
            "acento": next((p["acento"] for p in perfiles if p.get("acento")), None)}
