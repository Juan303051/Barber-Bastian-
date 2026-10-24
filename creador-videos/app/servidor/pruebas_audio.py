"""Pruebas de música, mezcla y control de calidad con audio y video sintéticos de resultado conocido.
Se ejecutan con ./creador probar (o: python -m servidor.pruebas_audio). Necesitan ffmpeg y numpy."""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100


def pista_sintetica(bpm: float, duracion: float = 40.0, desfase: float = 0.35, compases_calmos: int = 4, patron: str = "cuatro") -> tuple[np.ndarray, np.ndarray]:
    """Una canción de juguete: bombo, caja y platillos. Los primeros compases suenan solo los platillos (intro calma) y luego entra todo.
    Devuelve (audio, instantes exactos de cada pulso)."""
    rng = np.random.default_rng(1)
    y = np.zeros(int(SR * duracion))
    periodo = 60.0 / bpm
    t_b = np.arange(0, 0.18, 1 / SR)
    bombo = np.sin(2 * np.pi * (50 * t_b + 100 * (1 - np.exp(-t_b * 25)) / 25)) * np.exp(-t_b * 22)
    t_h = np.arange(0, 0.05, 1 / SR)
    plato = rng.standard_normal(len(t_h)) * np.exp(-t_h * 90) * 0.25
    caja = rng.standard_normal(int(0.14 * SR)) * np.exp(-np.arange(int(0.14 * SR)) / SR * 30) * 0.5
    verdaderos, k = [], 0
    while desfase + k * periodo < duracion - 0.3:
        t = desfase + k * periodo
        i = int(t * SR)
        lleno = k // 4 >= compases_calmos
        if lleno and (k % 4 in (0, 2) if patron == "golpe" else True):
            y[i:i + len(bombo)] += bombo[: len(y) - i] * 0.9
        if lleno and patron == "golpe" and k % 4 in (1, 3):
            y[i:i + len(caja)] += caja[: len(y) - i]
        y[i:i + len(plato)] += plato[: len(y) - i]
        j = int((t + periodo / 2) * SR)
        if j + len(plato) < len(y):
            y[j:j + len(plato)] += plato * (1.0 if lleno else 0.6)
        verdaderos.append(t)
        k += 1
    y += 0.02 * rng.standard_normal(len(y))
    return y / (np.abs(y).max() * 1.05), np.array(verdaderos)


def escribir_wav(y: np.ndarray, ruta: Path) -> None:
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def voz_sintetica(ruta: Path, duracion: float = 8.0) -> None:
    """Una «voz» de juguete: un tono con envolvente de palabras, con una pausa larga en el medio."""
    t = np.arange(int(SR * duracion)) / SR
    habla = ((t % 1.0) < 0.6) & ~((t > 3.0) & (t < 5.0))
    tono = 0.35 * np.sin(2 * np.pi * 180 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.2 * t)) * habla
    escribir_wav(tono + 0.002 * np.random.default_rng(2).standard_normal(len(t)), ruta)


def correr() -> list[str]:
    import audio
    import mezcla
    import musica

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    with tempfile.TemporaryDirectory(prefix="iris-audio-") as carpeta:
        base = Path(carpeta)
        print("Música (pistas sintéticas de tempo conocido)")
        casos = [(100, "cuatro"), (128, "cuatro"), (90, "golpe"), (140, "golpe")]
        errores_fase = []
        for bpm, patron in casos:
            y, verdad = pista_sintetica(bpm, patron=patron)
            ruta = base / f"p{bpm}.wav"
            escribir_wav(y, ruta)
            a = musica.analizar(ruta)
            pulsos = np.array(a["pulsos"])
            fase = float(np.mean([np.min(np.abs(verdad - p)) for p in pulsos])) * 1000
            errores_fase.append(fase)
            ok(abs(a["bpm"] - bpm) / bpm < 0.015, f"{bpm} BPM ({patron}): midió {a['bpm']}")
            ok(a["confianza"] >= 0.6, f"{bpm} BPM: confianza {a['confianza']:.0%}")
            esperada = 0.35 + 16 * 60 / bpm
            ok(any(abs(c - esperada) <= 1.0 for c in a["caidas"]), f"{bpm} BPM: detecta la entrada del ritmo cerca de {esperada:.1f} s ({a['caidas']})")
        ok(max(errores_fase) < 40, f"el pulso cae a menos de 40 ms del real (peor caso {max(errores_fase):.0f} ms)")

        a = musica.analizar(base / "p128.wav")
        entrada = musica.punto_de_entrada(a, 12.0)
        ok(entrada["inicio"] in a["tiempos_fuertes"] or entrada["inicio"] in a["pulsos"], "la canción entra en un tiempo fuerte")
        ok(musica.pulso_mas_cercano(5.01, a["pulsos"], 0.15) in a["pulsos"] and musica.pulso_mas_cercano(5.01, [], 0.15) == 5.01, "ajustar un instante al pulso más cercano")
        pista = musica.elegir_pista([{"id": "a", "analisis": a}], "alta", "medio")
        ok(pista is not None and pista["id"] == "a" and musica.elegir_pista([], "alta", "medio") is None, "elegir pista de la biblioteca")
        otra = {**a, "intensidad": "media", "confianza": 0.9}
        sin = {**a, "intensidad": "alta", "confianza": 0.9}
        con_licencia = musica.elegir_pista([{"id": "x", "licencia": "sin-confirmar", "analisis": sin}, {"id": "y", "licencia": "licenciada", "analisis": otra}], "alta", "medio")
        solo_sin = musica.elegir_pista([{"id": "x", "licencia": "sin-confirmar", "analisis": sin}], "alta", "medio")
        ok(con_licencia["id"] == "y" and solo_sin["id"] == "x", "entre dos canciones parecidas, gana la que tiene licencia declarada; si solo hay una sin licencia, se usa y se avisa")
        # cortes sobre el pulso frente a cortes al azar
        sobre = [a["pulsos"][i] + 0.02 for i in range(4, 40, 3)]
        azar = list(np.random.default_rng(7).uniform(2, 38, len(sobre)))
        fase_sobre = musica.fase_de_cortes(sobre, a["pulsos"], (1.0,))[0]
        fase_azar = musica.fase_de_cortes(azar, a["pulsos"], (1.0,))[0]
        ok(fase_sobre["r"] > 0.9 and fase_sobre["p"] < 0.001, f"cortes sobre el pulso: r={fase_sobre['r']} p={fase_sobre['p']}")
        ok(fase_azar["p"] > 0.01, f"cortes al azar no parecen sobre el pulso: p={fase_azar['p']}")
        escribir_wav(0.2 * np.random.default_rng(3).standard_normal(SR * 12), base / "ruido.wav")
        try:
            r = musica.analizar(base / "ruido.wav")
            ok(r["confianza"] < 0.6, f"ruido blanco: confianza baja ({r['confianza']:.0%})")
        except ValueError:
            ok(True, "ruido blanco: se rechaza con un mensaje claro")
        escribir_wav(0.3 * np.sin(2 * np.pi * 440 * np.arange(SR * 3) / SR), base / "corta.wav")
        try:
            musica.analizar(base / "corta.wav")
            ok(False, "una pista de 3 s se rechaza")
        except ValueError as error:
            ok("8 segundos" in str(error), "una pista de 3 s se rechaza con un mensaje claro")
        (base / "falso.mp3").write_bytes(b"no es audio")
        try:
            musica.analizar(base / "falso.mp3")
            ok(False, "un archivo que no es audio se rechaza")
        except ValueError:
            ok(True, "un archivo que no es audio se rechaza con un mensaje claro")

        print("Mezcla (voz + música con ducking + volumen)")
        voz = base / "voz.wav"
        voz_sintetica(voz)
        duracion = audio.duracion(voz)
        cancion = {"archivo": base / "p100.wav", "inicio": 0.35, "repetir": False, "lufs": audio.medir(base / "p100.wav")["lufs"]}
        destino = base / "mezcla.m4a"
        informe = mezcla.masterizar(voz, destino, duracion, cancion)
        medida = audio.medir(destino)
        ok(informe is not None and abs(medida["lufs"] - mezcla.OBJETIVO_LUFS) <= 1.0, f"volumen final {medida['lufs']} LUFS (objetivo {mezcla.OBJETIVO_LUFS:.0f}, tolerancia 1)")
        ok(medida["pico_db"] <= mezcla.PICO_MAXIMO + 0.3, f"pico real {medida['pico_db']} dBTP (máximo {mezcla.PICO_MAXIMO})")
        ok(abs(audio.duracion(destino) - duracion) < 0.15, f"dura lo mismo que el video ({audio.duracion(destino):.2f} s)")
        # la música baja mientras se habla y vuelve en la pausa
        voz_cadena = mezcla.cadena_de_voz()
        grafo = (f"[0:a]{voz_cadena},asplit=2[vm][vs];[1:a]volume={informe['musica_ganancia_db']}dB,aresample=48000[m0];"
                 "[m0][vs]sidechaincompress=threshold=0.05:ratio=3:attack=15:release=400:makeup=1[md];[vm]anullsink")
        sola, bajada = base / "sola.wav", base / "bajada.wav"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(voz), "-ss", "0.35", "-t", f"{duracion}", "-i", str(base / "p100.wav"), "-filter_complex", grafo, "-map", "[md]", str(bajada)], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "0.35", "-t", f"{duracion}", "-i", str(base / "p100.wav"), "-af", f"volume={informe['musica_ganancia_db']}dB", str(sola)], check=True)

        def nivel(ruta: Path, a: float, b: float) -> float:
            r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", str(a), "-t", str(b - a), "-i", str(ruta), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
            return float(re.search(r"mean_volume: (-?[0-9.]+) dB", r.stderr).group(1))
        baja = nivel(bajada, 0.5, 2.7) - nivel(sola, 0.5, 2.7)
        vuelve = nivel(bajada, 4.0, 4.8) - nivel(sola, 4.0, 4.8)
        ok(baja <= -6.0, f"la música baja {abs(baja):.1f} dB mientras se habla")
        ok(vuelve >= -1.5, f"y vuelve a su nivel en la pausa ({vuelve:+.1f} dB)")
        solo_voz = base / "solo-voz.m4a"
        mezcla.masterizar(voz, solo_voz, duracion, None)
        ok(abs(audio.medir(solo_voz)["lufs"] - mezcla.OBJETIVO_LUFS) <= 1.0, "sin música también queda al volumen objetivo")
        ok(mezcla.masterizar(None, base / "nada.m4a", 5.0, None) is None, "sin voz ni música no se inventa audio")
        ruidosa = "afftdn" in mezcla.cadena_de_voz(-30.0, -12.0) and "afftdn" not in mezcla.cadena_de_voz(-60.0, -12.0) and "afftdn" not in mezcla.cadena_de_voz(-30.0, -29.0)
        ok(ruidosa, "el reductor de ruido solo se activa con ruido de fondo y pausas que lo demuestren")

    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.exit(1 if correr() else 0)
