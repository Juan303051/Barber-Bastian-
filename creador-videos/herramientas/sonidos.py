"""Efectos de sonido sintetizados con fórmulas (numpy): whoosh, tecla, caja registradora, impacto, pop y brillo.

No usan ningún archivo de terceros: no hay derechos que confirmar ni nada que descargar. Cada efecto es determinista (misma entrada, mismo sonido)
y sale normalizado a 1,0; el nivel final lo fija la mezcla, relativo a la voz. Son sonidos de «diseño de sonido» básicos pensados para revisarse con el oído."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
PESO = {"whoosh": 0.85, "tecla": 0.55, "caja": 0.9, "impacto": 1.0, "pop": 0.5, "brillo": 0.4}
DURACION = {"whoosh": 0.5, "tecla": 0.1, "caja": 1.0, "impacto": 0.7, "pop": 0.14, "brillo": 0.9}


def _t(duracion: float) -> np.ndarray:
    return np.arange(int(SR * duracion)) / SR


def _normal(y: np.ndarray) -> np.ndarray:
    pico = float(np.abs(y).max()) or 1.0
    return (y / pico).astype(np.float32)


def whoosh(duracion: float = DURACION["whoosh"]) -> np.ndarray:
    """Ruido que pasa por un filtro resonante cuya frecuencia sube y baja: el «zumbido» de un movimiento rápido."""
    t = _t(duracion)
    n = len(t)
    ruido = np.random.default_rng(11).standard_normal(n)
    centro = 220.0 * (11.0 ** np.sin(np.pi * np.clip(t / duracion, 0, 1) ** 0.8))  # 220 Hz → ~2,4 kHz → 220 Hz
    f = 2 * np.sin(np.pi * np.minimum(centro, SR / 6) / SR)
    q = 0.6
    pasa_bajo = pasa_banda = 0.0
    salida = np.empty(n)
    for i in range(n):  # filtro de variables de estado con frecuencia variable
        pasa_bajo += f[i] * pasa_banda
        alto = ruido[i] - pasa_bajo - q * pasa_banda
        pasa_banda += f[i] * alto
        salida[i] = pasa_banda
    envolvente = np.sin(np.pi * np.clip(t / duracion, 0, 1)) ** 1.6
    return _normal(salida * envolvente)


def tecla(duracion: float = DURACION["tecla"]) -> np.ndarray:
    """Clic de tecla de calculadora: un golpe seco y corto."""
    t = _t(duracion)
    ruido = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t * 900)
    cuerpo = np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 90) + 0.6 * np.sin(2 * np.pi * 950 * t) * np.exp(-t * 60)
    return _normal(0.5 * ruido + cuerpo)


def caja(duracion: float = DURACION["caja"]) -> np.ndarray:
    """«Cha-ching» de caja registradora: dos campanas metálicas seguidas, la segunda más aguda."""
    t = _t(duracion)
    parciales = (1.0, 2.76, 5.4, 8.93)  # relaciones inarmónicas de una campana pequeña

    def campana(base: float, retraso: float, caida: float) -> np.ndarray:
        local = np.clip(t - retraso, 0, None)
        sonido = sum(np.sin(2 * np.pi * base * p * local) * np.exp(-local * caida * (1 + 0.5 * k)) / (1 + 0.6 * k) for k, p in enumerate(parciales))
        return sonido * (t >= retraso) * np.minimum(1.0, local * 800)

    golpe = np.random.default_rng(5).standard_normal(len(t)) * np.exp(-t * 400) * 0.4
    return _normal(campana(1320.0, 0.0, 7.0) + 0.9 * campana(1976.0, 0.085, 6.0) + golpe)


def impacto(duracion: float = DURACION["impacto"]) -> np.ndarray:
    """Golpe grave que cae de frecuencia, con un clic al inicio: el «boom» de un título que entra."""
    t = _t(duracion)
    fase = 2 * np.pi * (45.0 * t + (130.0 - 45.0) * (1 - np.exp(-t * 18)) / 18)
    cuerpo = np.sin(fase) * np.exp(-t * 6.5)
    clic = np.random.default_rng(7).standard_normal(len(t)) * np.exp(-t * 220) * 0.35
    return _normal(cuerpo + clic)


def pop(duracion: float = DURACION["pop"]) -> np.ndarray:
    """Burbuja corta: un tono que cae rápido. Para tarjetas, pasos y piezas que aparecen."""
    t = _t(duracion)
    fase = 2 * np.pi * (260.0 * t + (620.0 - 260.0) * (1 - np.exp(-t * 55)) / 55)
    return _normal(np.sin(fase) * np.exp(-t * 32))


def brillo(duracion: float = DURACION["brillo"]) -> np.ndarray:
    """Destello suave de agudos que acompaña el brillo que cruza un logo."""
    t = _t(duracion)
    frecuencias = (2637.0, 3136.0, 3951.0, 5274.0)
    y = sum(np.sin(2 * np.pi * f * t + k) * (0.6 + 0.4 * np.sin(2 * np.pi * (7 + k) * t)) for k, f in enumerate(frecuencias))
    envolvente = np.minimum(1.0, t * 40) * np.exp(-t * 4.5)
    return _normal(y * envolvente)


EFECTOS = {"whoosh": whoosh, "tecla": tecla, "caja": caja, "impacto": impacto, "pop": pop, "brillo": brillo}
_cache: dict[str, np.ndarray] = {}


def efecto(nombre: str) -> np.ndarray:
    if nombre not in _cache:
        _cache[nombre] = EFECTOS[nombre]()
    return _cache[nombre]


def eventos_de_guion(guion: dict, nivel: str = "sutil") -> list[dict]:
    """Qué sonido va en cada pieza del guion y cuándo: [{t, tipo, vol}] ordenado. «sutil» deja solo lo esencial; «marcado» añade golpes y pops."""
    marcado = nivel == "marcado"
    eventos: list[dict] = []

    def poner(t: float, tipo: str, vol: float = 1.0) -> None:
        if t >= 0:
            eventos.append({"t": round(float(t), 3), "tipo": tipo, "vol": vol})

    for capa in guion.get("capas", []):
        tipo = capa.get("tipo")
        if tipo == "transicion":
            corte = (capa["ini"] + capa["fin"]) / 2
            if capa.get("estilo") == "impacto":
                poner(corte, "impacto", 0.9)
            else:
                poner(corte - 0.22, "whoosh", 1.0 if capa.get("estilo") == "barrido" else 0.7)  # el máximo del zumbido cae sobre el corte
        elif tipo == "calculadora":
            poner(capa["ini"] + 0.3, "pop", 0.8)
            for e in capa.get("eventos", []):
                poner(e["t"], "tecla", 0.9)
                if e["op"] == "total":
                    poner(e["t"] + min(0.5 * e["dur"], 0.7), "caja", 1.0)
        elif tipo == "titulo" and marcado:
            poner(capa["ini"] + 0.05, "impacto", 0.8)
        elif tipo in ("tarjeta", "insignia", "contador") and marcado:
            poner(capa["ini"], "pop", 0.8)
        elif tipo == "logo" and capa.get("estilo") != "marca":
            poner(capa["ini"] + 0.45, "brillo", 1.0)
    for escena in guion.get("escenas", []):
        if escena.get("tipo") == "cta" and (guion.get("marca") or {}).get("logo"):
            poner(escena["ini"] + 0.45, "brillo", 1.0)
    eventos.sort(key=lambda e: e["t"])
    depurados: list[dict] = []
    for e in eventos:  # dos sonidos iguales a menos de 80 ms suenan a un error
        if depurados and depurados[-1]["tipo"] == e["tipo"] and e["t"] - depurados[-1]["t"] < 0.08:
            continue
        depurados.append(e)
    return depurados


def pista(eventos: list[dict], duracion: float) -> np.ndarray:
    """Todos los efectos colocados en su instante sobre un silencio de `duracion` segundos; el pico queda en 1,0. Vacía si no hay eventos."""
    y = np.zeros(int(SR * duracion) + 1, dtype=np.float32)
    for e in eventos:
        sonido = efecto(e["tipo"]) * PESO[e["tipo"]] * e.get("vol", 1.0)
        inicio = int(round(e["t"] * SR))
        if inicio >= len(y):
            continue
        fin = min(len(y), inicio + len(sonido))
        y[inicio:fin] += sonido[: fin - inicio]
    if not np.any(y):
        return y[: int(SR * duracion)]
    return (y / float(np.abs(y).max()))[: int(SR * duracion)].astype(np.float32)


def escribir(y: np.ndarray, destino: Path) -> None:
    with wave.open(str(destino), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes())
