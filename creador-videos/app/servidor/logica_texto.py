"""Utilidades de texto compartidas por el intérprete y el estilo."""
from __future__ import annotations

import re
import unicodedata


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos ni signos."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in sin if unicodedata.category(c) != "Mn"))
