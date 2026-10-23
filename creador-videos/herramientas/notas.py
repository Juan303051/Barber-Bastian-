"""Genera en la bóveda una nota por video y el informe de cada empresa."""
from __future__ import annotations

from pathlib import Path

from boveda import escribir_generado, frontmatter
from comun import TIPOS, boveda_empresa, seguro
from informe import cargar, indicadores, informe


def _mmss(segundos: float) -> str:
    return f"{int(segundos // 60)}:{int(segundos % 60):02d}"


def _nota(fila: dict, slug: str, base: Path) -> str:
    meta, ritmo, audio, voz = fila["meta"], fila["ritmo"], fila["audio"] or {}, fila["voz"] or {}
    i = indicadores(fila)
    nota_id = seguro(fila["id"])
    imagenes = fila["imagenes"]
    medios = f"../medios/{nota_id}"
    titulo = meta.get("titulo") or fila["id"]
    propiedades = {
        "tipo": fila["tipo"], "empresa": slug, "id": fila["id"], "generado": True,
        "plataforma": meta.get("plataforma"), "autor": meta.get("autor"), "url": meta.get("url"),
        "fecha_subida": meta.get("fecha_subida"), "fecha_consulta": meta.get("fecha_consulta"),
        "duracion": round(fila["duracion"], 1), "vertical": fila["vertical"],
        "vistas": meta.get("vistas"), "likes": meta.get("likes"), "comentarios": meta.get("comentarios"),
        "etiquetas": [fila["tipo"], slug],
    }
    texto = [frontmatter(propiedades), f"# {titulo}", "",
             f"> Nota generada por `./creador informe`; se reescribe sola, no la edites. "
             + (f"Lectura detallada: [[02-empresas/{slug}/analisis/{nota_id}]]."
                if (base / "analisis" / f"{nota_id}.md").exists()
                else f"Falta la lectura detallada: crea `analisis/{nota_id}.md` con la plantilla de análisis."), ""]
    if meta.get("url"):
        texto += [f"Fuente: <{meta['url']}>" + (f" · Autor: {meta['autor']}" if meta.get("autor") else ""), ""]
    elif meta.get("autor"):
        texto += [f"Autor: {meta['autor']}", ""]
    if meta.get("origen"):
        texto += [f"Origen: {meta['origen']}", ""]

    texto += ["## Métricas", "", "| Duración | Formato | Vistas | Vistas/día | % likes | % comentarios |", "|---|---|---|---|---|---|",
              f"| {round(fila['duracion'], 1)} s | {fila['ancho']}×{fila['alto']} a {fila['fps']} fps | "
              f"{i['vistas'] if i['vistas'] is not None else '—'} | {round(i['vistas_dia']) if i['vistas_dia'] else '—'} | "
              f"{i['likes_pct'] if i['likes_pct'] is not None else '—'} | {i['comentarios_pct'] if i['comentarios_pct'] is not None else '—'} |", ""]

    texto += ["## Ritmo", "", "| Planos | Plano mediano | Cortes por 10 s | Primer corte | Cortes en los 3 primeros s |", "|---|---|---|---|---|",
              f"| {ritmo['n_cortes'] + 1} | {ritmo['plano_mediano']} s | {ritmo['cortes_por_10s']} | "
              f"{ritmo['primer_corte'] if ritmo['primer_corte'] is not None else '—'} | {ritmo['cortes_en_gancho']} |", "",
              f"Cortes cada 5 s: {' · '.join(str(n) for n in ritmo['curva_5s'])}", "",
              "_Los cortes se miden sobre el cuadro completo: en videos con varias capas, pantalla dividida o una sola toma continua "
              "con gráficos encima, el cambio real está en las capas y no sale en esta cifra._", ""]

    if audio or voz:
        texto += ["## Audio y voz", "", "| Volumen (LUFS) | Rango (LU) | Pico (dBFS) | Silencio | Palabras/min | Idioma |", "|---|---|---|---|---|---|",
                  f"| {audio.get('lufs', '—')} | {audio.get('rango_lu', '—')} | {audio.get('pico_db', '—')} | "
                  f"{audio.get('silencio_pct', '—')} % | {voz.get('palabras_por_min', '—')} | {voz.get('idioma', '—')} |", ""]

    texto += ["## Gancho (0–3 s)", ""]
    if voz.get("gancho_texto"):
        texto += [f"Dicho: «{voz['gancho_texto']}»", ""]
    if imagenes.get("gancho"):
        texto += [f"![]({medios}/{imagenes['gancho']})", ""]

    if imagenes.get("planos"):
        texto += ["## Desglose por plano", "", "| # | Inicio | Fin | Duración | Fotograma |", "|---|---|---|---|---|"]
        texto += [f"| {p['n']} | {p['ini']} s | {p['fin']} s | {round(p['fin'] - p['ini'], 2)} s | ![\\|110]({medios}/{p['imagen']}) |"
                  for p in imagenes["planos"]]
        texto += [""]
    if imagenes.get("hoja"):
        texto += ["## Hoja de contacto", "", f"![]({medios}/{imagenes['hoja']})", ""]

    if voz.get("segmentos"):
        texto += ["## Transcripción", "", "_Automática (Whisper): puede equivocarse en nombres, cifras y palabras raras._", ""]
        texto += [f"- [{_mmss(s['ini'])}] {s['texto']}" for s in voz["segmentos"]]
        texto += [""]
    return "\n".join(texto)


def generar(carpeta: Path) -> int:
    """Escribe las notas de cada video y el informe. Devuelve cuántas notas escribió."""
    slug = carpeta.name
    base = boveda_empresa(carpeta)
    escritas = 0
    for fila in cargar(carpeta):
        destino = base / ("referencias" if fila["tipo"] == "referencia" else "propios")
        escritas += escribir_generado(destino / f"{seguro(fila['id'])}.md", _nota(fila, slug, base))
    informe(carpeta)
    return escritas
