"""Conexión con Claude (SDK oficial de Anthropic) para dirigir el video.

Reglas de este módulo:
- La clave de la IA vive solo en el servidor: variable de entorno ANTHROPIC_API_KEY, un perfil de `ant auth login`, o el archivo
  `ia.json` de la carpeta de datos (permisos 600, fuera del repositorio). Nunca se devuelve al navegador.
- Si la IA falla por cualquier motivo, el video se hace igual con reglas y se cuenta por qué. Nada de esto tumba un trabajo.
- A la IA se le envía: el guion hablado con tiempos, el brief, la ficha de la marca, el test del director y datos de la música;
  y, solo si la persona lo activó, hasta 6 fotogramas pequeños.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import time
from pathlib import Path

import numeros

from .. import datos, formatos
from . import perfil as perfiles
from . import plan as planes

MODELO_POR_DEFECTO = "claude-opus-5-5"
# Precios por millón de tokens (lista pública; el costo mostrado es una ESTIMACIÓN).
MODELOS = {
    "claude-opus-5-5": {"nombre": "Calidad máxima (Claude Opus 5.5)", "entrada": 4.0, "salida": 20.0},
    "claude-sonnet-5-5": {"nombre": "Equilibrado y más barato (Claude Sonnet 5.5)", "entrada": 2.0, "salida": 10.0},
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
_fabrica = None  # las pruebas ponen aquí una función que devuelve un cliente simulado

SISTEMA = """Eres director creativo audiovisual y editor senior de publicidad para marcas, con más de 20 años de oficio. Recibes el material de UN video corto vertical (el guion hablado con tiempos, el brief, la ficha de la marca, las preferencias del cliente y datos de la música) y decides cómo editarlo. Cada decisión tiene que servir al mensaje y a la retención; no decoras por decorar.

Criterios del oficio:
- Gancho: en los primeros 3 segundos tiene que haber una promesa, una pregunta o un resultado claro. Si la persona ya lo dice, resáltalo con las palabras clave; si no, propón un texto corto (máximo 7 palabras) que resuma la promesa con lo que SÍ dice el video.
- Ritmo: un cambio visual (acercamiento o pieza en pantalla) por cada idea nueva, no por llenar. Menos es más, y respetas el nivel de piezas que pidió el cliente.
- Palabras clave: solo las que la persona dice y que cargan el sentido (resultado, cifra, objeción, acción).
- Música y acabado: elige lo que acompañe el tono de la marca; la voz manda siempre.
- Plataforma: el texto va fuera de las franjas superior (14 %) e inferior (35 %) de la pantalla.
- Marca: respeta su tono y todo lo que nunca debe aparecer.

El brief de la persona es la instrucción principal: léelo entero y cumple todo lo que Iris puede hacer. Lo que Iris sabe construir:
- Subtítulos palabra por palabra con palabras clave en grande, acercamientos, pasos numerados (solo si se dicen en voz alta), tarjetas con frases del video, gancho en pantalla y cierre con palabra clave.
- Calculadora de dinero: muestra el precio, resta descuentos, suma extras y confirma el total con las cifras que se DICEN. Tú no escribes cifras: solo dices qué hace cada una (restar, sumar, total, mostrar) en «calculadora.ajustes», indicando el segundo en que se dice; el código lee las cifras y calcula.
- Transiciones (destello, barrido, impacto) sobre los cortes reales entre escenas o pausas quitadas; tú eliges el estilo, no el instante.
- Efectos de sonido sintetizados (ninguno, sutil, marcado), logo animado de la marca (cierre, intro o marca de agua), quitar pausas, música de la biblioteca y acabado de color.
- Formato: dinero (calculadora), subtitulos, pasos o antes-despues. Elige el que mejor sirva al brief.
Por cada cosa que pida el brief escribe una entrada en «requisitos»: el pedido con sus palabras, la capacidad de Iris que lo cubre y una nota breve. Si Iris no puede hacerlo, usa la capacidad «otra» y explica por qué en la nota; no prometas lo que no puedes construir.

Reglas duras:
- Usa SOLO hechos que estén en el guion hablado, el brief o la ficha. No inventes cifras, precios, nombres, plazos ni promesas. Si una cifra no se dice en el video, no la uses.
- Lo que la marca «nunca» quiere es una prohibición absoluta.
- Los tiempos (t) son segundos desde el inicio y deben caer en un momento en que alguien habla.
- Si algo te preocupa del material (audio flojo, gancho débil, promesa arriesgada), escríbelo en «alertas», en español claro y breve.
- Responde únicamente con el JSON del esquema."""


# ------------------------------------------------------------------------------------------------------------------
# Ajustes y clave
# ------------------------------------------------------------------------------------------------------------------

def _archivo() -> Path:
    return datos.DATOS / "ia.json"


def _leer_archivo() -> dict:
    try:
        bruto = json.loads(_archivo().read_text(encoding="utf-8"))
        return bruto if isinstance(bruto, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_ajustes(cambios: dict) -> None:
    """Guarda los ajustes (y la clave, si viene) con permisos 600, de forma atómica."""
    actual = _leer_archivo()
    if "clave" in cambios:
        clave = str(cambios["clave"] or "").strip()
        if clave:
            actual["clave"] = clave
        else:
            actual.pop("clave", None)
    if "activa" in cambios:
        actual["activa"] = bool(cambios["activa"])
    if "ver_fotogramas" in cambios:
        actual["ver_fotogramas"] = bool(cambios["ver_fotogramas"])
    if "consentimiento" in cambios:  # la persona confirma qué datos se envían a Anthropic; queda la fecha
        if cambios["consentimiento"]:
            actual["consentimiento_ia"] = time.strftime("%Y-%m-%d")
        else:
            actual.pop("consentimiento_ia", None)
    if cambios.get("modelo") in MODELOS:
        actual["modelo"] = cambios["modelo"]
    destino = _archivo()
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = destino.with_suffix(".tmp")
    descriptor = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
        json.dump(actual, archivo)
    os.chmod(temporal, 0o600)
    os.replace(temporal, destino)


def _clave() -> tuple[str | None, str | None]:
    """(origen, clave). Origen: «entorno» o «archivo». Los perfiles de `ant auth login` no exponen clave: el SDK los resuelve solo."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "entorno", os.environ["ANTHROPIC_API_KEY"]
    guardada = _leer_archivo().get("clave")
    return ("archivo", guardada) if guardada else (None, None)


_credenciales_cache: tuple[float, bool] = (0.0, False)


def _credenciales_del_sdk() -> bool:
    """¿El SDK encuentra credenciales por su cuenta (perfil de `ant auth login`, etc.)? Se recuerda 30 s para no crear un cliente en cada consulta."""
    global _credenciales_cache
    ahora = time.time()
    if ahora - _credenciales_cache[0] < 30:
        return _credenciales_cache[1]
    try:
        import anthropic
        cliente = anthropic.Anthropic()
        validar = getattr(cliente, "_validate_headers", None)  # construir el cliente no basta: esto falla si no hay con qué autenticarse
        if validar is not None:
            validar({}, {})
        encontrado = True
    except Exception:  # noqa: BLE001 - cualquier fallo significa «no hay credenciales»
        encontrado = False
    _credenciales_cache = (ahora, encontrado)
    return encontrado


def estado_publico() -> dict:
    """Lo que el navegador puede saber: si hay IA disponible y cómo está configurada. Nunca la clave."""
    ajustes = _leer_archivo()
    origen, clave = _clave()
    if origen is None and _credenciales_del_sdk():
        origen = "perfil"
    disponible = origen is not None or _fabrica is not None
    consentida = bool(ajustes.get("consentimiento_ia"))
    modelo = ajustes.get("modelo") if ajustes.get("modelo") in MODELOS else MODELO_POR_DEFECTO
    return {
        "disponible": disponible,
        "origen": origen,
        "final_clave": f"…{clave[-4:]}" if clave and origen == "archivo" else None,
        "consentida": consentida,
        "consentida_en": ajustes.get("consentimiento_ia"),
        "activa": bool(ajustes.get("activa", True)) and disponible and consentida,
        "costo_estimado_usd": costo_estimado(modelo, *TOKENS_TIPICOS),
        "gastado_mes_usd": gastado_en_el_mes(),
        "modelo": modelo,
        "modelos": [{"id": k, "nombre": v["nombre"]} for k, v in MODELOS.items()],
        "ver_fotogramas": bool(ajustes.get("ver_fotogramas", False)),
    }


def crear_cliente():
    if _fabrica is not None:
        return _fabrica()
    import anthropic
    origen, clave = _clave()
    return anthropic.Anthropic(api_key=clave, max_retries=2, timeout=180.0) if origen == "archivo" else anthropic.Anthropic(max_retries=2, timeout=180.0)


def probar_clave(modelo: str | None = None) -> tuple[bool, str]:
    """Comprueba la clave sin generar nada (contar tokens no cuesta)."""
    try:
        cliente = crear_cliente()
        cliente.messages.count_tokens(model=modelo or MODELO_POR_DEFECTO, messages=[{"role": "user", "content": "ok"}])
        return True, "La IA responde. Todo listo."
    except Exception as error:  # noqa: BLE001
        return False, mensaje_de_error(error)


def mensaje_de_error(error: Exception) -> str:
    """El error de la IA en una frase que se entienda."""
    nombre = type(error).__name__
    texto = str(error).lower()
    if nombre == "AuthenticationError":
        return "La clave de la IA no es válida."
    if nombre == "PermissionDeniedError":
        return "La clave de la IA no tiene permiso para este modelo."
    if nombre == "RateLimitError":
        return "La IA está saturada en este momento."
    if nombre in ("APIConnectionError", "APITimeoutError"):
        return "No pude conectar con la IA. ¿Hay internet?"
    if "credit balance" in texto or "billing" in texto:
        return "La cuenta de la IA no tiene saldo."
    if nombre == "BadRequestError":
        return "La IA rechazó la petición: " + re.sub(r"\s+", " ", str(error))[:140]
    if nombre == "AnthropicError":
        return "No hay una clave de IA configurada."
    if nombre == "InternalServerError" or "overloaded" in texto:
        return "La IA tuvo un problema del lado del servicio."
    return "La IA falló (" + nombre + ")."


# ------------------------------------------------------------------------------------------------------------------
# Petición
# ------------------------------------------------------------------------------------------------------------------

def _frases(palabras: list, maximo: int = 8000) -> str:
    """El guion hablado agrupado por frases con su tiempo: «[3.2-6.8] texto»."""
    lineas, inicio, fin, trozo = [], None, 0.0, []
    for ini, f, texto in palabras:
        inicio = ini if inicio is None else inicio
        trozo.append(texto)
        fin = f
        if re.search(r"[.?!]$", texto.strip()) or len(trozo) >= 22:
            lineas.append(f"[{inicio:.1f}-{fin:.1f}] {' '.join(trozo)}")
            inicio, trozo = None, []
    if trozo:
        lineas.append(f"[{inicio:.1f}-{fin:.1f}] {' '.join(trozo)}")
    return "\n".join(lineas)[:maximo]


def texto_de_contexto(contexto: dict) -> str:
    musica = contexto.get("musica")
    referencia = contexto.get("referencia")
    config = contexto.get("config") or {}
    nombres = {"calculadora": "calculadora de dinero", "transiciones": "transiciones", "sonidos": "efectos de sonido", "logo": "logo animado", "acercamientos": "acercamientos",
               "contadores": "contadores de cifras", "cierre": "cierre con palabra clave", "quitar_pausas": "quitar pausas", "musica": "música"}
    fijados = [f"{nombres[k]}: {'sí' if config[k] else 'no'}" for k in nombres if config.get(k) is not None and config.get("origenes", {}).get(k) in ("manual", "texto", "formato")]
    cortes = contexto.get("cortes") or []
    dichas = [c for c in numeros.encontrar(contexto.get("palabras", [])) if c["clase"] in ("dinero", "porcentaje")]
    formato = formatos.FORMATOS.get(config.get("formato") or "auto", {}).get("nombre", "Automático")
    segundos_cortes = ", ".join("%.1f" % c["t"] for c in cortes[:12])
    partes = [
        f"Brief de la persona (instrucción principal): {contexto.get('brief') or '(sin brief: decide con criterio profesional)'}",
        f"Marca: {contexto.get('marca_nombre') or 'sin marca'}",
        "Ficha de la marca (memoria del equipo):\n" + (contexto.get("ficha") or "(sin ficha)")[:3000],
        "Preferencias del cliente (test del director):\n" + perfiles.a_texto(contexto.get("perfil")),
        f"Duración: {contexto.get('duracion')} s, {'vertical' if contexto.get('vertical', True) else 'horizontal'}",
        f"Formato: {formato}" + (" (lo eligió la persona o su texto)" if config.get("formato_origen") in ("manual", "texto") else " (sin elegir: decide tú según el brief y lo que se dice)"),
        f"Escenas unidas: {contexto.get('escenas', 1)}. " + ("Cortes reales donde caben transiciones (segundos): " + segundos_cortes + "." if cortes else "No hay cortes: las transiciones no tienen dónde ir."),
        "Logo de la marca subido: " + ("sí" if contexto.get("tiene_logo") else "no (no propongas logo)"),
        "Fijado por la persona o por su texto (respétalo): " + (", ".join(fijados) if fijados else "nada; decide tú") + ".",
    ]
    if dichas:
        partes.append("Cifras de dinero o porcentajes que se dicen (segundo, texto): " + "; ".join(f"[{c['ini']:.1f}] {c['texto']}" for c in dichas[:12]))
    if referencia:
        partes.append(f"Referencias elegidas: {referencia.get('ritmo')} cortes por cada 10 s, unas {referencia.get('ppm') or '?'} palabras por minuto.")
    if musica:
        partes.append(f"Música candidata de la biblioteca: {musica['bpm']} BPM ({musica['ritmo']}), energía {musica['intensidad']}, "
                      f"confianza del análisis {musica['confianza']:.0%}.")
    else:
        partes.append("No hay música disponible: no propongas usarla.")
    partes.append("Guion hablado con tiempos (segundos):\n" + (_frases(contexto.get("palabras", [])) or "(no se oyó voz)"))
    return "\n\n".join(partes)


def fotogramas(video: Path, duracion: float, cantidad: int = 6) -> list[tuple[float, bytes]]:
    """Fotogramas pequeños repartidos por el video (JPEG de 512 px de ancho)."""
    salida = []
    for k in range(cantidad):
        t = duracion * (k + 0.5) / cantidad
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=512:-2", "-q:v", "6",
                            "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True)
        if r.returncode == 0 and r.stdout:
            salida.append((round(t, 1), r.stdout))
    return salida


def construir_peticion(contexto: dict, modelo: str, imagenes: list[tuple[float, bytes]] | None = None) -> dict:
    contenido: list[dict] = [{"type": "text", "text": texto_de_contexto(contexto)}]
    for t, jpeg in imagenes or []:
        contenido.append({"type": "text", "text": f"Fotograma del material en t = {t} s:"})
        contenido.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(jpeg).decode("ascii")}})
    return {"model": modelo, "max_tokens": 16000, "system": SISTEMA, "messages": [{"role": "user", "content": contenido}],
            "output_config": {"effort": "high", "format": {"type": "json_schema", "schema": planes.ESQUEMA}}}


TOKENS_TIPICOS = (3500, 4500)  # lo que suele gastar un video de un minuto: sirve para mostrar el costo antes de crearlo


def gastado_en_el_mes() -> float:
    """Suma de lo que costaron (estimado) los videos dirigidos con IA este mes, para que nada de dinero sea una sorpresa."""
    mes = time.strftime("%Y-%m")
    total = 0.0
    for fila in datos.todos("SELECT ia_info, actualizado FROM trabajos WHERE ia_info IS NOT NULL"):
        info = fila["ia_info"] or {}
        if info.get("costo_usd") and time.strftime("%Y-%m", time.localtime(fila["actualizado"] or 0)) == mes:
            total += info["costo_usd"]
    return round(total, 2)


def costo_estimado(modelo: str, entrada: int, salida: int) -> float | None:
    precios = MODELOS.get(modelo)
    return round((entrada * precios["entrada"] + salida * precios["salida"]) / 1_000_000, 4) if precios else None


def _llamar(cliente, peticion: dict):
    """Llama con reintento por fallos de modelo (server-side fallbacks); si el servicio no acepta esa opción, repite sin ella."""
    try:
        return cliente.beta.messages.create(**peticion, betas=[FALLBACK_BETA], fallbacks="default")
    except Exception as error:  # noqa: BLE001
        texto = str(error).lower()
        if type(error).__name__ == "BadRequestError" and ("fallback" in texto or "beta" in texto):
            return cliente.messages.create(**peticion)
        raise


def generar_plan(contexto: dict, video: Path | None = None) -> dict:
    """Pide el plan a la IA. Devuelve siempre un resultado: `plan` es None si hay que usar reglas, y `motivo` dice por qué."""
    estado = estado_publico()
    resultado = {"plan": None, "origen": "reglas", "motivo": None, "advertencias": [], "modelo": None, "uso": None, "costo_usd": None}
    if not estado["activa"]:
        if not estado["disponible"]:
            resultado["motivo"] = None
        elif not estado["consentida"]:
            resultado["motivo"] = "Falta confirmar qué datos se envían a la IA (menú de tu cuenta → Director con IA)."
        else:
            resultado["motivo"] = "La IA está desactivada en los ajustes."
        return resultado
    modelo = estado["modelo"]
    resultado["modelo"] = modelo
    try:
        imagenes = fotogramas(video, contexto["duracion"]) if (estado["ver_fotogramas"] and video) else None
        respuesta = _llamar(crear_cliente(), construir_peticion(contexto, modelo, imagenes))
    except Exception as error:  # noqa: BLE001 - la IA nunca tumba un trabajo
        resultado["motivo"] = mensaje_de_error(error)
        return resultado
    uso = getattr(respuesta, "usage", None)
    if uso is not None:
        resultado["uso"] = {"entrada": getattr(uso, "input_tokens", 0) or 0, "salida": getattr(uso, "output_tokens", 0) or 0}
        resultado["costo_usd"] = costo_estimado(modelo, resultado["uso"]["entrada"], resultado["uso"]["salida"])
    if getattr(respuesta, "stop_reason", None) == "refusal":
        resultado["motivo"] = "La IA declinó dirigir este contenido."
        return resultado
    texto = next((b.text for b in getattr(respuesta, "content", []) if getattr(b, "type", None) == "text"), "")
    try:
        bruto = json.loads(texto)
    except ValueError:
        resultado["motivo"] = "La IA no devolvió un plan legible."
        return resultado
    plan, advertencias = planes.sanear(bruto, contexto)
    resultado["advertencias"] = advertencias
    if plan is None:
        resultado["motivo"] = advertencias[0] if advertencias else "La IA no devolvió un plan útil."
        return resultado
    resultado.update(plan=plan, origen="ia")
    return resultado
