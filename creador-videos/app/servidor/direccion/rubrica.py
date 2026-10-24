"""La rúbrica: cómo debe comportarse el director, escrito como criterios que se pueden comprobar.
Se usa en las pruebas (con una IA simulada) y en `./creador director` (con la IA real) para calificar un plan y el guion que salió de él."""
from __future__ import annotations

import re

from ..logica_texto import normalizar
from . import perfil as perfiles
from . import plan as planes

ZONA_SUPERIOR = 14.0   # % de alto que Meta pide dejar libre arriba en Reels
ZONA_INFERIOR = 35.0   # y abajo


def _textos_en_pantalla(plan: dict, guion: dict) -> list[str]:
    textos = [plan["gancho"]["texto"]] if plan["gancho"]["texto"] else []
    textos += [c.get("texto", "") for c in guion.get("capas", []) if c.get("tipo") in ("palabra", "tarjeta") and c.get("texto")]
    textos += [m["texto"] for m in plan["momentos"] if m.get("texto")]
    return [t for t in textos if t]


def evaluar(plan: dict, guion: dict, contexto: dict) -> list[dict]:
    """Lista de criterios con `ok` y una frase. Todos los `ok` en True = el plan cumple lo que se espera del director."""
    ef = perfiles.efectos(contexto.get("perfil"))
    fuente = planes.fuentes(contexto)
    duracion = float(contexto.get("duracion") or guion.get("duracion") or 0)
    config = contexto.get("config") or {}
    palabras = contexto.get("palabras", [])
    resultados: list[dict] = []

    def criterio(id_: str, ok: bool, texto: str) -> None:
        resultados.append({"id": id_, "ok": bool(ok), "texto": texto})

    gancho = plan["gancho"]["texto"]
    capa_gancho = next((c for c in guion.get("capas", []) if c.get("tipo") == "palabra" and c.get("texto") == gancho), None) if gancho else None
    habla_pronto = bool(palabras) and palabras[0][0] <= 1.0
    criterio("gancho_en_3s", (capa_gancho is not None and capa_gancho["ini"] <= 0.6 and capa_gancho["fin"] <= 3.4) or habla_pronto,
             "Hay mensaje en los 3 primeros segundos (texto de gancho o voz desde el inicio)")
    criterio("gancho_corto", not gancho or (len(gancho.split()) <= planes.PALABRAS_MAX_GANCHO and len(gancho) <= planes.CARACTERES_MAX_GANCHO),
             f"El gancho cabe en pantalla (hasta {planes.PALABRAS_MAX_GANCHO} palabras)")

    textos = _textos_en_pantalla(plan, guion)
    inventadas = [t for t in textos if planes._cifras(t) - fuente["cifras"]]
    criterio("sin_cifras_inventadas", not inventadas, "Ninguna cifra en pantalla sale de la nada" + (f": {inventadas[0]!r}" if inventadas else ""))
    contadores_mal = [c for c in guion.get("capas", []) if c.get("tipo") == "contador" and str(int(c.get("hasta", 0))) not in fuente["cifras"]]
    criterio("contadores_dichos", not contadores_mal, "Todo contador cuenta hacia una cifra que se dice en el video")
    sin_respaldo = [t for t in textos if t != gancho and not planes._texto_respaldado(t, fuente)]
    criterio("texto_respaldado", not sin_respaldo, "Las tarjetas y palabras en pantalla salen del video o del brief")
    hablado = {normalizar(p[2]) for p in palabras}
    criterio("claves_dichas", all(normalizar(c) in hablado for c in plan["claves"]), "Las palabras clave se dicen en el video")
    ilegales = [t for t in textos + plan["claves"] if planes._tiene_prohibidas(t, ef["prohibidas"])]
    criterio("sin_prohibidas", not ilegales, "Nada de lo que la marca «nunca» quiere ver" + (f": {ilegales[0]!r}" if ilegales else ""))

    piezas = len(guion.get("capas", [])) + len(guion.get("zooms", []))
    tope = duracion / max(3.0, ef["efectos_cada"]) * 1.6 + 3
    criterio("densidad", piezas <= tope, f"Cantidad de piezas razonable para {duracion:.0f} s ({piezas} de hasta {tope:.0f})")
    tiempos = sorted(m["t"] for m in plan["momentos"])
    criterio("separacion", all(b - a >= 2.0 for a, b in zip(tiempos, tiempos[1:])), "Los momentos de énfasis están separados al menos 2 s")
    fuera = [c for c in guion.get("capas", []) + guion.get("zooms", []) if c.get("ini", 0) < 0 or c.get("fin", duracion) > duracion + 0.05]
    criterio("tiempos_validos", not fuera, "Todo cae dentro de la duración del video")

    mal_ubicadas = [c for c in guion.get("capas", []) if c.get("tipo") in ("palabra", "tarjeta", "contador")
                    and not (ZONA_SUPERIOR <= float(c.get("y", 50)) <= 100 - ZONA_INFERIOR)]
    posicion = (guion.get("estiloPalabras") or {}).get("posicion")
    criterio("zona_segura", not mal_ubicadas and not (posicion == "abajo" and ef["canal"] in ("reels", "tiktok", "shorts", "anuncios")),
             "El texto queda fuera de las franjas que tapan las aplicaciones (14 % arriba, 35 % abajo)")

    criterio("respeta_interruptores",
             (config.get("acercamientos", True) or not guion.get("zooms"))
             and (config.get("contadores", True) or not any(c.get("tipo") == "contador" for c in guion.get("capas", [])))
             and (config.get("cierre", True) or not any(e.get("tipo") == "cta" for e in guion.get("escenas", []))),
             "No pone nada que la persona apagó")
    musica = contexto.get("musica")
    criterio("musica_coherente", (not plan["musica"]["usar"]) or musica is not None, "Solo propone música si hay una pista disponible")
    pulso = guion.get("pulso")
    criterio("pulso_con_confianza", pulso is None or (musica is not None and musica["confianza"] >= 0.55), "El pulso sobre la música solo se usa si el análisis es fiable")
    return resultados


def aprobada(resultados: list[dict]) -> bool:
    return all(r["ok"] for r in resultados)


def informe(resultados: list[dict]) -> str:
    return "\n".join(f"  {'✓' if r['ok'] else '✗'} {r['texto']}" for r in resultados)
