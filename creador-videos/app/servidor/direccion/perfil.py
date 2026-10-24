"""El «test del director»: preguntas cortas que fijan cómo quiere la marca sus videos. Se guarda por marca (o general) y lo usan
el director con IA y también las reglas cuando no hay IA."""
from __future__ import annotations

import json
import re

from .. import datos

PREGUNTAS: list[dict] = [
    {"id": "publico", "tipo": "texto", "max": 160, "texto": "¿A quién le hablan tus videos?", "ejemplo": "Dueños de moto que quieren gastar menos en mantenimiento"},
    {"id": "tono", "tipo": "uno", "texto": "¿Cómo debe sonar la marca?", "opciones": [
        ["cercano", "Cercano y de confianza"], ["experto", "Experto y claro"], ["divertido", "Divertido y con energía"],
        ["premium", "Premium y sobrio"], ["urgente", "Directo y urgente"]]},
    {"id": "ritmo", "tipo": "uno", "texto": "¿Qué ritmo de edición prefieres?", "opciones": [
        ["pausado", "Pausado: deja respirar"], ["medio", "Medio"], ["rapido", "Rápido: cambios seguidos"]]},
    {"id": "musica", "tipo": "uno", "texto": "¿Y la música de fondo?", "opciones": [
        ["segun", "Según el video"], ["suave", "Suave, casi no se nota"], ["energica", "Enérgica, que se sienta"], ["nunca", "Nunca"]]},
    {"id": "acabado", "tipo": "uno", "texto": "¿Qué acabado de color prefieres?", "opciones": [
        ["auto", "Que decida Iris"], ["natural", "Natural"], ["calido", "Cálido"], ["frio", "Frío"], ["cine", "Cine"], ["vibrante", "Vibrante"]]},
    {"id": "efectos", "tipo": "uno", "texto": "¿Cuántas piezas en pantalla (cifras, números, tarjetas)?", "opciones": [
        ["sobrio", "Pocas: solo lo esencial"], ["medio", "Las justas"], ["lleno", "Muchas, estilo cinético"]]},
    {"id": "canal", "tipo": "uno", "texto": "¿Dónde se publica sobre todo?", "opciones": [
        ["reels", "Instagram Reels"], ["tiktok", "TikTok"], ["shorts", "YouTube Shorts"], ["anuncios", "Anuncios pagados"]]},
    {"id": "cierre", "tipo": "texto", "max": 30, "texto": "¿Qué palabra suele pedirse comentar al final? (si usas cierre)", "ejemplo": "INFO"},
    {"id": "nunca", "tipo": "texto", "max": 300, "texto": "¿Qué no debe aparecer nunca? Palabras, promesas, temas", "ejemplo": "garantizado, el mejor del mundo, precios de la competencia"},
    {"id": "referentes", "tipo": "texto", "max": 200, "texto": "¿Marcas o creadores cuyo estilo te gusta? (opcional)", "ejemplo": "Red Bull, @jeann_content"},
]
_POR_ID = {p["id"]: p for p in PREGUNTAS}

# Lo que cada respuesta cambia aunque no haya IA.
RITMOS = {"pausado": {"zoom_cada": 3, "max_palabras": 3, "zoom_s": 6.5, "momentos_cada": 8.0},
          "medio": {"zoom_cada": 2, "max_palabras": 3, "zoom_s": 4.5, "momentos_cada": 5.0},
          "rapido": {"zoom_cada": 1, "max_palabras": 2, "zoom_s": 3.0, "momentos_cada": 3.5}}
EFECTOS_CADA = {"sobrio": 8.0, "medio": 5.0, "lleno": 3.0}


def _limpio(texto: object, maximo: int) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]+", " ", str(texto or ""))).strip()[:maximo]


def validar(respuestas: dict) -> tuple[dict, dict[str, str]]:
    """Devuelve (respuestas limpias, errores por pregunta). Lo desconocido se ignora; una opción inválida se rechaza."""
    limpias: dict = {}
    errores: dict[str, str] = {}
    for pregunta in PREGUNTAS:
        bruto = respuestas.get(pregunta["id"])
        if bruto in (None, ""):
            continue
        if pregunta["tipo"] == "uno":
            validas = {valor for valor, _ in pregunta["opciones"]}
            if bruto in validas:
                limpias[pregunta["id"]] = bruto
            else:
                errores[pregunta["id"]] = "Elige una de las opciones."
        else:
            limpias[pregunta["id"]] = _limpio(bruto, pregunta["max"])
    return {k: v for k, v in limpias.items() if v != ""}, errores


def palabras_prohibidas(perfil: dict | None) -> list[str]:
    """Las palabras o frases de «nunca», separadas por coma, punto y coma o salto de línea (en minúsculas)."""
    if not perfil or not perfil.get("nunca"):
        return []
    return [p.strip().lower() for p in re.split(r"[,;\n]", perfil["nunca"]) if len(p.strip()) >= 2][:30]


def a_texto(perfil: dict | None) -> str:
    """El perfil como frases para el director con IA."""
    if not perfil:
        return "Sin test del director: no hay preferencias de la marca, usa criterio profesional estándar."
    etiquetas = {p["id"]: dict(p["opciones"]) for p in PREGUNTAS if p["tipo"] == "uno"}
    lineas = []
    for pregunta in PREGUNTAS:
        valor = perfil.get(pregunta["id"])
        if valor:
            mostrado = etiquetas.get(pregunta["id"], {}).get(valor, valor)
            lineas.append(f"- {pregunta['texto']} {mostrado}")
    return "\n".join(lineas) or "Sin respuestas."


def efectos(perfil: dict | None) -> dict:
    """Ajustes numéricos que se aplican con o sin IA."""
    perfil = perfil or {}
    ritmo = RITMOS.get(perfil.get("ritmo", ""), RITMOS["medio"])
    return {**ritmo, "efectos_cada": EFECTOS_CADA.get(perfil.get("efectos", ""), 5.0), "musica": perfil.get("musica", "segun"),
            "acabado": perfil.get("acabado", "auto"), "canal": perfil.get("canal"), "cierre": perfil.get("cierre") or None,
            "prohibidas": palabras_prohibidas(perfil)}


# ------------------------------------------------------------------------------------------------------------------
# Guardar y leer
# ------------------------------------------------------------------------------------------------------------------

def guardar(marca: str | None, respuestas: dict) -> None:
    datos.ejecutar("INSERT OR REPLACE INTO perfiles (marca, datos, actualizado) VALUES (?, ?, ?)",
                   (marca or "", json.dumps(respuestas, ensure_ascii=False), datos.ahora()))


def leer(marca: str | None) -> dict | None:
    """El perfil de la marca; si no tiene, el general; si tampoco, None."""
    for clave in ([marca] if marca else []) + [""]:
        fila = datos.uno("SELECT datos FROM perfiles WHERE marca = ?", (clave,))
        if fila and fila["datos"]:
            return fila["datos"]
    return None


def leer_exacto(marca: str | None) -> dict | None:
    fila = datos.uno("SELECT datos FROM perfiles WHERE marca = ?", (marca or "",))
    return fila["datos"] if fila else None
