"""Análisis de una canción con medidas, no con el oído: tempo, pulsos, tiempos fuertes del compás, energía, secciones y caídas.
Solo usa numpy y ffmpeg. Método: fuerza de ataques (flujo espectral) → tempo por autocorrelación → pulsos por programación dinámica
(Ellis, «Beat Tracking by Dynamic Programming», Journal of New Music Research 36(1), 2007).
Es una estimación: dice cuánta confianza tiene y no sustituye escuchar la pista."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

import audio

SR = 22050
NFFT = 1024
HOP = 256
FR = SR / HOP  # cuadros de análisis por segundo
LATENCIA = 0.0  # se calibra con pulsos sintéticos (ver pruebas)


def decodificar(ruta: Path, hasta: float | None = None) -> np.ndarray:
    import subprocess
    comando = ["ffmpeg", "-v", "error", "-i", str(ruta), "-vn", "-ac", "1", "-ar", str(SR)]
    if hasta:
        comando += ["-t", f"{hasta:.2f}"]
    resultado = subprocess.run(comando + ["-f", "f32le", "-"], capture_output=True)
    if resultado.returncode != 0 or not resultado.stdout:
        raise ValueError("No pude leer el audio de ese archivo.")
    return np.frombuffer(resultado.stdout, dtype=np.float32).copy()


def _banco_mel(bandas: int = 40, fmin: float = 30.0, fmax: float = 8000.0) -> tuple[np.ndarray, np.ndarray]:
    a_mel = lambda f: 2595.0 * np.log10(1.0 + f / 700.0)
    de_mel = lambda m: 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    puntos = de_mel(np.linspace(a_mel(fmin), a_mel(fmax), bandas + 2))
    frecuencias = np.fft.rfftfreq(NFFT, 1.0 / SR)
    banco = np.zeros((bandas, len(frecuencias)), dtype=np.float32)
    for i in range(bandas):
        a, b, c = puntos[i], puntos[i + 1], puntos[i + 2]
        banco[i] = np.maximum(0.0, np.minimum((frecuencias - a) / (b - a), (c - frecuencias) / (c - b)))
    return banco, puntos[1:-1]


def _espectro_mel(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Espectrograma en dB por bandas mel: (cuadros × bandas) y el centro de cada banda en Hz."""
    banco, centros = _banco_mel()
    relleno = np.pad(y, (NFFT // 2, NFFT // 2), mode="reflect") if len(y) > NFFT else np.pad(y, (NFFT, NFFT))
    cuadros = 1 + (len(relleno) - NFFT) // HOP
    ventana = np.hanning(NFFT).astype(np.float32)
    ventanas = np.lib.stride_tricks.sliding_window_view(relleno, NFFT)[::HOP][:cuadros]
    trozos = []
    for i in range(0, cuadros, 2048):  # por partes para no gastar memoria con canciones largas
        magnitud = np.abs(np.fft.rfft(ventanas[i:i + 2048] * ventana, axis=1)) ** 2
        trozos.append(magnitud @ banco.T)
    mel = np.concatenate(trozos, axis=0)
    db = 10.0 * np.log10(mel + 1e-10)
    return np.maximum(db, db.max() - 80.0), centros


def _ataques(db: np.ndarray, bandas: slice | None = None) -> np.ndarray:
    """Fuerza de los ataques: suma de los aumentos de energía entre cuadros."""
    parte = db if bandas is None else db[:, bandas]
    flujo = np.maximum(0.0, np.diff(parte, axis=0, prepend=parte[:1])).mean(axis=1)
    return np.convolve(flujo, np.hanning(3) / np.hanning(3).sum(), mode="same")


def _autocorrelacion(ataques: np.ndarray) -> np.ndarray:
    o = ataques - ataques.mean()
    n = len(o)
    if n < int(FR * 4) or not np.any(o):
        raise ValueError("La pista es demasiado corta o plana para medir el tempo.")
    f = np.fft.rfft(o, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    return ac / (ac[0] + 1e-12)


def _prior(bpm: float) -> float:
    """Preferencia suave por los tempos más habituales (centrada en 115 BPM, ancho de una octava)."""
    return float(np.exp(-0.5 * (np.log2(bpm / 115.0) / 1.0) ** 2))


def _candidatos(ac: np.ndarray) -> list[float]:
    """Tempos posibles: los picos más fuertes de la autocorrelación y sus mitades y dobles."""
    n = len(ac)
    lags = np.arange(1, n)
    bpm = 60.0 * FR / lags
    doble = np.zeros(n - 1)
    sirve = lags * 2 < n
    doble[sirve] = ac[(lags * 2)[sirve]]
    base = ac[1:] + 0.5 * doble
    base[(bpm < 45) | (bpm > 220)] = -np.inf
    picos = np.flatnonzero((base[1:-1] > base[:-2]) & (base[1:-1] >= base[2:])) + 1
    picos = picos[np.argsort(base[picos])[::-1]][:5]
    candidatos: list[float] = []
    for i in picos:
        lag = float(i + 1)
        if 1 <= i < len(ac) - 3:
            y0, y1, y2 = ac[i], ac[i + 1], ac[i + 2]
            denom = y0 - 2 * y1 + y2
            lag += float(np.clip(0.5 * (y0 - y2) / denom, -1, 1)) if abs(denom) > 1e-12 else 0.0
        for factor in (1.0, 0.5, 2.0):
            b = 60.0 * FR / lag * factor
            if 55 <= b <= 200 and all(abs(b - c) / c > 0.03 for c in candidatos):
                candidatos.append(b)
    return candidatos


def _tempo(ataques: np.ndarray) -> tuple[float, float, np.ndarray]:
    """Elige el tempo cuyos pulsos caen sobre los ataques más fuertes (con leve preferencia por los tempos habituales).
    Devuelve (bpm, prominencia, pulsos en cuadros)."""
    ac = _autocorrelacion(ataques)
    candidatos = _candidatos(ac)
    if not candidatos:
        raise ValueError("No encontré un pulso claro en esta pista.")
    normal = ataques / (ataques.std() + 1e-9)
    mejor = None
    for bpm in candidatos:
        pulsos = _pulsos(ataques, bpm)
        if len(pulsos) < 6:
            continue
        fuerza = float(np.mean(normal[pulsos]))
        calidad = fuerza * _prior(bpm)
        if mejor is None or calidad > mejor[0]:
            mejor = (calidad, bpm, pulsos)
    if mejor is None:
        raise ValueError("No encontré un pulso claro en esta pista.")
    _, bpm, pulsos = mejor
    rango = (60.0 * FR / np.arange(1, len(ac))) 
    valido = ac[1:][(rango >= 55) & (rango <= 200)]
    lag = int(round(60.0 * FR / bpm))
    prominencia = float((ac[min(lag, len(ac) - 1)] - valido.mean()) / (valido.std() + 1e-9))
    return bpm, prominencia, pulsos


def _pulsos(ataques: np.ndarray, bpm: float, rigidez: float = 100.0) -> np.ndarray:
    """Posición (en cuadros) de cada pulso: la secuencia a intervalo casi constante que cae sobre los ataques más fuertes."""
    periodo = 60.0 * FR / bpm
    ventana = np.exp(-0.5 * (np.arange(-round(periodo), round(periodo) + 1) * 32.0 / periodo) ** 2)
    local = np.convolve(ataques / (ataques.std() + 1e-9), ventana, mode="same")
    n = len(local)
    acumulado = local.copy()
    enlace = np.full(n, -1, dtype=np.int64)
    distancias = np.arange(max(1, round(periodo / 2)), round(periodo * 2) + 1)
    penal = rigidez * (np.log(distancias) - np.log(periodo)) ** 2
    primero = True
    for i in range(n):
        previos = i - distancias
        valido = previos >= 0
        mejor, donde = -np.inf, -1
        if valido.any():
            candidatos = acumulado[previos[valido]] - penal[valido]
            k = int(np.argmax(candidatos))
            mejor, donde = float(candidatos[k]), int(previos[valido][k])
        acumulado[i] = local[i] + (mejor if donde >= 0 else 0.0)
        if primero and local[i] < 0.01 * local.max():
            enlace[i] = -1
        else:
            enlace[i] = donde
            primero = False
    # último pulso: el último máximo local con puntaje decente
    maximos = np.flatnonzero((acumulado[1:-1] > acumulado[:-2]) & (acumulado[1:-1] >= acumulado[2:])) + 1
    if len(maximos) == 0:
        maximos = np.array([int(np.argmax(acumulado))])
    umbral = 0.5 * np.median(acumulado[maximos])
    ultimo = int(maximos[np.flatnonzero(acumulado[maximos] >= umbral)[-1]])
    pulsos = [ultimo]
    while enlace[pulsos[-1]] >= 0:
        pulsos.append(int(enlace[pulsos[-1]]))
    pulsos = np.array(pulsos[::-1])
    # recorta los extremos donde casi no hay ataque (silencio o cola)
    fuerza = local[pulsos]
    corte = 0.5 * np.sqrt(np.mean(fuerza ** 2))
    util = np.flatnonzero(fuerza >= corte)
    return pulsos[util[0]:util[-1] + 1] if len(util) else pulsos


def _tiempos_fuertes(pulsos: np.ndarray, graves: np.ndarray) -> tuple[np.ndarray, float]:
    """Asume compás de 4 tiempos y escoge cuál de los 4 pulsos cae en el bombo/graves más fuerte. Devuelve (índices de pulso, claridad 0–1)."""
    if len(pulsos) < 8:
        return np.arange(0, len(pulsos), 4), 0.0
    energia = np.array([graves[pulsos[k::4]].mean() for k in range(4)])
    mejor = int(np.argmax(energia))
    resto = np.delete(energia, mejor)
    claridad = float(np.clip((energia[mejor] - resto.mean()) / (energia[mejor] + 1e-9), 0, 1))
    return np.arange(mejor, len(pulsos), 4), claridad


def _energia(y: np.ndarray, ventana: float = 0.25) -> np.ndarray:
    n = int(SR * ventana)
    trozos = len(y) // n
    if trozos == 0:
        return np.array([-80.0])
    cuadrados = (y[:trozos * n].reshape(trozos, n) ** 2).mean(axis=1)
    return 10.0 * np.log10(cuadrados + 1e-10)


def _secciones(compases_t: np.ndarray, pulsos_t: np.ndarray, energia_db: np.ndarray, ventana: float, duracion: float) -> tuple[list[dict], list[float]]:
    """Secciones por cambios de energía entre compases. «Caída» = salto brusco hacia una sección fuerte."""
    if len(compases_t) < 6:
        return [{"ini": 0.0, "fin": round(duracion, 2), "nivel": "medio", "db": round(float(np.mean(energia_db)), 1)}], []
    def en(a, b):
        i, j = int(a / ventana), max(int(a / ventana) + 1, int(b / ventana))
        return float(np.mean(energia_db[i:j])) if i < len(energia_db) else -80.0
    def afinar(tiempo: float) -> float:
        """El pulso, a menos de un compás del límite, donde más sube la energía (1 s después frente a 1 s antes)."""
        compas = float(np.median(np.diff(compases_t))) if len(compases_t) > 1 else 2.0
        cerca = [p for p in pulsos_t if abs(p - tiempo) <= compas]
        if not cerca:
            return tiempo
        return float(max(cerca, key=lambda p: en(p, p + 1.0) - en(max(0.0, p - 1.0), p)))
    limites = [0.0] + list(compases_t[1:]) + [duracion]
    por_compas = np.array([en(a, b) for a, b in zip(limites, limites[1:])])
    n = len(por_compas)
    cambio = np.zeros(n)
    for k in range(2, n - 1):
        cambio[k] = abs(por_compas[k:k + 2].mean() - por_compas[max(0, k - 2):k].mean())
    cambios = [0]
    for k in np.argsort(cambio)[::-1]:
        if cambio[k] < 3.0:
            break
        if all(abs(int(k) - c) >= 2 for c in cambios):
            cambios.append(int(k))
    cambios.sort()
    medias = [float(por_compas[a:b].mean()) for a, b in zip(cambios, cambios[1:] + [n])]
    techo = max(medias)
    inicios = [0.0] + [afinar(float(limites[a])) for a in cambios[1:]] + [duracion]
    secciones = []
    for i, nivel_db in enumerate(medias):
        nivel = "alto" if nivel_db >= techo - 3.0 else "bajo" if nivel_db <= techo - 6.0 else "medio"
        secciones.append({"ini": round(inicios[i], 2), "fin": round(inicios[i + 1], 2), "nivel": nivel, "db": round(nivel_db, 1)})
    caidas = [actual["ini"] for anterior, actual in zip(secciones, secciones[1:])
              if actual["nivel"] == "alto" and anterior["nivel"] != "alto" and actual["db"] - anterior["db"] >= 4.0]
    return secciones, caidas


def analizar(ruta: Path, maximo: float = 600.0) -> dict:
    """Analiza una pista (hasta `maximo` segundos). Lanza ValueError con un mensaje claro si no se puede."""
    y = decodificar(ruta, hasta=maximo)
    duracion = len(y) / SR
    if duracion < 8:
        raise ValueError("La pista dura menos de 8 segundos: es muy corta para medir el pulso.")
    db, centros = _espectro_mel(y)
    ataques = _ataques(db)
    graves = _ataques(db, slice(0, int(np.searchsorted(centros, 200.0))))
    bpm_inicial, prominencia, pulsos_cuadros = _tempo(ataques)
    tiempos = pulsos_cuadros * HOP / SR - LATENCIA
    if len(tiempos) >= 8:
        ajuste = np.polyfit(np.arange(len(tiempos)), tiempos, 1)
        bpm = float(60.0 / ajuste[0])
        desvio = float(np.std(tiempos - np.polyval(ajuste, np.arange(len(tiempos)))))
    else:
        bpm, desvio = bpm_inicial, 1.0
    fuertes_idx, claridad = _tiempos_fuertes(pulsos_cuadros, graves)
    fuertes = tiempos[fuertes_idx]
    mediana_ataque = float(np.median(ataques))
    sobre = float(np.mean(ataques[pulsos_cuadros] > 1.5 * mediana_ataque)) if len(pulsos_cuadros) else 0.0
    # confianza: pulsos sobre ataques claros, regularidad del intervalo y prominencia del tempo (heurística, 0–1)
    regular = float(np.clip(1.0 - desvio / 0.06, 0, 1))
    confianza = round(float(np.clip(0.45 * sobre + 0.35 * regular + 0.20 * np.clip(prominencia / 6.0, 0, 1), 0, 1)), 2)
    energia = _energia(y)
    secciones, caidas = _secciones(fuertes, tiempos, energia, 0.25, duracion)
    volumen = audio.medir(ruta)
    medio = float(np.mean(energia))
    return {
        "archivo": ruta.name,
        "duracion": round(duracion, 2),
        "bpm": round(bpm, 1),
        "bpm_alternativos": [round(bpm / 2, 1), round(bpm * 2, 1)],
        "confianza": confianza,
        "compas": 4,
        "claridad_compas": round(claridad, 2),
        "pulsos": [round(float(t), 3) for t in tiempos],
        "tiempos_fuertes": [round(float(t), 3) for t in fuertes],
        "energia_db": [round(float(e), 1) for e in energia],
        "energia_ventana_s": 0.25,
        "secciones": secciones,
        "caidas": [round(c, 2) for c in caidas],
        "volumen": {"lufs": volumen["lufs"], "pico_db": volumen["pico_db"], "rango_lu": volumen["rango_lu"]} if volumen else None,
        "ritmo": "lento" if bpm < 90 else "medio" if bpm < 125 else "rápido",
        "intensidad": "baja" if medio < -26 else "media" if medio < -18 else "alta",
    }


# ------------------------------------------------------------------------------------------------------------------
# Usar el pulso al editar
# ------------------------------------------------------------------------------------------------------------------

def pulso_mas_cercano(t: float, pulsos: list[float], tolerancia: float = 0.15) -> float:
    """El pulso más cercano a `t` si está dentro de la tolerancia; si no, `t` sin cambios."""
    if not pulsos:
        return t
    mejor = min(pulsos, key=lambda p: abs(p - t))
    return mejor if abs(mejor - t) <= tolerancia else t


def alineacion_de_cortes(cortes: list[float], pulsos: list[float], tolerancia: float = 0.08) -> dict:
    """Qué parte de los cortes cae sobre un pulso, comparada con la que caería por azar."""
    if len(cortes) < 3 or len(pulsos) < 4:
        return {"n": len(cortes), "sobre_pulso": None, "azar": None, "ventaja": None}
    periodo = float(np.median(np.diff(pulsos)))
    sobre = sum(1 for c in cortes if abs(pulso_mas_cercano(c, pulsos, tolerancia) - c) <= tolerancia and any(abs(p - c) <= tolerancia for p in pulsos))
    azar = min(1.0, 2 * tolerancia / periodo)
    return {"n": len(cortes), "sobre_pulso": round(sobre / len(cortes), 2), "azar": round(azar, 2),
            "ventaja": round((sobre / len(cortes)) / azar, 1) if azar else None}


def fase_de_cortes(cortes: list[float], pulsos: list[float], multiplos: tuple[float, ...] = (1.0, 2.0)) -> list[dict]:
    """¿Los cortes siguen el pulso con un desfase constante? Estadística circular (prueba de Rayleigh) para cada múltiplo del periodo.
    La fase de cada corte se mide contra los pulsos realmente detectados (no contra una rejilla perfecta, que se desajusta con el tiempo).
    `r` va de 0 (azar) a 1 (siempre en la misma fase); `p` es la probabilidad de ver ese `r` por azar. Con pocos cortes o `p` alto, no hay evidencia."""
    pulsos = list(pulsos)
    if len(cortes) < 5 or len(pulsos) < 8:
        return []
    arreglo = np.array(pulsos)
    resultado = []
    for multiplo in multiplos:
        fases, usados = [], 0
        for c in cortes:
            k = int(np.searchsorted(arreglo, c, side="right")) - 1
            if k < 0 or k >= len(arreglo) - 1:
                continue  # antes del primer pulso o después del último
            fraccion = (c - arreglo[k]) / (arreglo[k + 1] - arreglo[k])
            if multiplo >= 1:
                m = int(round(multiplo))
                fases.append(((k % m) + fraccion) / m)
            else:
                fases.append((fraccion / multiplo) % 1.0)  # por ejemplo 0.5: la mitad del pulso (corchea)
            usados += 1
        if usados < 5:
            continue
        angulos = 2 * np.pi * np.array(fases)
        z = np.exp(1j * angulos).mean()
        r = float(abs(z))
        periodo = float(np.median(np.diff(arreglo))) * multiplo
        resultado.append({"periodo_ms": round(periodo * 1000), "r": round(r, 2), "p": round(math.exp(-usados * r * r), 3),
                          "desfase_ms": round(float(np.angle(z) / (2 * np.pi) * periodo * 1000)), "n": usados})
    return resultado


def punto_de_entrada(analisis: dict, duracion_video: float) -> dict:
    """Dónde empezar la canción para que dure el video, arranque en un tiempo fuerte y, si se puede, la caída coincida con el gancho (1.5–5 s)."""
    fuertes = analisis["tiempos_fuertes"] or analisis["pulsos"] or [0.0]
    energia = np.array(analisis["energia_db"])
    ventana = analisis["energia_ventana_s"]
    total = analisis["duracion"]
    mejor = {"inicio": fuertes[0], "puntaje": -1e9, "caida_en": None}
    for inicio in fuertes:
        if inicio + duracion_video > total + 0.01 and inicio != fuertes[0]:
            continue
        i, j = int(inicio / ventana), max(int(inicio / ventana) + 1, int((inicio + duracion_video) / ventana))
        media = float(np.mean(energia[i:j])) if i < len(energia) else -80.0
        caida = next((c - inicio for c in analisis["caidas"] if 1.5 <= c - inicio <= 5.0), None)
        puntaje = media + (4.0 if caida is not None else 0.0) - 0.02 * inicio  # leve preferencia por entrar pronto
        if puntaje > mejor["puntaje"]:
            mejor = {"inicio": inicio, "puntaje": puntaje, "caida_en": caida}
    return {"inicio": round(float(mejor["inicio"]), 3), "caida_en": None if mejor["caida_en"] is None else round(float(mejor["caida_en"]), 2),
            "repetir": analisis["duracion"] - mejor["inicio"] < duracion_video}


def elegir_pista(biblioteca: list[dict], energia: str | None = None, ritmo: str | None = None) -> dict | None:
    """La pista que mejor encaja con la energía y el ritmo pedidos (None si no hay ninguna analizada)."""
    candidatas = [p for p in biblioteca if p.get("analisis")]
    if not candidatas:
        return None
    orden_energia = {"baja": 0, "media": 1, "alta": 2}
    orden_ritmo = {"lento": 0, "medio": 1, "rápido": 2}
    def distancia(p):
        a = p["analisis"]
        d = 0.0
        if energia in orden_energia:
            d += 2.0 * abs(orden_energia[a["intensidad"]] - orden_energia[energia])
        if ritmo in orden_ritmo:
            d += 1.5 * abs(orden_ritmo[a["ritmo"]] - orden_ritmo[ritmo])
        if p.get("licencia", "sin-confirmar") == "sin-confirmar":
            d += 2.5  # a igualdad de gusto, la canción con licencia declarada gana: es la que se puede publicar
        return d + (1.0 - a["confianza"]) * 1.5
    return min(candidatas, key=distancia)


def resumen(a: dict) -> str:
    fuerte = f"; {len(a['caidas'])} caída(s) hacia sección fuerte" if a["caidas"] else ""
    return (f"{a['bpm']} BPM ({a['ritmo']}), energía {a['intensidad']}, confianza {a['confianza']:.0%}{fuerte}"
            + (f", {a['volumen']['lufs']} LUFS" if a.get("volumen") else ""))
