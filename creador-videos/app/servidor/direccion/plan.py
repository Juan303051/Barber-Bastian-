"""El plan del director: qué decide sobre el video (concepto, gancho, énfasis, música, acabado).

Lo propone una IA o, sin IA, unas reglas; en los dos casos pasa por `sanear`, que hace cumplir los límites:
nada de cifras ni datos que no estén en lo que dijo la persona, el brief o la ficha de la marca; nada de palabras prohibidas;
tiempos dentro del video y piezas bien separadas. La IA propone; el código decide qué se queda.
"""
from __future__ import annotations

import re
import unicodedata

from ..logica_texto import normalizar
from . import perfil as perfiles

TONOS = ["cercano", "experto", "divertido", "premium", "urgente"]
GANCHOS = ["pregunta", "paradoja", "resultado_primero", "promesa", "dato", "historia"]
MOMENTOS = ["acercamiento", "insignia", "contador", "tarjeta"]
LOOKS = ["natural", "calido", "frio", "cine", "vibrante"]
ENERGIAS = ["baja", "media", "alta"]
RITMOS = ["lento", "medio", "rapido"]

# Esquema de la respuesta de la IA (salida estructurada). Sin mínimos ni máximos: eso lo hace cumplir `sanear`.
ESQUEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["concepto", "gancho", "claves", "momentos", "cierre", "musica", "acabado", "segundos_entre_acercamientos", "alertas"],
    "properties": {
        "concepto": {"type": "object", "additionalProperties": False, "required": ["resumen", "tono", "tipo_de_gancho"], "properties": {
            "resumen": {"type": "string"}, "tono": {"type": "string", "enum": TONOS}, "tipo_de_gancho": {"type": "string", "enum": GANCHOS}}},
        "gancho": {"type": "object", "additionalProperties": False, "required": ["texto", "alternativas"], "properties": {
            "texto": {"type": "string"}, "alternativas": {"type": "array", "items": {"type": "string"}}}},
        "claves": {"type": "array", "items": {"type": "string"}},
        "momentos": {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": ["t", "tipo", "motivo"], "properties": {
            "t": {"type": "number"}, "tipo": {"type": "string", "enum": MOMENTOS}, "motivo": {"type": "string"},
            "texto": {"type": "string"}, "valor": {"type": "number"}}}},
        "cierre": {"type": "object", "additionalProperties": False, "required": ["clave"], "properties": {"clave": {"type": "string"}}},
        "musica": {"type": "object", "additionalProperties": False, "required": ["usar", "energia", "ritmo", "motivo"], "properties": {
            "usar": {"type": "boolean"}, "energia": {"type": "string", "enum": ENERGIAS}, "ritmo": {"type": "string", "enum": RITMOS}, "motivo": {"type": "string"}}},
        "acabado": {"type": "object", "additionalProperties": False, "required": ["look", "intensidad", "pulso"], "properties": {
            "look": {"type": "string", "enum": LOOKS}, "intensidad": {"type": "number"}, "pulso": {"type": "boolean"}}},
        "segundos_entre_acercamientos": {"type": "number"},
        "alertas": {"type": "array", "items": {"type": "string"}},
    },
}

PALABRAS_MAX_GANCHO = 7
CARACTERES_MAX_GANCHO = 52


def _fragmentos(texto: str) -> set[str]:
    return {normalizar(p) for p in re.split(r"\s+", texto) if normalizar(p)}


def _cifras(texto: str) -> set[str]:
    """Los números que aparecen escritos con dígitos (sin signos de miles)."""
    return {re.sub(r"[.,]", "", m) for m in re.findall(r"\d[\d.,]*", texto)}


def fuentes(contexto: dict) -> dict:
    """Todo lo que un texto en pantalla puede citar: lo dicho en el video, el brief, la ficha y el nombre de la marca."""
    dicho = " ".join(p[2] for p in contexto.get("palabras", []))
    resto = " ".join(str(contexto.get(c) or "") for c in ("brief", "ficha", "marca_nombre"))
    return {"dicho": dicho, "palabras": _fragmentos(dicho + " " + resto), "cifras": _cifras(dicho + " " + resto)}


def _plano(texto: str) -> str:
    """Minúsculas, sin acentos y con las palabras separadas por un espacio."""
    sin = unicodedata.normalize("NFD", texto.lower())
    return " ".join(re.findall(r"[a-z0-9ñ]+", "".join(c for c in sin if unicodedata.category(c) != "Mn")))


def _tiene_prohibidas(texto: str, prohibidas: list[str]) -> str | None:
    plano = _plano(texto)
    for p in prohibidas:
        limpia = _plano(p)
        if limpia and re.search(rf"(?<![a-z0-9ñ]){re.escape(limpia)}(?![a-z0-9ñ])", plano):
            return p
    return None


def _texto_respaldado(texto: str, fuente: dict, minimo: float = 0.7) -> bool:
    """Un texto de pantalla se acepta si casi todas sus palabras salen de las fuentes y todas sus cifras también."""
    palabras = [normalizar(p) for p in re.split(r"\s+", texto) if normalizar(p)]
    if not palabras:
        return False
    cifras = _cifras(texto)
    if cifras - fuente["cifras"]:
        return False
    conocidas = sum(1 for p in palabras if p in fuente["palabras"] or p.isdigit())
    return conocidas / len(palabras) >= minimo


def _limpiar_linea(texto: object, maximo: int) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f\"“”]", " ", str(texto or ""))).strip()[:maximo]


def plan_base(contexto: dict) -> dict:
    """Plan por reglas, sin IA: usa el test del director y la configuración. No inventa ganchos ni textos."""
    ef = perfiles.efectos(contexto.get("perfil"))
    energia = {"suave": "baja", "energica": "alta"}.get(ef["musica"])
    if energia is None:
        referencia = contexto.get("referencia") or {}
        energia = "alta" if (referencia.get("ritmo") or 0) >= 3 else "media"
    return {
        "concepto": {"resumen": "", "tono": (contexto.get("perfil") or {}).get("tono") or "cercano", "tipo_de_gancho": "promesa"},
        "gancho": {"texto": "", "alternativas": []},
        "claves": [],
        "momentos": [],
        "cierre": {"clave": ""},
        "musica": {"usar": ef["musica"] != "nunca", "energia": energia, "ritmo": {"pausado": "lento", "rapido": "rapido"}.get((contexto.get("perfil") or {}).get("ritmo"), "medio"),
                   "motivo": "Según el test del director" if contexto.get("perfil") else "Valores estándar"},
        "acabado": {"look": ef["acabado"] if ef["acabado"] in LOOKS else "natural", "intensidad": 0.5, "pulso": ef["musica"] != "nunca"},
        "segundos_entre_acercamientos": ef["zoom_s"],
        "alertas": [],
        "origen": "reglas",
    }


def sanear(bruto: object, contexto: dict) -> tuple[dict | None, list[str]]:
    """Convierte lo que devolvió la IA en un plan válido. Devuelve (plan, advertencias); None si no sirve para nada."""
    if not isinstance(bruto, dict):
        return None, ["La IA no devolvió un plan legible."]
    avisos: list[str] = []
    base = plan_base(contexto)
    plan = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in base.items()}
    ef = perfiles.efectos(contexto.get("perfil"))
    prohibidas = ef["prohibidas"]
    fuente = fuentes(contexto)
    duracion = float(contexto.get("duracion") or 0)

    concepto = bruto.get("concepto") if isinstance(bruto.get("concepto"), dict) else {}
    plan["concepto"] = {"resumen": _limpiar_linea(concepto.get("resumen"), 240),
                        "tono": concepto.get("tono") if concepto.get("tono") in TONOS else base["concepto"]["tono"],
                        "tipo_de_gancho": concepto.get("tipo_de_gancho") if concepto.get("tipo_de_gancho") in GANCHOS else "promesa"}

    gancho = bruto.get("gancho") if isinstance(bruto.get("gancho"), dict) else {}
    candidatos = [gancho.get("texto")] + list(gancho.get("alternativas") or [])[:3]
    validos: list[str] = []
    for candidato in candidatos:
        linea = _limpiar_linea(candidato, 200)
        if not linea:
            continue
        palabras = linea.split()
        if len(palabras) > PALABRAS_MAX_GANCHO or len(linea) > CARACTERES_MAX_GANCHO:
            avisos.append(f"Descarté un gancho demasiado largo: «{linea[:40]}…»")
            continue
        if (mala := _tiene_prohibidas(linea, prohibidas)):
            avisos.append(f"Descarté un gancho con una palabra que la marca no usa («{mala}»).")
            continue
        if _cifras(linea) - fuente["cifras"]:
            avisos.append(f"Descarté un gancho con una cifra que no está en tu video ni en el brief: «{linea}».")
            continue
        validos.append(linea)
    plan["gancho"] = {"texto": validos[0] if validos else "", "alternativas": validos[1:3]}

    claves, vistas = [], set()
    originales = {normalizar(p[2]): p[2].strip(".,;:!?¿¡\"“”") for p in contexto.get("palabras", [])}
    for c in (bruto.get("claves") or [])[:20]:
        clave = normalizar(str(c))
        if clave in originales and clave not in vistas and len(clave) >= 3 and not _tiene_prohibidas(originales[clave], prohibidas):
            claves.append(originales[clave])
            vistas.add(clave)
    if len(claves) < len([c for c in (bruto.get("claves") or []) if str(c).strip()]):
        avisos.append("Quité palabras clave que no se dicen en el video.")
    plan["claves"] = claves[:8]

    separacion = max(2.0, ef["efectos_cada"] * 0.6)
    momentos, ultimo = [], -99.0
    for m in sorted([m for m in (bruto.get("momentos") or []) if isinstance(m, dict)], key=lambda m: float(m.get("t") or 0)):
        tipo = m.get("tipo")
        try:
            t = float(m.get("t"))
        except (TypeError, ValueError):
            continue
        if tipo not in MOMENTOS or not (0.4 <= t <= max(0.5, duracion - 1.2)) or t - ultimo < separacion:
            continue
        item = {"t": round(t, 2), "tipo": tipo, "motivo": _limpiar_linea(m.get("motivo"), 140)}
        if tipo == "insignia":
            continue  # los pasos numerados salen de lo que se dice («primero, segundo…»); la IA no los inventa
        if tipo == "contador":
            valor = m.get("valor")
            if not isinstance(valor, (int, float)) or str(int(valor)) not in fuente["cifras"] or valor <= 0:
                avisos.append("Descarté un contador cuya cifra no se dice en el video.")
                continue
            item["valor"] = int(valor)
        if tipo == "tarjeta":
            texto = _limpiar_linea(m.get("texto"), 60)
            if not texto or not _texto_respaldado(texto, fuente) or _tiene_prohibidas(texto, prohibidas):
                avisos.append("Descarté una tarjeta con un texto que no sale de tu video ni del brief.")
                continue
            item["texto"] = texto
        momentos.append(item)
        ultimo = t
    plan["momentos"] = momentos[: max(1, int(duracion // max(3.0, ef["efectos_cada"])) + 1)]

    cierre = bruto.get("cierre") if isinstance(bruto.get("cierre"), dict) else {}
    clave = re.sub(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]", "", str(cierre.get("clave") or ""))[:20].upper()
    plan["cierre"] = {"clave": clave if clave and not _tiene_prohibidas(clave, prohibidas) else ""}

    musica = bruto.get("musica") if isinstance(bruto.get("musica"), dict) else {}
    plan["musica"] = {"usar": bool(musica.get("usar", base["musica"]["usar"])) and ef["musica"] != "nunca" and contexto.get("musica") is not None,
                      "energia": musica.get("energia") if musica.get("energia") in ENERGIAS else base["musica"]["energia"],
                      "ritmo": musica.get("ritmo") if musica.get("ritmo") in RITMOS else base["musica"]["ritmo"],
                      "motivo": _limpiar_linea(musica.get("motivo"), 160)}
    acabado = bruto.get("acabado") if isinstance(bruto.get("acabado"), dict) else {}
    look = acabado.get("look") if acabado.get("look") in LOOKS else base["acabado"]["look"]
    if ef["acabado"] in LOOKS:
        look = ef["acabado"]  # lo que la persona eligió en el test manda sobre la IA
    try:
        intensidad = min(0.8, max(0.1, float(acabado.get("intensidad", 0.5))))
    except (TypeError, ValueError):
        intensidad = 0.5
    plan["acabado"] = {"look": look, "intensidad": round(intensidad, 2), "pulso": bool(acabado.get("pulso", base["acabado"]["pulso"]))}
    try:
        plan["segundos_entre_acercamientos"] = min(9.0, max(2.5, float(bruto.get("segundos_entre_acercamientos"))))
    except (TypeError, ValueError):
        pass
    plan["alertas"] = [_limpiar_linea(a, 160) for a in (bruto.get("alertas") or []) if str(a).strip()][:5]
    plan["origen"] = "ia"
    return plan, avisos
