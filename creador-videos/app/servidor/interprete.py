"""Convierte lo que escribe la persona (y lo que Iris oyó en el video) en un guion de Remotion.

No usa inteligencia artificial: reconoce frases frecuentes en español y detecta en la transcripción pasos numerados,
cifras y la palabra que se pide comentar. Todo lo que entiende se lo cuenta de vuelta a la persona.
"""
from __future__ import annotations

import re

from .logica_texto import normalizar

ORDINALES = {"primero": 1, "primer": 1, "segundo": 2, "tercero": 3, "tercer": 3, "cuarto": 4, "quinto": 5,
             "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
NUMEROS_PALABRA = {"uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
RELLENO_CTA = {"la", "el", "un", "una", "palabra", "aqui", "abajo", "este", "esta", "reel", "video", "post", "publicacion", "me", "te",
               "con", "tu", "en", "y", "the", "word", "below", "this", "a", "mi", "al", "por", "favor", "solo", "simplemente"}
COLORES = {"rojo": "#FF3B30", "naranja": "#FF9500", "amarillo": "#FFCC00", "verde": "#34C759", "turquesa": "#30B0C7", "celeste": "#32ADE6",
           "azul": "#0A84FF", "morado": "#AF52DE", "violeta": "#AF52DE", "rosa": "#FF2D55", "rosado": "#FF2D55", "blanco": "#FFFFFF"}
# Cosas que la persona puede pedir y que Iris todavía no hace: se le dice claro en vez de ignorarlas.
PENDIENTES = [
    (r"\bmusica\b|\bcancion\b", "Música de fondo: todavía no puedo añadirla."),
    (r"\btransicion|\btransiciones\b", "Transiciones con efecto: todavía no están disponibles."),
    (r"detras de (la|el)\b|\btexto detras\b", "Texto detrás de la persona: todavía no lo hago de forma automática."),
    (r"efectos? de sonido|\bwhoosh\b", "Efectos de sonido: todavía no los añado."),
    (r"\brecort(a|ar|e)\b.*\bsegundos\b|\bduracion de \d+", "Recortar a una duración exacta: todavía no lo hago."),
    (r"\blogo\b", "Logo animado: usa el logo de la marca si lo tiene configurado; no genero uno nuevo."),
]
FORMATOS = {"subtitulos": "Subtítulos dinámicos", "antes-despues": "Antes y después"}


def _sin_comillas(texto: str) -> str:
    return texto.strip().strip("\"'“”«»‘’ .,:;!¡¿?")


def _lista(texto: str) -> list[str]:
    piezas = re.split(r",|;|\s+y\s+|\s+e\s+|\s+and\s+", texto)
    vistas: list[str] = []
    for pieza in piezas:
        limpia = _sin_comillas(pieza)
        if limpia and len(limpia) <= 40 and limpia.lower() not in {v.lower() for v in vistas}:
            vistas.append(limpia)
    return vistas[:12]


def leer_prompt(prompt: str) -> dict:
    """Lo que el texto pide de forma explícita; nada se inventa."""
    texto = prompt.strip()
    plano = normalizar_conservando_espacios(texto)
    leido: dict = {"claves": [], "cta": None, "posicion": None, "max_palabras": None, "acento": None, "sugerencias": {}, "pendiente": []}

    coincidencia = re.search(r"(?:resalta|destaca|enfatiza|pon en grande|marca en grande)\w*\s*(?:las\s+|los\s+)?(?:palabras?|frases?)?\s*(?:clave)?\s*:?\s*(.+)", texto, re.I)
    if not coincidencia:
        coincidencia = re.search(r"palabras?\s+clave\s*:?\s*(.+)", texto, re.I)
    if coincidencia:
        resto = re.split(r"[.\n]|\s+(?:quita|elimina|y\s+quita|y\s+elimina|con\s+subtitulos|pon|y\s+pon|cierra|y\s+cierra|al\s+final)\b", coincidencia.group(1), maxsplit=1, flags=re.I)[0]
        leido["claves"] = _lista(resto)

    comentar = re.search(r"coment\w*\s+(?:la\s+palabra\s+|la\s+frase\s+|the\s+word\s+)?[\"“«']?([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]{3,30})", texto, re.I)
    if comentar and normalizar(comentar.group(1)) not in RELLENO_CTA:
        leido["cta"] = comentar.group(1).upper()

    posicion = re.search(r"subtitulos?\s+(?:van\s+|ponlos\s+|poner\s+)?(?:al\s+|en\s+el\s+|en\s+la\s+)?(abajo|arriba|centro|medio)", plano)
    if posicion:
        leido["posicion"] = {"abajo": "abajo", "arriba": "arriba", "centro": "centro", "medio": "centro"}[posicion.group(1)]
    cantidad = re.search(r"(?:subtitulos?\s+de\s+|de\s+)?(una|1|dos|2|tres|3)\s+palabras?\s+(?:por\s+vez|a la vez|por pantalla)", plano)
    if cantidad:
        leido["max_palabras"] = {"una": 1, "1": 1, "dos": 2, "2": 2, "tres": 3, "3": 3}[cantidad.group(1)]
    color = re.search(r"(?:color|acento|tono)\s+(?:de\s+acento\s+|principal\s+)?(?:es\s+|sea\s+)?(#[0-9a-fA-F]{6}|rojo|naranja|amarillo|verde|turquesa|celeste|azul|morado|violeta|rosa|rosado|blanco)", texto, re.I)
    if color:
        valor = color.group(1)
        leido["acento"] = valor.upper() if valor.startswith("#") else COLORES[valor.lower()]

    if re.search(r"antes\s*(?:y|/|-)\s*despues|before\s*(?:and|/)\s*after", plano):
        leido["sugerencias"]["formato"] = "antes-despues"
    if re.search(r"(quita|quitar|elimina|eliminar|corta|cortar|saca|sacar|remueve)\s+(las\s+|los\s+)?(pausas|silencios)|sin\s+(pausas|silencios)", plano):
        leido["sugerencias"]["quitar_pausas"] = True
    leido["pendiente"] = [aviso for patron, aviso in PENDIENTES if re.search(patron, plano)]
    return leido


def normalizar_conservando_espacios(texto: str) -> str:
    """Minúsculas y sin acentos, pero con los espacios (para buscar frases)."""
    import unicodedata
    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def efectivo(prompt: str, opciones: dict) -> dict:
    """Mezcla lo que dicen los interruptores (mandan) con lo que pide el texto (rellena lo que los interruptores no cubren)."""
    leido = leer_prompt(prompt)
    return {
        "formato": opciones.get("formato") or "subtitulos",
        "quitar_pausas": bool(opciones.get("quitar_pausas", False)),
        "acercamientos": bool(opciones.get("acercamientos", True)),
        "insignias": bool(opciones.get("insignias", True)),
        "contadores": bool(opciones.get("contadores", True)),
        "cierre": bool(opciones.get("cierre", True)),
        "color_referencias": bool(opciones.get("color_referencias", False)),
        "idioma": opciones.get("idioma") or None,
        "borrador": opciones.get("calidad") == "borrador",
        "claves": leido["claves"],
        "cta": leido["cta"],
        "posicion": leido["posicion"],
        "max_palabras": leido["max_palabras"],
        "acento": leido["acento"],
        "pendiente": leido["pendiente"],
        "sugerencias": leido["sugerencias"],
    }


def resumen(config: dict) -> list[dict]:
    """Lo que Iris entendió, en frases para mostrar (con un icono por tema)."""
    filas = [{"icono": "texto", "texto": f"Formato: {FORMATOS.get(config['formato'], config['formato'])}"}]
    if config["claves"]:
        filas.append({"icono": "estrella", "texto": "Palabras en grande: " + ", ".join(config["claves"])})
    if config["cta"] and config["cierre"]:
        filas.append({"icono": "mensaje", "texto": f"Cierre pidiendo comentar «{config['cta']}»"})
    elif config["cierre"]:
        filas.append({"icono": "mensaje", "texto": "Cierre con palabra clave si la dices en el video (por ejemplo «comenta EDITOR»)"})
    if config["quitar_pausas"]:
        filas.append({"icono": "tijeras", "texto": "Quitaré las pausas largas"})
    if config["posicion"]:
        filas.append({"icono": "texto", "texto": f"Subtítulos {config['posicion']}"})
    if config["acento"]:
        filas.append({"icono": "color", "texto": f"Color principal {config['acento']}"})
    return filas


# ---------------------------------------------------------------------------------------------------------------------
# Del análisis del video al guion
# ---------------------------------------------------------------------------------------------------------------------

def _pasos(palabras: list) -> list[tuple[int, float]]:
    """Pasos numerados que se dicen en voz alta: «primero… segundo… tercero…». Solo vale una cuenta que empieza en 1 y avanza de uno en uno."""
    encontrados: list[tuple[int, float]] = []
    for i, (ini, _fin, texto) in enumerate(palabras):
        clave = normalizar(texto)
        numero = ORDINALES.get(clave)
        if numero is None and clave == "paso" and i + 1 < len(palabras):
            siguiente = normalizar(palabras[i + 1][2])
            numero = int(siguiente) if siguiente.isdigit() and int(siguiente) <= 9 else NUMEROS_PALABRA.get(siguiente)
            if numero is None and siguiente == "numero" and i + 2 < len(palabras):
                tercero = normalizar(palabras[i + 2][2])
                numero = int(tercero) if tercero.isdigit() else NUMEROS_PALABRA.get(tercero)
        if numero is None:
            continue
        # «segundo» también es una unidad de tiempo: solo cuenta si abre una frase.
        abre_frase = i == 0 or re.search(r"[.?!,:;]$", palabras[i - 1][2].strip()) or ini - palabras[i - 1][1] > 0.3 or normalizar(palabras[i - 1][2]) in {"y", "luego", "despues", "and", "then"}
        if clave in ORDINALES and not abre_frase:
            continue
        encontrados.append((numero, ini))
    secuencia: list[tuple[int, float]] = []
    esperado = 1
    for numero, ini in encontrados:
        if numero == esperado:
            secuencia.append((numero, ini))
            esperado += 1
    return secuencia if len(secuencia) >= 2 else []


def _valor(texto: str) -> tuple[float, str, str] | None:
    """(valor, prefijo, sufijo) si la palabra es una cifra que merece contador; None si no."""
    limpio = texto.strip().rstrip(".,;:!?")
    moneda = "$" if limpio.startswith("$") else ""
    limpio = limpio.lstrip("$")
    porcentaje = limpio.endswith("%")
    limpio = limpio.rstrip("%")
    miles = re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", limpio)
    if miles:
        valor = float(re.sub(r"[.,]", "", limpio))
    elif re.fullmatch(r"\d+", limpio):
        valor = float(limpio)
    else:
        return None  # decimales y mezclas: no se tocan
    if not porcentaje and not moneda and 1900 <= valor <= 2100:
        return None  # parece un año
    if valor < (10 if (porcentaje or moneda) else 100) or valor > 10_000_000:
        return None
    return valor, moneda, "%" if porcentaje else ""


def _contadores(palabras: list, duracion: float) -> list[dict]:
    capas: list[dict] = []
    ultimo = -99.0
    for i, (ini, _fin, texto) in enumerate(palabras):
        if len(capas) >= 3 or ini < 0.8 or ini - ultimo < 4.0 or ini > duracion - 1.0:
            continue
        valor = _valor(texto)
        if valor is None:
            continue
        cifra, moneda, sufijo = valor
        if not moneda and i + 1 < len(palabras) and normalizar(palabras[i + 1][2]) in {"dolares", "pesos", "usd", "cop", "euros", "dollars"}:
            moneda = "$"
        capas.append({"tipo": "contador", "ini": round(ini, 2), "fin": round(min(duracion, ini + 2.4), 2), "x": 50, "y": 20,
                      "desde": 0, "hasta": int(cifra), "prefijo": moneda, "sufijo": sufijo, "tamano": 130})
        ultimo = ini
    return capas


def _cierre(palabras: list, duracion: float, cta_pedido: str | None) -> tuple[str | None, float | None]:
    """Palabra que se pide comentar y segundo en que empieza el cierre. Prefiere lo que se dice en el video."""
    for i, (ini, _fin, texto) in enumerate(palabras):
        if normalizar(texto).startswith(("coment", "comment")):
            for _a, _b, siguiente in palabras[i + 1:i + 7]:
                clave = normalizar(siguiente)
                if clave and clave not in RELLENO_CTA and len(clave) >= 3:
                    return _sin_comillas(siguiente).upper(), ini
    if cta_pedido:
        return cta_pedido, max(0.0, duracion - 3.5)
    return None, None


def construir_guion(nombre: str, config: dict, analisis: dict, perfil: dict | None, colores_marca: dict, base_clip: str) -> tuple[dict, list[str]]:
    """Guion de Remotion y la lista de lo que se aplicó (para contárselo a la persona)."""
    duracion = round(float(analisis["duracion"]), 2)
    voz = analisis.get("voz") or {}
    palabras = [list(p) for p in voz.get("palabras", [])]
    notas: list[str] = []

    guion: dict = {"formato": nombre, "diseno": "antes-despues" if config["formato"] == "antes-despues" else "pleno",
                   "base": {"clip": base_clip}, "duracion": duracion, "escenas": [], "capas": [], "zooms": []}
    if config["formato"] == "antes-despues":
        guion["etiquetas"] = {"antes": "antes", "despues": "después"}
    horizontal = bool(analisis.get("ancho") and analisis.get("alto") and analisis["ancho"] > analisis["alto"])  # un video horizontal se queda horizontal
    ancho, alto = (1920, 1080) if horizontal else (1080, 1920)
    if config.get("borrador"):  # borrador rápido: la mitad de tamaño, se construye mucho más deprisa
        ancho, alto = ancho // 2, alto // 2
        notas.append("Borrador rápido (mitad de tamaño)")
    if (ancho, alto) != (1080, 1920):
        guion["ancho"], guion["alto"] = ancho, alto

    colores = dict(colores_marca)
    if config["acento"]:
        colores["acento"] = config["acento"]
    elif config["color_referencias"] and perfil and perfil.get("acento"):
        colores["acento"] = perfil["acento"]
    if colores:
        guion["marca"] = {"colores": colores}

    if not palabras:
        notas.append("No encontré voz en el video: apliqué solo lo visual.")
        return guion, notas

    cierre_clave, cierre_ini = (None, None)
    if config["cierre"]:
        cierre_clave, cierre_ini = _cierre(palabras, duracion, config["cta"])
    if cierre_clave and cierre_ini is not None:
        inicio = min(cierre_ini, max(0.0, duracion - 2.5))
        guion["escenas"].append({"tipo": "cta", "ini": round(inicio, 2), "duracion": round(duracion - inicio, 2), "clave": cierre_clave})
        palabras = [p for p in palabras if p[0] < inicio]
        notas.append(f"Cierre pidiendo comentar «{cierre_clave}»")

    maximo = config["max_palabras"] or (perfil or {}).get("maxPalabras") or 3
    guion["palabras"] = palabras
    claves = list(config["claves"])
    cifras = [t for _i, _f, t in palabras if _valor(t) is not None]
    guion["estiloPalabras"] = {"maxPalabras": maximo, "claves": claves + [c.strip("$%") for c in cifras][:12], "serif": [],
                               "posicion": config["posicion"] or ("abajo" if config["formato"] == "antes-despues" else "centro")}
    notas.append(f"Subtítulos palabra por palabra ({maximo} a la vez)")
    if claves:
        notas.append("Palabras en grande: " + ", ".join(claves))

    if config["acercamientos"]:
        cada = (perfil or {}).get("zoom_cada") or 2
        zooms, inicio, frase = [], None, 0
        for i, (ini, fin, texto) in enumerate(palabras):
            inicio = ini if inicio is None else inicio
            if re.search(r"[.?!]$", texto.strip()) or i == len(palabras) - 1:
                if frase % cada == cada - 1 and fin - inicio >= 1.0:
                    zooms.append({"ini": round(inicio, 2), "fin": round(fin, 2), "escala": 1.22, "x": 50, "y": 38})
                frase, inicio = frase + 1, None
        guion["zooms"] = zooms
        if zooms:
            notas.append(f"{len(zooms)} acercamientos para dar ritmo")

    if config["insignias"]:
        pasos = _pasos(palabras)
        for k, (numero, ini) in enumerate(pasos):
            fin = pasos[k + 1][1] - 0.2 if k + 1 < len(pasos) else min(duracion, ini + 5.0)
            guion["capas"].append({"tipo": "insignia", "ini": round(max(0, ini - 0.15), 2), "fin": round(fin, 2), "x": 14, "y": 12, "numero": numero})
        if pasos:
            notas.append(f"Numeré {len(pasos)} pasos")

    if config["contadores"]:
        contadores = _contadores(palabras, duracion)
        guion["capas"] += contadores
        if contadores:
            notas.append(f"{len(contadores)} contador(es) para cifras que dices")
    return guion, notas
