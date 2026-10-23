"""Junta las métricas de cada empresa en empresas/<empresa>/informe.md."""
from __future__ import annotations

import json
import statistics
from datetime import date
from pathlib import Path

from boveda import escribir_generado, frontmatter
from comun import boveda_empresa, carpeta_analisis, nombre, seguro


def cargar(carpeta: Path) -> list[dict]:
    filas = []
    for archivo in sorted(carpeta_analisis(carpeta).glob("*.analisis.json")):
        fila = json.loads(archivo.read_text(encoding="utf-8"))
        meta = archivo.with_name(archivo.name.replace(".analisis.json", ".meta.json"))
        fila["meta"] = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        filas.append(fila)
    return filas


def _vistas_por_dia(meta: dict) -> float | None:
    if not meta.get("vistas") or not meta.get("fecha_subida"):
        return None
    dias = (date.fromisoformat(meta["fecha_consulta"]) - date.fromisoformat(meta["fecha_subida"])).days
    return meta["vistas"] / max(dias, 1)


def _pct(parte, total) -> float | None:
    return round(parte / total * 100, 2) if parte is not None and total else None


def _texto(valor, formato="{}") -> str:
    return "—" if valor is None else formato.format(valor)


def indicadores(fila: dict) -> dict:
    meta, ritmo, audio, voz = fila["meta"], fila["ritmo"], fila["audio"] or {}, fila["voz"] or {}
    return {
        "duracion": fila["duracion"],
        "vistas": meta.get("vistas"),
        "vistas_dia": _vistas_por_dia(meta),
        "likes_pct": _pct(meta.get("likes"), meta.get("vistas")),
        "comentarios_pct": _pct(meta.get("comentarios"), meta.get("vistas")),
        "plano_mediano": ritmo["plano_mediano"],
        "cortes_por_10s": ritmo["cortes_por_10s"],
        "cortes_en_gancho": ritmo["cortes_en_gancho"],
        "lufs": audio.get("lufs"),
        "silencio_pct": audio.get("silencio_pct"),
        "palabras_por_min": voz.get("palabras_por_min"),
    }


def _tabla(filas: list[dict], slug: str, carpeta_nota: str) -> list[str]:
    encabezado = ("| Video | Plataforma | Dur. (s) | Vistas | Vistas/día | % likes | % coment. | "
                  "Plano mediano (s) | Cortes/10 s | Cortes en 3 s | LUFS | Silencio % | Palabras/min | Gancho dicho |")
    lineas = [encabezado, "|" + "---|" * 14]
    for fila in sorted(filas, key=lambda f: f["meta"].get("vistas") or 0, reverse=True):
        i, meta = indicadores(fila), fila["meta"]
        gancho = ((fila["voz"] or {}).get("gancho_texto") or meta.get("titulo") or "").replace("|", "/")[:70]
        lineas.append("| " + " | ".join([
            f"[[02-empresas/{slug}/{carpeta_nota}/{seguro(fila['id'])}\\|{fila['id']}]]", meta.get("plataforma") or "local", _texto(round(i["duracion"])),
            _texto(i["vistas"], "{:,}"), _texto(i["vistas_dia"] and round(i["vistas_dia"]), "{:,}"),
            _texto(i["likes_pct"]), _texto(i["comentarios_pct"]), _texto(i["plano_mediano"]),
            _texto(i["cortes_por_10s"]), _texto(i["cortes_en_gancho"]), _texto(i["lufs"]),
            _texto(i["silencio_pct"]), _texto(i["palabras_por_min"]), gancho]) + " |")
    return lineas


def _mediana(filas: list[dict], clave: str) -> float | None:
    valores = [v for v in (indicadores(f)[clave] for f in filas) if v is not None]
    return round(statistics.median(valores), 2) if valores else None


def _comparativa(refs: list[dict], propios: list[dict]) -> list[str]:
    nombres = [("duracion", "Duración (s)"), ("plano_mediano", "Plano mediano (s)"),
               ("cortes_por_10s", "Cortes por 10 s"), ("cortes_en_gancho", "Cortes en los 3 primeros s"),
               ("lufs", "Volumen (LUFS)"), ("silencio_pct", "Silencio %"), ("palabras_por_min", "Palabras/min")]
    lineas = [f"| Indicador (mediana) | Referencias ({len(refs)}) | Propios ({len(propios)}) |", "|---|---|---|"]
    for clave, etiqueta in nombres:
        lineas.append(f"| {etiqueta} | {_texto(_mediana(refs, clave))} | {_texto(_mediana(propios, clave))} |")
    return lineas


def informe(carpeta: Path) -> Path | None:
    filas = cargar(carpeta)
    if not filas:
        return None
    slug = carpeta.name
    base = boveda_empresa(carpeta)
    refs = [f for f in filas if f["tipo"] == "referencia"]
    propios = [f for f in filas if f["tipo"] == "propio"]
    lineas = [frontmatter({"tipo": "informe", "empresa": slug, "generado": True, "fecha": date.today().isoformat()}),
              f"# Informe — {nombre(carpeta)}", "",
              f"> Generado por `./creador informe`; se reescribe solo, no lo edites.", ""]
    if refs and propios:
        lineas += ["## Cómo editas tú frente a las referencias", ""] + _comparativa(refs, propios)
        if len(refs) < 3:
            lineas += ["", "_Con menos de 3 referencias son pistas, no patrones._"]
        lineas.append("")
    for titulo, grupo, carpeta_nota in (("Referencias", refs, "referencias"), ("Videos propios", propios, "propios")):
        if grupo:
            lineas += [f"## {titulo}", ""] + _tabla(grupo, slug, carpeta_nota) + [""]
    pendientes = [f for f in filas if not (base / "analisis" / f"{seguro(f['id'])}.md").exists()]
    if pendientes:
        lineas += ["## Pendientes de analizar", "", "Videos medidos cuya lectura detallada todavía no está en `analisis/`:", ""]
        lineas += [f"- [[02-empresas/{slug}/{'referencias' if f['tipo'] == 'referencia' else 'propios'}/{seguro(f['id'])}|{f['id']}]]"
                   for f in pendientes] + [""]
    salida = base / "informe.md"
    return salida if escribir_generado(salida, "\n".join(lineas) + "\n") else None
