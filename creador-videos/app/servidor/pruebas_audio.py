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
    import musica as analisis_musical

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

        print("Efectos de sonido sintetizados")
        import sonidos

        def banda(y: np.ndarray, desde: float, hasta: float) -> float:
            """Parte de la energía del sonido que cae entre dos frecuencias (0–1)."""
            energia = np.abs(np.fft.rfft(y)) ** 2
            frecuencias = np.fft.rfftfreq(len(y), 1 / sonidos.SR)
            return float(energia[(frecuencias >= desde) & (frecuencias < hasta)].sum() / energia.sum())

        for nombre, funcion in sonidos.EFECTOS.items():
            y = funcion()
            esperado = sonidos.DURACION[nombre]
            ok(np.isfinite(y).all() and abs(float(np.abs(y).max()) - 1.0) < 1e-6 and abs(len(y) / sonidos.SR - esperado) < 0.01 and abs(float(y.mean())) < 0.05,
               f"{nombre}: dura {len(y) / sonidos.SR:.2f} s, pico 1,0, sin continua y sin valores raros")
            ok(np.array_equal(y, funcion()), f"{nombre}: es determinista (siempre suena igual)")
        ok(banda(sonidos.impacto(), 0, 300) > 0.9 and banda(sonidos.brillo(), 2000, 24000) > 0.9 and banda(sonidos.pop(), 300, 1500) > 0.8
           and banda(sonidos.tecla(), 0, 300) < 0.05 and banda(sonidos.tecla(), 1500, 24000) > 0.5 and banda(sonidos.whoosh(), 300, 3000) > 0.5,
           "el carácter de cada sonido: impacto grave, pop medio, tecla seca y brillante, whoosh de medios, brillo agudo")
        ok(sonidos.efecto("caja") is sonidos.efecto("caja"), "los efectos se calculan una sola vez")

        def nivel_rms(y: np.ndarray, a: float, b: float, sr: int = sonidos.SR) -> float:
            trozo = y[int(a * sr): int(b * sr)]
            return float(np.sqrt(np.mean(trozo ** 2)) + 1e-12)

        pista_fx = sonidos.pista([{"t": 1.0, "tipo": "impacto"}, {"t": 3.0, "tipo": "caja"}, {"t": 99.0, "tipo": "pop"}], 5.0)
        ok(len(pista_fx) == 5 * sonidos.SR and abs(float(np.abs(pista_fx).max()) - 1.0) < 1e-6, "la pista mide lo que el video y su pico queda en 1,0 (un evento fuera del video se ignora)")
        ok(nivel_rms(pista_fx, 1.0, 1.1) > 20 * nivel_rms(pista_fx, 2.0, 2.8) and nivel_rms(pista_fx, 3.0, 3.1) > 20 * nivel_rms(pista_fx, 4.5, 5.0), "cada efecto suena en su segundo y hay silencio entre ellos")
        ok(not np.any(sonidos.pista([], 2.0)) and len(sonidos.pista([], 2.0)) == 2 * sonidos.SR, "sin eventos, la pista es silencio")
        guion_fx = {"capas": [{"tipo": "transicion", "estilo": "barrido", "ini": 3.8, "fin": 4.2}, {"tipo": "transicion", "estilo": "impacto", "ini": 8.0, "fin": 8.4},
                              {"tipo": "calculadora", "ini": 1.0, "fin": 12.0, "eventos": [{"t": 1.5, "dur": 1.0, "op": "fijar"}, {"t": 1.53, "dur": 1.0, "op": "fijar"},
                                                                                           {"t": 6.0, "dur": 1.0, "op": "total"}]},
                              {"tipo": "titulo", "ini": 0.2, "fin": 2.0}, {"tipo": "tarjeta", "ini": 9.0, "fin": 11.0}, {"tipo": "logo", "estilo": "cierre", "ini": 12.0, "fin": 13.8},
                              {"tipo": "logo", "estilo": "marca", "ini": 0.5, "fin": 5.0}],
                    "escenas": [{"tipo": "cta", "ini": 11.0, "duracion": 3.0}], "marca": {"logo": "m/logo.png"}}
        sutil = sonidos.eventos_de_guion(guion_fx, "sutil")
        tipos = [(e["tipo"], e["t"]) for e in sutil]
        ok(("whoosh", 3.78) in tipos and ("impacto", 8.2) in tipos, "transiciones: el zumbido llega justo antes del corte y el impacto cae sobre él")
        ok(sum(1 for e in sutil if e["tipo"] == "tecla") == 2 and ("caja", 6.5) in tipos and ("pop", 1.3) in tipos, "calculadora: una tecla por paso (dos casi iguales se funden), caja al confirmar el total, pop al entrar")
        ok(("brillo", 12.45) in tipos and ("brillo", 11.45) in tipos and not any(e["t"] == 0.95 for e in sutil), "logo y cierre con logo: brillo; la marca de agua no suena")
        marcado = sonidos.eventos_de_guion(guion_fx, "marcado")
        ok(not any(e["tipo"] == "pop" and e["t"] == 9.0 for e in sutil) and any(e["tipo"] == "pop" and e["t"] == 9.0 for e in marcado) and any(e["tipo"] == "impacto" and e["t"] == 0.25 for e in marcado),
           "«sutil» deja solo lo esencial; «marcado» suma el golpe del título y los pops de las tarjetas")
        ok([e["t"] for e in marcado] == sorted(e["t"] for e in marcado), "los eventos salen ordenados")

        efectos_wav = base / "efectos.wav"
        sonidos.escribir(sonidos.pista([{"t": 3.6, "tipo": "caja"}, {"t": 6.5, "tipo": "tecla"}], duracion), efectos_wav)
        for nivel in ("sutil", "marcado"):
            destino_fx = base / f"con-efectos-{nivel}.m4a"
            informe_fx = mezcla.masterizar(voz, destino_fx, duracion, None, efectos={"archivo": efectos_wav, "nivel": nivel})
            medida_fx = audio.medir(destino_fx)
            ok(informe_fx["con_efectos"] and abs(medida_fx["lufs"] - mezcla.OBJETIVO_LUFS) <= 1.0 and medida_fx["pico_db"] <= mezcla.PICO_MAXIMO + 0.3,
               f"mezcla con efectos «{nivel}»: {medida_fx['lufs']} LUFS y pico {medida_fx['pico_db']} dBTP dentro de lo esperado")
        sin_fx = base / "sin-efectos.m4a"
        mezcla.masterizar(voz, sin_fx, duracion, None)
        y_sin, y_sutil, y_marcado = (analisis_musical.decodificar(base / n) for n in ("sin-efectos.m4a", "con-efectos-sutil.m4a", "con-efectos-marcado.m4a"))
        sr = analisis_musical.SR
        ok(nivel_rms(y_sutil, 3.6, 3.8, sr) > 4 * nivel_rms(y_sin, 3.6, 3.8, sr), "el efecto se oye en la pausa de la voz (la caja a los 3,6 s, más de 12 dB sobre el silencio)")
        ok(abs(nivel_rms(y_sutil, 0.5, 2.5, sr) / nivel_rms(y_sin, 0.5, 2.5, sr) - 1) < 0.1, "y la voz queda igual donde no hay efectos")
        diferencia = 20 * np.log10(nivel_rms(y_marcado, 3.6, 3.8, sr) / nivel_rms(y_sutil, 3.6, 3.8, sr))
        ok(3.5 < diferencia < 8.5, f"«marcado» suena unos 6 dB más fuerte que «sutil» ({diferencia:.1f} dB)")
        ok(mezcla.masterizar(None, base / "x.m4a", 4.0, None, efectos={"archivo": efectos_wav, "nivel": "sutil"}) is None, "sin voz ni música, los efectos solos no se convierten en un audio")

    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.exit(1 if correr() else 0)
