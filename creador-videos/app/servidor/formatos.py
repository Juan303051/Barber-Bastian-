"""Catálogo de formatos de video. Cada formato es un conjunto de valores iniciales para los interruptores y una forma de mostrar el video.

«Automático» no es un formato: significa que Iris lo decide según lo que la persona escribe (y, con IA, según lo que se dice en el video).
Añadir un formato nuevo es añadir una entrada aquí; la pantalla lo muestra sola."""
from __future__ import annotations

FORMATOS: dict[str, dict] = {
    "auto": {"nombre": "Automático", "ayuda": "Iris elige según lo que pidas y lo que digas.", "diseno": "pleno", "preset": {}},
    "subtitulos": {"nombre": "Subtítulos dinámicos", "ayuda": "Palabra por palabra, con las clave en grande.", "diseno": "pleno", "preset": {}},
    "dinero": {"nombre": "Contador de dinero", "ayuda": "Una calculadora suma y resta cada cifra que dices.", "diseno": "pleno",
               "preset": {"calculadora": True, "contadores": False, "sonidos": True}},
    "antes-despues": {"nombre": "Antes y después", "ayuda": "Tu toma cruda al lado de la editada.", "diseno": "antes-despues", "preset": {}},
    "pasos": {"nombre": "Paso a paso", "ayuda": "Un 1, 2, 3 en pantalla cuando enumeras pasos.", "diseno": "pleno", "preset": {"insignias": True, "transiciones": True}},
}


def publicos() -> list[dict]:
    """Lo que la pantalla necesita para dibujar el selector."""
    return [{"id": k, "nombre": v["nombre"], "ayuda": v["ayuda"]} for k, v in FORMATOS.items()]
