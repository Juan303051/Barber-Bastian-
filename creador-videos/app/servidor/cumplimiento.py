"""Cumplimiento de lo pedido: cada cosa que la persona escribió (o que la IA entendió del texto) se contrasta con lo que de verdad quedó en el video.

Lo decide el código mirando el guion y el audio terminado, no la IA: «hecho», «parcial», «no» (no se pudo) u «omitido» (la persona lo apagó), con el motivo en una frase.
Así la persona sabe qué pasó con cada petición en vez de suponerlo."""
from __future__ import annotations

import re

from .logica_texto import normalizar

NOMBRES = {"calculadora": "Calculadora de dinero", "transiciones": "Transiciones", "sonidos": "Efectos de sonido", "logo": "Logo animado", "quitar_pausas": "Quitar pausas largas",
           "musica": "Música de fondo", "palabras_clave": "Palabras en grande", "cierre": "Cierre con palabra clave", "acabado": "Acabado de color", "gancho": "Gancho en pantalla",
           "acercamientos": "Acercamientos", "pasos": "Pasos numerados", "tarjetas": "Tarjetas con frases del video", "antes_despues": "Antes y después", "subtitulos": "Subtítulos"}


def _fila(capacidad: str, estado: str, detalle: str, pedido: str | None = None) -> dict:
    return {"capacidad": capacidad, "pedido": pedido or NOMBRES.get(capacidad, capacidad), "estado": estado, "detalle": detalle}


def evaluar(config: dict, plan: dict, guion: dict, *, efectos: dict | None, musica: dict | None, tiene_logo: bool, pausas_quitadas: float | None, hay_cortes: bool) -> list[dict]:
    """Lista de filas {capacidad, pedido, estado, detalle}. Incluye lo que el texto pidió, lo que la IA entendió del texto y lo que la persona encendió a mano."""
    capas = guion.get("capas", [])
    de_tipo = lambda tipo: [c for c in capas if c.get("tipo") == tipo]  # noqa: E731
    filas: list[dict] = []

    def pedido_de(capacidad: str) -> bool:
        return capacidad in config.get("pide", []) or config.get("origenes", {}).get(capacidad) == "manual" and bool(config.get(capacidad))

    ia_pide = {r["capacidad"]: r for r in plan.get("requisitos", [])}

    def quiere(capacidad: str) -> bool:
        return pedido_de(capacidad) or capacidad in ia_pide

    if quiere("calculadora"):
        calc = de_tipo("calculadora")
        if calc:
            n = len(calc[0]["eventos"])
            derivados = sum(1 for e in calc[0]["eventos"] if e.get("derivado"))
            filas.append(_fila("calculadora", "hecho", f"{n} paso(s) con las cifras que dices" + (f"; en {derivados} el resultado lo calculó Iris, revísalo" if derivados else "")))
        elif config.get("calculadora") is False:
            filas.append(_fila("calculadora", "omitido", "Lo apagaste con el interruptor."))
        else:
            filas.append(_fila("calculadora", "no", "No oí cifras de dinero en el video (por ejemplo «ocho millones de pesos»)."))
    if quiere("transiciones"):
        n = len(de_tipo("transicion"))
        if n:
            filas.append(_fila("transiciones", "hecho", f"{n} transición(es) sobre los cortes del video"))
        elif config.get("transiciones") is False:
            filas.append(_fila("transiciones", "omitido", "Las apagaste con el interruptor."))
        else:
            filas.append(_fila("transiciones", "no", "El video no tiene cortes donde ponerlas: sube varias escenas o activa «Quitar pausas largas»." if not hay_cortes else "Los cortes quedaban demasiado cerca del inicio o del final."))
    if quiere("sonidos"):
        if efectos:
            filas.append(_fila("sonidos", "hecho", f"{efectos['cantidad']} efectos de sonido ({efectos['nivel']}) bajo tu voz"))
        elif config.get("sonidos") is False:
            filas.append(_fila("sonidos", "omitido", "Los apagaste con el interruptor."))
        else:
            filas.append(_fila("sonidos", "no", "No había piezas en pantalla a las que acompañar con sonido."))
    if quiere("logo"):
        puesto = de_tipo("logo") or ((guion.get("marca") or {}).get("logo") and any(e.get("tipo") == "cta" for e in guion.get("escenas", [])))
        if puesto:
            filas.append(_fila("logo", "hecho", "Logo animado de la marca"))
        elif not tiene_logo:
            filas.append(_fila("logo", "no", "Esta marca no tiene logo: súbelo en «Logo de la marca» y vuelve a crear el video."))
        elif config.get("logo") is False:
            filas.append(_fila("logo", "omitido", "Lo apagaste con el interruptor."))
        else:
            filas.append(_fila("logo", "no", "No hubo dónde colocarlo."))
    if quiere("pausas") or pedido_de("quitar_pausas"):
        if pausas_quitadas:
            filas.append(_fila("quitar_pausas", "hecho", f"Quité {pausas_quitadas:.1f} s de pausas"))
        elif config.get("quitar_pausas"):
            filas.append(_fila("quitar_pausas", "hecho", "No había pausas largas que quitar"))
        else:
            filas.append(_fila("quitar_pausas", "omitido", "Lo apagaste con el interruptor."))
    if quiere("musica") and config.get("musica") is not False:
        filas.append(_fila("musica", "hecho" if musica else "no", f"«{musica['titulo']}»" if musica else "Tu biblioteca no tiene canciones listas, o ninguna encajó."))
    if config.get("claves"):
        puestas = {normalizar(c) for c in (guion.get("estiloPalabras") or {}).get("claves", [])}
        dichas = {normalizar(p[2]) for p in guion.get("palabras", [])}
        sin_decir = [c for c in config["claves"] if normalizar(c) not in dichas]
        faltan = [c for c in config["claves"] if normalizar(c) not in puestas or c in sin_decir]
        estado = "hecho" if not faltan else "parcial" if len(faltan) < len(config["claves"]) else "no"
        detalle = "Todas puestas en grande" if not faltan else ("No se dicen en el video: " + ", ".join(sin_decir)) if sin_decir else "Faltan: " + ", ".join(faltan)
        filas.append(_fila("palabras_clave", estado, detalle, "Palabras en grande: " + ", ".join(config["claves"])))
    if quiere("cierre") or config.get("cta"):
        cta = next((e for e in guion.get("escenas", []) if e.get("tipo") == "cta"), None)
        filas.append(_fila("cierre", "hecho" if cta else "no", f"Cierre pidiendo comentar «{cta['clave']}»" if cta and cta.get("clave") else "Cierre con tu marca" if cta else "No encontré la palabra que debían comentar: dila en el video o escríbela en tu texto."))
    if quiere("antes_despues") or config.get("formato") == "antes-despues":
        filas.append(_fila("antes_despues", "hecho" if guion.get("diseno") == "antes-despues" else "no", "Tu toma cruda al lado de la editada" if guion.get("diseno") == "antes-despues" else "No se aplicó el formato."))
    if quiere("pasos"):
        n = len(de_tipo("insignia"))
        filas.append(_fila("pasos", "hecho" if n else "no", f"{n} paso(s) numerados" if n else "No dijiste «primero, segundo…» en voz alta, así que no hay pasos que numerar."))
    for r in plan.get("requisitos", []):
        if r["capacidad"] == "otra":
            filas.append(_fila("otra", "no", r["nota"] or "Iris todavía no puede hacer esto.", r["pedido"]))
    vistos, salida = set(), []
    for f in filas:
        clave = (f["capacidad"], f["pedido"])
        if clave not in vistos:
            vistos.add(clave)
            salida.append(f)
    return salida
