"""Convierte lo que escribe la persona (y lo que Iris oyó en el video) en un guion de Remotion.

Este es el intérprete por reglas: reconoce frases frecuentes en español y detecta en la transcripción pasos numerados,
cifras y la palabra que se pide comentar. La IA (si está activa) propone un plan aparte (ver `direccion/`) que se mezcla con esto.
Todo lo que entiende se lo cuenta de vuelta a la persona.
"""
from __future__ import annotations

import re

import numeros
from musica import pulso_mas_cercano

from . import formatos
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
    (r"detras de (la|el)\b|\btexto detras\b", "Texto detrás de la persona: todavía no lo hago de forma automática."),
    (r"\brecort(a|ar|e)\b.*\bsegundos\b|\bduracion de \d+", "Recortar a una duración exacta: todavía no lo hago."),
]
FORMATOS = {k: v["nombre"] for k, v in formatos.FORMATOS.items()}

# Lo que el texto puede pedir (o negar) de forma explícita. Cada clave coincide con un interruptor de la tarjeta.
PEDIDOS = {
    "calculadora": r"calculadora|contador (?:digital )?de (?:dinero|precios?|valores?)|cada vez que se anuncie una cifra|(?:muestra|anima|actualiza)\w*\s+(?:el\s+|la\s+)?(?:valor|dinero|precio|monto|cifra)|sumar y restar|sume y reste",
    "transiciones": r"transicion(?:es)?|cortes? con efecto",
    "sonidos": r"efectos? de sonido|efectos? sonoros|\bsfx\b|\bwhoosh\b|sonidos? de (?:caja|transicion)",
    "logo": r"\blogo(?:tipo)?\b",
}
NEGADORES = r"(?:sin|ni|no\s+(?:quiero|pongas|agregues|uses|incluyas|anadas|hagas)|quita(?:r)?|elimina(?:r)?|evita(?:r)?|nada\s+de)"

# Interruptores de la tarjeta: nombre → valor por defecto (None = «Iris decide», con la IA o con reglas).
INTERRUPTORES = {"quitar_pausas": False, "acercamientos": True, "insignias": True, "contadores": True, "cierre": True, "color_referencias": False,
                 "musica": True, "ia": True, "calculadora": None, "transiciones": None, "sonidos": None, "logo": None}
VERSION_OPCIONES = 2


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


def _niega(plano: str, patron: str) -> bool:
    return bool(re.search(rf"\b{NEGADORES}\s+(?:las\s+|los\s+|el\s+|la\s+|ningun[ao]s?\s+|mas\s+)?(?:{patron})", plano))


def leer_prompt(prompt: str) -> dict:
    """Lo que el texto pide de forma explícita; nada se inventa.
    `pide` y `niega` son los interruptores que el texto enciende o apaga; `formato` es el que el texto describe (o None)."""
    texto = prompt.strip()
    plano = normalizar_conservando_espacios(texto)
    leido: dict = {"claves": [], "cta": None, "posicion": None, "max_palabras": None, "acento": None, "pide": set(), "niega": set(), "formato": None, "pendiente": []}

    coincidencia = re.search(r"(?:resalta|destaca|enfatiza|pon en grande|marca en grande)\w*\s+(?:las\s+|los\s+)?(?:palabras?|frases?)\s*(?:clave)?\s*:?\s*(.+)", texto, re.I)
    if not coincidencia:
        coincidencia = re.search(r"palabras?\s+clave\s*:\s*(.+)", texto, re.I)
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

    for clave, patron in PEDIDOS.items():
        if _niega(plano, patron):
            leido["niega"].add(clave)
        elif re.search(patron, plano):
            leido["pide"].add(clave)
    if re.search(r"(quita|quitar|elimina|eliminar|corta|cortar|saca|sacar|remueve)\s+(las\s+|los\s+)?(pausas|silencios)|sin\s+(pausas|silencios)", plano):
        leido["pide"].add("quitar_pausas")
    if re.search(r"\bsin\s+(la\s+)?(musica|cancion)", plano):
        leido["niega"].add("musica")
    elif re.search(r"\b(con|pon|poner|agrega|agregar|anade|anadir)\s+(la\s+|una\s+)?(musica|cancion)|musica\s+de\s+fondo", plano):
        leido["pide"].add("musica")

    if re.search(r"antes\s*(?:y|/|-)\s*despues|before\s*(?:and|/)\s*after", plano):
        leido["formato"] = "antes-despues"
    elif "calculadora" in leido["pide"]:
        leido["formato"] = "dinero"
    elif re.search(r"paso a paso|pasos numerados|tutorial|enumera\w* los pasos", plano):
        leido["formato"] = "pasos"
    leido["pendiente"] = [aviso for patron, aviso in PENDIENTES if re.search(patron, plano)]
    return leido


def normalizar_conservando_espacios(texto: str) -> str:
    """Minúsculas y sin acentos, pero con los espacios (para buscar frases)."""
    import unicodedata
    sin = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in sin if unicodedata.category(c) != "Mn")


def _manuales(opciones: dict) -> dict:
    """Lo que la persona tocó a propósito. Las tarjetas guardadas por una versión anterior guardaban todos los interruptores: ahí solo cuenta lo que se aparta del valor de entonces."""
    if opciones.get("_v") == VERSION_OPCIONES:
        return {k: v for k, v in opciones.items() if k in INTERRUPTORES and isinstance(v, bool)}
    antiguos = {"quitar_pausas": False, "acercamientos": True, "insignias": True, "contadores": True, "cierre": True, "color_referencias": False, "musica": True, "ia": True}
    return {k: v for k, v in opciones.items() if k in antiguos and isinstance(v, bool) and v != antiguos[k]}


def efectivo(prompt: str, opciones: dict) -> dict:
    """Lo que Iris va a hacer: lo que la persona tocó manda; si no, lo que pidió en el texto; si no, lo que trae el formato; si no, el valor por defecto
    (para calculadora, transiciones, sonidos y logo, `None` significa «lo decide el director»). `origenes` dice de dónde salió cada valor."""
    leido = leer_prompt(prompt)
    manual = _manuales(opciones)
    elegido = opciones.get("formato")
    ignorados = ("auto",) if opciones.get("_v") == VERSION_OPCIONES else ("auto", "subtitulos")  # antes «subtítulos» era el valor que se guardaba sin que nadie lo eligiera
    formato_manual = elegido if elegido in formatos.FORMATOS and elegido not in ignorados else None
    formato = formato_manual or leido["formato"] or "subtitulos"
    preset = formatos.FORMATOS[formato]["preset"]
    valores: dict = {}
    origenes: dict = {}
    for clave, defecto in INTERRUPTORES.items():
        if clave in manual:
            valores[clave], origenes[clave] = manual[clave], "manual"
        elif clave in leido["niega"]:
            valores[clave], origenes[clave] = False, "texto"
        elif clave in leido["pide"]:
            valores[clave], origenes[clave] = True, "texto"
        elif clave in preset and (formato_manual is not None or leido["formato"] is not None):
            valores[clave], origenes[clave] = preset[clave], "formato"
        else:
            valores[clave], origenes[clave] = defecto, "defecto"
    return {
        "formato": formato,
        "formato_origen": "manual" if formato_manual else "texto" if leido["formato"] else "defecto",
        **valores,
        "origenes": origenes,
        "color_referencias": bool(valores["color_referencias"]),
        "idioma": opciones.get("idioma") or None,
        "borrador": opciones.get("calidad") == "borrador",
        "acabado": opciones.get("acabado") or "auto",
        "claves": leido["claves"],
        "cta": leido["cta"],
        "posicion": leido["posicion"],
        "max_palabras": leido["max_palabras"],
        "acento": leido["acento"],
        "pendiente": leido["pendiente"],
        "pide": sorted(leido["pide"]),
        "niega": sorted(leido["niega"]),
    }


def resolver(config: dict, plan: dict, tiene_logo: bool, hay_dinero: bool) -> dict:
    """Completa lo que quedó en «lo decide el director» (None) con lo que decidió el plan. Nada se enciende sin que el plan o la persona lo pidan."""
    final = dict(config)
    if final["calculadora"] is None:
        final["calculadora"] = bool((plan.get("calculadora") or {}).get("usar")) and hay_dinero
    if final["transiciones"] is None:
        final["transiciones"] = bool((plan.get("transiciones") or {}).get("usar"))
    if final["sonidos"] is None:
        final["sonidos"] = ((plan.get("sonidos") or {}).get("nivel") or "ninguno") != "ninguno"
    if final["logo"] is None:
        final["logo"] = bool((plan.get("logo") or {}).get("usar")) and tiene_logo
    return final


def resumen(config: dict, tiene_logo: bool = False) -> list[dict]:
    """Lo que Iris entendió, en frases para mostrar (con un icono por tema)."""
    def de(clave: str) -> str:
        return {"texto": " · lo pediste en tu texto", "manual": "", "formato": " · viene con este formato"}.get(config["origenes"].get(clave, ""), "")

    filas = [{"icono": "texto", "texto": f"Formato: {FORMATOS.get(config['formato'], config['formato'])}" + (" · elegido por Iris según tu texto" if config["formato_origen"] == "texto" else "")}]
    if config["calculadora"]:
        filas.append({"icono": "calculadora", "texto": "Calculadora: suma, resta y muestra el total de cada cifra que digas" + de("calculadora")})
    elif config["calculadora"] is None:
        filas.append({"icono": "calculadora", "texto": "Calculadora de dinero: la usa el director si dices precios"})
    if config["claves"]:
        filas.append({"icono": "estrella", "texto": "Palabras en grande: " + ", ".join(config["claves"])})
    if config["cta"] and config["cierre"]:
        filas.append({"icono": "mensaje", "texto": f"Cierre pidiendo comentar «{config['cta']}»"})
    elif config["cierre"]:
        filas.append({"icono": "mensaje", "texto": "Cierre con palabra clave si la dices en el video (por ejemplo «comenta EDITOR»)"})
    if config["transiciones"]:
        filas.append({"icono": "transicion", "texto": "Transiciones en los cortes entre escenas" + de("transiciones")})
    elif config["transiciones"] is None:
        filas.append({"icono": "transicion", "texto": "Transiciones: las decide el director"})
    if config["sonidos"]:
        filas.append({"icono": "sonido", "texto": "Efectos de sonido sutiles bajo tu voz" + de("sonidos")})
    elif config["sonidos"] is None:
        filas.append({"icono": "sonido", "texto": "Efectos de sonido: los decide el director"})
    if config["logo"]:
        filas.append({"icono": "logo", "texto": "Logo animado de la marca" + de("logo") + ("" if tiene_logo else " · falta subir el logo de esta marca")})
    if config["quitar_pausas"]:
        filas.append({"icono": "tijeras", "texto": "Quitaré las pausas largas" + de("quitar_pausas")})
    if config["posicion"]:
        filas.append({"icono": "texto", "texto": f"Subtítulos {config['posicion']}"})
    if config["acento"]:
        filas.append({"icono": "color", "texto": f"Color principal {config['acento']}"})
    filas.append({"icono": "musica", "texto": "Música de fondo de tu biblioteca, con la voz siempre por delante" if config["musica"] else "Sin música"})
    if config["acabado"] != "auto":
        filas.append({"icono": "color", "texto": f"Acabado de color: {config['acabado']}"})
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
    """Un contador que sube hasta cada cifra importante que se dice (máximo tres, separados). Entiende «8.500.000», «300 mil» y «un millón»."""
    capas: list[dict] = []
    ultimo = -99.0
    for c in numeros.encontrar(palabras):
        valor = c["valor"]
        if len(capas) >= 3 or c["ini"] < 0.8 or c["ini"] - ultimo < 4.0 or c["ini"] > duracion - 1.0 or isinstance(valor, float):
            continue
        if valor < (10 if c["clase"] in ("dinero", "porcentaje") else 100) or valor > 10_000_000_000 or (c["clase"] == "cantidad" and 1900 <= valor <= 2100):
            continue
        capas.append({"tipo": "contador", "ini": round(c["ini"], 2), "fin": round(min(duracion, c["ini"] + 2.4), 2), "x": 50, "y": 20, "desde": 0, "hasta": int(valor),
                      "prefijo": "$" if c["clase"] == "dinero" else "", "sufijo": "%" if c["clase"] == "porcentaje" else "", "tamano": 130})
        ultimo = c["ini"]
    return capas


def _calculadora(palabras: list, duracion: float, tope: float, ajustes: list[dict] | None = None) -> dict | None:
    """Capa de calculadora con los pasos que salen de las cifras de dinero dichas antes de `tope`; None si no se dijo ninguna."""
    cifras = [c for c in numeros.encontrar(palabras) if c["ini"] < tope - 0.5]
    eventos = numeros.operaciones(cifras, ajustes=ajustes)
    if not eventos:
        return None
    moneda = "$"
    for c in cifras:
        if "dolares" in c["despues"][:2] or "usd" in c["despues"][:2]:
            moneda = "US$"
        elif "euros" in c["despues"][:2] or "euro" in c["despues"][:2]:
            moneda = "€"
    ini = max(0.0, eventos[0]["t"] - 0.4)
    fin = min(tope, eventos[-1]["t"] + eventos[-1]["dur"] + 2.4)
    return {"tipo": "calculadora", "ini": round(ini, 2), "fin": round(fin, 2), "x": 50, "y": 42, "moneda": moneda, "eventos": eventos}


def _transiciones(cortes: list[dict], duracion: float, desde: float = 1.0) -> list[dict]:
    """Cortes donde cabe una transición: ni al principio ni al final, bien separados. Entre escenas se permiten más seguidos que entre pausas quitadas."""
    elegidos: list[dict] = []
    for c in sorted(cortes, key=lambda c: c["t"]):
        separacion = 2.0 if c["tipo"] == "escena" else 3.5
        if c["t"] < desde or c["t"] > duracion - 1.0 or (elegidos and c["t"] - elegidos[-1]["t"] < separacion):
            continue
        elegidos.append(c)
    return elegidos[:10]


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


def _frases(palabras: list) -> list[tuple[float, float]]:
    """(inicio, fin) de cada frase dicha, según los signos de la transcripción."""
    frases, inicio = [], None
    for i, (ini, fin, texto) in enumerate(palabras):
        inicio = ini if inicio is None else inicio
        if re.search(r"[.?!]$", texto.strip()) or i == len(palabras) - 1:
            frases.append((inicio, fin))
            inicio = None
    return frases


def _tamano_titulo(texto: str) -> int:
    return 96 if len(texto) <= 24 else 84 if len(texto) <= 36 else 74


def construir_guion(nombre: str, config: dict, analisis: dict, perfil: dict | None, colores_marca: dict, base_clip: str,
                    plan: dict | None = None, musica: dict | None = None, marca_nombre: str = "", cortes: list[dict] | None = None,
                    logo: str | None = None) -> tuple[dict, list[str]]:
    """Guion de Remotion y la lista de lo que se aplicó (para contárselo a la persona).

    `plan`: lo que decidió el director (con IA o por reglas, ya saneado). `musica`: pulsos de la canción elegida ya medidos desde
    el inicio del video, `{"pulsos": [...], "fuertes": [...], "confianza": 0.7}`; con ellos los acercamientos se apoyan en el pulso.
    `cortes`: instantes donde hay un corte real, `[{"t": 12.4, "tipo": "escena" | "pausa"}]`, para las transiciones. `logo`: ruta (relativa a empresas/) del logo de la marca.
    """
    duracion = round(float(analisis["duracion"]), 2)
    voz = analisis.get("voz") or {}
    palabras = [list(p) for p in voz.get("palabras", [])]
    notas: list[str] = []
    plan = plan or {}

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

    acabado = plan.get("acabado")
    if acabado and config.get("acabado", "auto") != "ninguno":
        look = config.get("acabado") if config.get("acabado") in ("natural", "calido", "frio", "cine", "vibrante") else acabado["look"]
        guion["acabado"] = {"look": look, "intensidad": acabado["intensidad"]}
        notas.append(f"Acabado de color «{look}»")

    if not palabras:
        notas.append("No encontré voz en el video: apliqué solo lo visual.")
        return guion, notas

    cierre_clave, cierre_ini = (None, None)
    fin_de_contenido = duracion  # hasta dónde llegan las piezas: el cierre ocupa el final
    if config["cierre"]:
        cierre_clave, cierre_ini = _cierre(palabras, duracion, config["cta"])
        if cierre_clave is None and (plan.get("cierre") or {}).get("clave"):
            cierre_clave, cierre_ini = plan["cierre"]["clave"], max(0.0, duracion - 3.5)
    if cierre_clave and cierre_ini is not None:
        inicio = min(cierre_ini, max(0.0, duracion - 2.5))
        guion["escenas"].append({"tipo": "cta", "ini": round(inicio, 2), "duracion": round(duracion - inicio, 2), "clave": cierre_clave})
        fin_de_contenido = inicio
        palabras = [p for p in palabras if p[0] < inicio]
        notas.append(f"Cierre pidiendo comentar «{cierre_clave}»")

    maximo = config["max_palabras"] or (perfil or {}).get("maxPalabras") or 3
    guion["palabras"] = palabras
    claves = list(config["claves"])
    vistas = {normalizar(c) for c in claves}
    claves += [c for c in plan.get("claves", []) if normalizar(c) not in vistas]
    cifras = [t for _i, _f, t in palabras if _valor(t) is not None]
    guion["estiloPalabras"] = {"maxPalabras": maximo, "claves": claves + [c.strip("$%") for c in cifras][:12], "serif": [],
                               "posicion": config["posicion"] or ("abajo" if config["formato"] == "antes-despues" else "centro")}
    notas.append(f"Subtítulos palabra por palabra ({maximo} a la vez)")
    if claves:
        notas.append("Palabras en grande: " + ", ".join(claves))

    gancho = (plan.get("gancho") or {}).get("texto")
    fin_gancho = 0.0
    if gancho:
        fin_gancho = round(min(3.2, max(1.8, duracion * 0.4)), 2)
        guion["capas"].append({"tipo": "titulo", "ini": 0.15, "fin": fin_gancho, "x": 50, "y": 25, "texto": gancho, "tamano": _tamano_titulo(gancho)})
        notas.append(f"Gancho en pantalla: «{gancho}»")

    frases = _frases(palabras)
    if config["acercamientos"]:
        cada = (perfil or {}).get("zoom_cada") or 2
        espacio = plan.get("segundos_entre_acercamientos")
        if espacio and cada == 1:
            espacio *= 0.75  # las referencias que elegiste cortan rápido
        zooms, ultimo_fin = [], -99.0
        elegidas = [m for m in plan.get("momentos", []) if m["tipo"] == "acercamiento"] if plan.get("origen") == "ia" else []
        if elegidas:
            for m in elegidas:
                frase = next(((a, b) for a, b in frases if a - 0.2 <= m["t"] <= b), None)
                if frase and frase[1] - frase[0] >= 1.0 and frase[0] - ultimo_fin >= 1.0:
                    zooms.append({"ini": round(frase[0], 2), "fin": round(frase[1], 2), "escala": 1.22, "x": 50, "y": 38})
                    ultimo_fin = frase[1]
        elif espacio:
            for a, b in frases:
                if b - a >= 1.0 and a - ultimo_fin >= max(1.0, espacio - 1.2):
                    zooms.append({"ini": round(a, 2), "fin": round(b, 2), "escala": 1.22, "x": 50, "y": 38})
                    ultimo_fin = b
        else:
            for k, (a, b) in enumerate(frases):
                if k % cada == cada - 1 and b - a >= 1.0:
                    zooms.append({"ini": round(a, 2), "fin": round(b, 2), "escala": 1.22, "x": 50, "y": 38})
        if musica and musica["confianza"] >= 0.55:
            rejilla = musica["fuertes"] or musica["pulsos"]
            for z in zooms:
                nuevo = pulso_mas_cercano(z["ini"], rejilla, 0.18)
                if nuevo < z["fin"] - 0.8:
                    z["ini"] = round(nuevo, 2)
        guion["zooms"] = zooms
        if zooms:
            notas.append(f"{len(zooms)} acercamientos para dar ritmo" + (" apoyados en el pulso de la música" if musica and musica["confianza"] >= 0.55 else ""))

    if config["insignias"]:
        pasos = _pasos(palabras)
        for k, (numero, ini) in enumerate(pasos):
            fin = pasos[k + 1][1] - 0.2 if k + 1 < len(pasos) else min(duracion, ini + 5.0)
            guion["capas"].append({"tipo": "insignia", "ini": round(max(0, ini - 0.15), 2), "fin": round(fin, 2), "x": 14, "y": 12, "numero": numero})
        if pasos:
            notas.append(f"Numeré {len(pasos)} pasos")

    calculadora = None
    if config.get("calculadora"):
        calculadora = _calculadora([list(p) for p in voz.get("palabras", [])], duracion, fin_de_contenido,
                                  (plan.get("calculadora") or {}).get("ajustes"))
        if calculadora:
            calculadora["y"] = 42.5  # entre el gancho (arriba) y los subtítulos (58 %)
            for capa in guion["capas"]:
                if capa["tipo"] == "titulo":
                    capa["y"] = 23  # el gancho sube un poco para dejar sitio a la calculadora
            guion["capas"].append(calculadora)
            notas.append(f"Calculadora de dinero con {len(calculadora['eventos'])} paso(s) que salen de lo que dices")
        else:
            notas.append("Pediste calculadora, pero no oí cifras de dinero en el video: no la puse.")

    if config["contadores"] and not calculadora:
        contadores = _contadores(palabras, duracion)
        for m in plan.get("momentos", []):
            if m["tipo"] == "contador" and all(abs(m["t"] - c["ini"]) > 2.5 for c in contadores) and len(contadores) < 3:
                contadores.append({"tipo": "contador", "ini": m["t"], "fin": round(min(duracion, m["t"] + 2.4), 2), "x": 50, "y": 20,
                                   "desde": 0, "hasta": m["valor"], "prefijo": "", "sufijo": "", "tamano": 130})
        for c in contadores:
            if c["ini"] < fin_gancho:
                c["y"] = 38  # no tapar el gancho
        guion["capas"] += contadores
        if contadores:
            notas.append(f"{len(contadores)} contador(es) para cifras que dices")

    tarjetas = [m for m in plan.get("momentos", []) if m["tipo"] == "tarjeta"]
    puestas = 0
    for m in tarjetas[:3]:
        fin = round(min(duracion, m["t"] + 3.0), 2)
        if all(c["fin"] <= m["t"] or c["ini"] >= fin for c in guion["capas"] if c["tipo"] in ("tarjeta", "contador", "calculadora")):
            guion["capas"].append({"tipo": "tarjeta", "variante": "notificacion", "ini": m["t"], "fin": fin, "x": 50, "y": 58,
                                   "nombre": marca_nombre, "texto": m["texto"]})
            puestas += 1
    if puestas:
        notas.append(f"{puestas} tarjeta(s) con frases de tu video")

    if config.get("transiciones"):
        estilo = (plan.get("transiciones") or {}).get("estilo") or "barrido"
        elegidos = _transiciones(cortes or [], duracion)
        for c in elegidos:
            largo = (0.12, 0.33) if estilo == "impacto" else (0.2, 0.2)
            guion["capas"].append({"tipo": "transicion", "estilo": estilo, "ini": round(max(0.0, c["t"] - largo[0]), 2), "fin": round(min(duracion, c["t"] + largo[1]), 2)})
            if estilo == "impacto" and all(z["fin"] <= c["t"] - 0.1 or z["ini"] >= c["t"] + 0.3 for z in guion["zooms"]):
                guion["zooms"].append({"ini": round(max(0.0, c["t"] - 0.1), 2), "fin": round(c["t"] + 0.3, 2), "escala": 1.12, "x": 50, "y": 40})
        if elegidos:
            notas.append(f"{len(elegidos)} transición(es) «{estilo}» sobre los cortes" + (" entre escenas" if any(c["tipo"] == "escena" for c in elegidos) else ""))
        else:
            notas.append("Pediste transiciones, pero este video no tiene cortes donde ponerlas (sube varias escenas o quita las pausas).")

    if config.get("logo"):
        if not logo:
            notas.append("Pediste logo animado, pero esta marca no tiene logo: súbelo en «Logo de la marca» y vuelve a crear el video.")
        else:
            estilo_logo = (plan.get("logo") or {}).get("estilo") or "cierre"
            tiene_cta = any(e.get("tipo") == "cta" for e in guion["escenas"])
            if estilo_logo == "cierre" and tiene_cta:
                guion.setdefault("marca", {})["logo"] = logo  # el cierre ya muestra el logo de la marca, ahora animado
                notas.append("Logo animado en el cierre")
            else:
                largo = 1.8 if estilo_logo == "cierre" else 1.4 if estilo_logo == "intro" else max(1.0, duracion - 1.0)
                ini_logo = max(0.0, duracion - largo) if estilo_logo == "cierre" else 0.2 if estilo_logo == "intro" else 0.5
                guion["capas"].append({"tipo": "logo", "archivo": logo, "estilo": estilo_logo, "ini": round(ini_logo, 2), "fin": round(min(duracion, ini_logo + largo), 2)})
                notas.append({"cierre": "Logo animado al final", "intro": "Logo animado al inicio", "marca": "Marca de agua con el logo"}[estilo_logo])

    if musica and plan.get("acabado", {}).get("pulso") and musica["confianza"] >= 0.55 and musica["fuertes"]:
        guion["pulso"] = {"tiempos": [round(t, 3) for t in musica["fuertes"]], "intensidad": 0.5}
    return guion, notas
