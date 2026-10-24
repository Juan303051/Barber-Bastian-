"""Cifras habladas: encuentra en una transcripción con tiempos los números y montos que la persona dice, y los convierte en operaciones de calculadora.

Whisper escribe las cifras de formas muy distintas: «8.500.000» llega partido en tres palabras («8», «.500», «.000»), «300 mil» mezcla dígitos y letras y
«un millón» llega en letras. Aquí se reúnen esos pedazos, se leen los números en letras (hasta billones) y se decide qué es dinero, porcentaje o simple cantidad.
Nada se inventa: cada valor sale de lo que se dijo; lo que Iris calcula con ellos se marca como `derivado`.
"""
from __future__ import annotations

import re
import unicodedata

Palabra = list  # [inicio, fin, texto]

UNIDADES = {"cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
            "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19,
            "veinte": 20, "veintiun": 21, "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24, "veinticinco": 25,
            "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90}
CENTENAS = {"cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300, "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400,
            "quinientos": 500, "quinientas": 500, "seiscientos": 600, "seiscientas": 600, "setecientos": 700, "setecientas": 700, "ochocientos": 800,
            "ochocientas": 800, "novecientos": 900, "novecientas": 900}
MAGNITUDES = {"mil": 1_000, "millon": 1_000_000, "millones": 1_000_000, "billon": 10**12, "billones": 10**12}
MONEDAS = {"peso", "pesos", "dolar", "dolares", "usd", "cop", "euro", "euros", "dollars", "dollar", "mxn", "soles", "sol", "bolivares"}
PISTAS_DINERO = {"cuesta", "cuestan", "vale", "valen", "precio", "costo", "valor", "descuento", "descuentos", "rebaja", "ahorras", "ahorro", "pagas",
                 "pagar", "cuota", "inicial", "mensual", "mensuales", "gasto", "gastas", "ganas", "ganancia", "factura", "inversion"}
PISTAS_RESTA = {"descuento", "descuentos", "rebaja", "rebajamos", "rebajas", "menos", "resta", "restamos", "restar", "quitamos", "quitas", "quita", "ahorras",
                "ahorro", "ahorrarte", "gasto", "gastos", "gastas", "recorte", "bonificacion", "subsidio"}
PISTAS_SUMA = {"mas", "suma", "sumamos", "sumar", "agrega", "agregamos", "adicional", "adicionales", "extra", "recargo", "sumale", "aparte"}
PISTAS_TOTAL = {"queda", "quedas", "quedan", "quedaria", "total", "final", "finalmente", "resultado", "terminas", "terminaria", "sale", "salen"}


def plano(texto: str) -> str:
    """Minúsculas y sin acentos ni signos de puntuación (los separadores de miles se pierden a propósito)."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in sin if unicodedata.category(c) != "Mn"))


# ---------------------------------------------------------------------------------------------------------------------
# Reunir lo que Whisper parte
# ---------------------------------------------------------------------------------------------------------------------

def unir_fragmentos(palabras: list[Palabra]) -> list[Palabra]:
    """«8» «.500» «.000» → «8.500.000»; «$» «5» → «$5»; «20» «%» → «20%»; «1» «,5» → «1,5». Conserva el tiempo del primero al último pedazo."""
    salida: list[Palabra] = []
    for ini, fin, texto in palabras:
        t = texto.strip()
        if salida:
            previa = salida[-1][2]
            solo_digitos = re.fullmatch(r"\$?\d[\d.,]*", previa) is not None
            if solo_digitos and (re.fullmatch(r"[.,]\d{3}[.,;:!?]*", t) or re.fullmatch(r"[.,]\d{1,2}[.,;:!?]*", t) and not re.search(r"[.,]\d{3}", t)) and not re.search(r"[.,;:!?]$", previa):
                salida[-1] = [salida[-1][0], fin, previa + t]
                continue
            if solo_digitos and t in ("%", "%.", "%,"):
                salida[-1] = [salida[-1][0], fin, previa + t]
                continue
            if previa == "$" and re.fullmatch(r"\d[\d.,]*", t):
                salida[-1] = [salida[-1][0], fin, previa + t]
                continue
        salida.append([ini, fin, t])
    return salida


# ---------------------------------------------------------------------------------------------------------------------
# Leer números
# ---------------------------------------------------------------------------------------------------------------------

def _es_numero_en_letras(clave: str) -> bool:
    return clave in UNIDADES or clave in DECENAS or clave in CENTENAS or clave in MAGNITUDES or clave in ("medio", "media")


def leer_en_letras(claves: list[str]) -> float | None:
    """Valor de una cadena de palabras numéricas («ocho millones quinientos mil» → 8 500 000); None si no es un número bien formado."""
    total, actual = 0.0, 0.0
    ultimo_millon = False
    vistos = 0
    for i, c in enumerate(claves):
        if c == "y":
            continue
        if c in UNIDADES:
            actual += UNIDADES[c]
        elif c in DECENAS:
            actual += DECENAS[c]
        elif c in CENTENAS:
            actual += CENTENAS[c]
        elif c in ("medio", "media"):
            if ultimo_millon and actual == 0:
                total += 500_000
            else:
                actual += 0.5
        elif c == "mil":
            total += (actual or 1) * 1_000
            actual = 0.0
        elif c in ("millon", "millones", "billon", "billones"):
            base = total + actual if (total or actual) else 1.0
            total = base * MAGNITUDES[c]
            actual = 0.0
            ultimo_millon = c in ("millon", "millones")
        else:
            return None
        vistos += 1
    return float(total + actual) if vistos else None


def _numero_digitos(texto: str) -> tuple[float, str, str] | None:
    """(valor, prefijo, sufijo) de un token con dígitos; ignora puntuación final. None si no es un número."""
    limpio = texto.strip().rstrip(".,;:!?»”\"')")
    prefijo = "$" if limpio.startswith("$") else ""
    limpio = limpio.lstrip("$")
    sufijo = "%" if limpio.endswith("%") else ""
    limpio = limpio.rstrip("%")
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", limpio):
        return float(re.sub(r"[.,]", "", limpio)), prefijo, sufijo
    if re.fullmatch(r"\d+", limpio):
        return float(limpio), prefijo, sufijo
    if re.fullmatch(r"\d+[.,]\d{1,2}", limpio):
        return float(limpio.replace(",", ".")), prefijo, sufijo
    return None


def encontrar(palabras: list[Palabra]) -> list[dict]:
    """Cifras dichas, en orden: [{ini, fin, valor, clase, texto, antes, despues, i0, i1}].
    clase: «dinero» (con moneda o con una palabra como «cuesta»/«descuento»), «porcentaje» o «cantidad»."""
    p = unir_fragmentos(palabras)
    claves = [plano(t) for _i, _f, t in p]
    n = len(p)
    hallazgos: list[dict] = []
    i = 0
    while i < n:
        ini, _f, texto = p[i]
        leido = _numero_digitos(texto) if re.search(r"\d", texto) else None
        j = i + 1
        valor: float | None = None
        prefijo = sufijo = ""
        if leido is not None:
            valor, prefijo, sufijo = leido
            # «300 mil», «2 millones», «1,5 millones», «2 mil 500», «2 millones y medio»
            if not sufijo and j < n and claves[j] in MAGNITUDES:
                multiplicador = MAGNITUDES[claves[j]]
                valor *= multiplicador
                j += 1
                if multiplicador == 1_000 and j < n and re.fullmatch(r"\d{1,3}", claves[j]) and 0 < int(claves[j]) < 1000:
                    valor += int(claves[j])
                    j += 1
                elif multiplicador == 1_000_000 and j + 1 < n and claves[j] == "y" and claves[j + 1] in ("medio", "media"):
                    valor += 500_000
                    j += 2
        elif _es_numero_en_letras(claves[i]):
            k = i
            while k < n and (_es_numero_en_letras(claves[k]) or (claves[k] == "y" and k + 1 < n and _es_numero_en_letras(claves[k + 1]) and k > i)):
                k += 1
            # «un», «una», «uno» sueltos son artículos o pronombres: solo cuentan si siguen a una moneda o a una magnitud
            tramo = claves[i:k]
            if tramo in (["un"], ["una"], ["uno"]) and not (k < n and (claves[k] in MAGNITUDES or claves[k] in MONEDAS)):
                i += 1
                continue
            if tramo[-1] == "y":
                tramo, k = tramo[:-1], k - 1
            valor = leer_en_letras(tramo)
            if valor is None:
                i += 1
                continue
            j = k
        if valor is None:
            i += 1
            continue
        # porcentaje en letras: «veinte por ciento»
        if j + 1 < n and claves[j] == "por" and claves[j + 1] == "ciento":
            sufijo, j = "%", j + 2
        elif j < n and claves[j] in ("porciento", "porcentaje"):
            sufijo, j = "%", j + 1
        fin = p[j - 1][1]
        antes = claves[max(0, i - 8):i]
        despues = claves[j:j + 4]
        moneda = prefijo == "$" or any(c in MONEDAS for c in despues[:2])
        pista = any(c in PISTAS_DINERO for c in antes[-4:])
        clase = "porcentaje" if sufijo == "%" else "dinero" if (moneda or (pista and valor >= 1000)) else "cantidad"
        hallazgos.append({"ini": round(ini, 2), "fin": round(fin, 2), "valor": int(valor) if float(valor).is_integer() else round(valor, 2), "clase": clase,
                          "texto": " ".join(t for _a, _b, t in p[i:j]), "antes": antes, "despues": despues, "i0": i, "i1": j})
        i = max(j, i + 1)
    return hallazgos


# ---------------------------------------------------------------------------------------------------------------------
# De cifras a operaciones de calculadora
# ---------------------------------------------------------------------------------------------------------------------

OPERACIONES = ("fijar", "sumar", "restar", "restar_pct", "total", "mostrar")


def _pista(cifra: dict) -> str | None:
    """Qué hace esta cifra según las palabras que la rodean: «total», «restar», «sumar» o None."""
    contexto = set(cifra["antes"][-5:]) | set(cifra["despues"][:2])
    if contexto & PISTAS_TOTAL and not contexto & PISTAS_RESTA:
        return "total"
    if contexto & PISTAS_RESTA:
        return "restar"
    if contexto & PISTAS_SUMA:
        return "sumar"
    return None


ETIQUETAS_RESTA = {"descuento": "Descuento", "descuentos": "Descuento", "rebaja": "Rebaja", "rebajamos": "Rebaja", "rebajas": "Rebaja", "ahorras": "Ahorro", "ahorro": "Ahorro",
                   "ahorrarte": "Ahorro", "gasto": "Gasto", "gastos": "Gasto", "gastas": "Gasto", "bonificacion": "Bonificación", "subsidio": "Subsidio"}
ETIQUETAS_SUMA = {"extra": "Extra", "adicional": "Adicional", "adicionales": "Adicional", "recargo": "Recargo"}


def _etiqueta(op: str, cifra: dict) -> str:
    """Rótulo corto del paso, tomado de la palabra que lo anuncia («descuento», «gasto»…)."""
    contexto = cifra["antes"][-5:] + cifra["despues"][:2]
    if op in ("restar", "restar_pct"):
        return next((ETIQUETAS_RESTA[c] for c in contexto if c in ETIQUETAS_RESTA), "Menos")
    if op == "sumar":
        return next((ETIQUETAS_SUMA[c] for c in contexto if c in ETIQUETAS_SUMA), "Más")
    if op == "total":
        return "Total"
    if op == "fijar":
        return "Precio" if set(contexto) & {"cuesta", "cuestan", "vale", "valen", "precio", "costo", "valor"} else "Valor inicial"
    return "Valor"


def operaciones(cifras: list[dict], minimo_dinero: int = 10, ajustes: list[dict] | None = None) -> list[dict]:
    """Eventos de la calculadora a partir de las cifras dichas: [{t, dur, op, valor, de, a, derivado, texto, concepto}].
    La primera cifra de dinero fija el valor de partida; «descuento», «menos»… restan; «más», «extra»… suman; «queda en», «total»… muestran el resultado dicho.
    Una cifra sin pista que llega después de la primera solo se muestra, sin cambiar el total (puede ser el valor de un regalo, por ejemplo).
    `ajustes`: [{t, op}] corrigen qué hace una cifra (los propone el director); los valores siempre se recalculan aquí, nunca vienen de fuera.
    `derivado` es verdadero cuando el número en pantalla lo calculó Iris y no se dice así en el video."""
    eventos: list[dict] = []
    total: float | None = None
    for c in cifras:
        if c["clase"] == "cantidad" or (c["clase"] == "dinero" and c["valor"] < minimo_dinero):
            continue
        pista = _pista(c)
        forzada = next((a["op"] for a in (ajustes or []) if abs(a["t"] - c["ini"]) <= 0.7), None)
        if forzada == "mostrar":
            pista = "mostrar"
        elif forzada in ("restar", "restar_pct"):
            pista = "restar"
        elif forzada in ("sumar", "total"):
            pista = forzada
        dur = round(max(0.7, min(1.6, c["fin"] - c["ini"])), 2)
        ev = {"t": c["ini"], "dur": dur, "valor": c["valor"], "texto": c["texto"], "clase": c["clase"], "derivado": False}
        if pista == "mostrar":
            ev.update(op="mostrar", de=None, a=None)
        elif c["clase"] == "porcentaje":
            if pista == "restar" and total is not None:
                nuevo = round(total * (1 - c["valor"] / 100))
                ev.update(op="restar_pct", de=round(total), a=nuevo, derivado=True)
                total = nuevo
            else:
                ev.update(op="mostrar", de=None, a=None)
        elif total is None and pista in ("restar", "sumar", "total"):
            ev.update(op="mostrar", de=None, a=None)  # sin valor de partida no se puede calcular: solo se muestra lo dicho
        elif total is None:
            ev.update(op="fijar", de=0, a=c["valor"])
            total = float(c["valor"])
        elif pista == "total":
            ev.update(op="total", de=round(total), a=c["valor"], calculado=round(total))
            total = float(c["valor"])
        elif pista == "restar":
            nuevo = round(total - c["valor"])
            ev.update(op="restar", de=round(total), a=nuevo, derivado=True)
            total = float(nuevo)
        elif pista == "sumar":
            nuevo = round(total + c["valor"])
            ev.update(op="sumar", de=round(total), a=nuevo, derivado=True)
            total = float(nuevo)
        else:
            ev.update(op="mostrar", de=None, a=None)
        ev["etiqueta"] = _etiqueta(ev["op"], c)
        eventos.append(ev)
    return eventos


def formato_es(valor: float, moneda: str = "") -> str:
    """8500000 → «$8.500.000» (puntos como separador de miles, como se escribe en español)."""
    entero = f"{abs(round(valor)):,}".replace(",", ".")
    return f"{'-' if valor < 0 else ''}{moneda}{entero}"
