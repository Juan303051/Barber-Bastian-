"""Descarga los videos listados en referencias.txt y propios.txt y guarda sus métricas públicas."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from comun import TIPOS, carpeta_analisis, nombre, urls


def _extractor_args(texto: str | None) -> dict:
    """'youtube:player_client=tv,android_vr' -> {'youtube': {'player_client': ['tv', 'android_vr']}}"""
    if not texto:
        return {}
    extractor, _, resto = texto.partition(":")
    clave, _, valores = resto.partition("=")
    return {extractor: {clave: valores.split(",")}}


def _meta(info: dict, tipo: str) -> dict:
    descripcion = info.get("description") or ""
    fecha = info.get("upload_date")
    return {
        "id": f"{info['extractor_key'].lower()}-{info['id']}",
        "tipo": TIPOS[tipo],
        "url": info.get("webpage_url"),
        "plataforma": info["extractor_key"],
        "titulo": info.get("title"),
        "descripcion": descripcion[:500],
        "autor": info.get("uploader") or info.get("channel"),
        "duracion": info.get("duration"),
        "fecha_subida": f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}" if fecha else None,
        "vistas": info.get("view_count"),
        "likes": info.get("like_count"),
        "comentarios": info.get("comment_count"),
        "compartidos": info.get("repost_count"),
        "hashtags": info.get("tags") or re.findall(r"#\w+", descripcion),
        "musica": info.get("track") or None,
        "fecha_consulta": date.today().isoformat(),
    }


def descargar(carpeta: Path, solo_metadatos: bool, cookies_navegador: str | None,
              extractor_args: str | None, maximo: int) -> int:
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError

    fallos = 0
    analisis = carpeta_analisis(carpeta)
    for tipo in TIPOS:
        lista = urls(carpeta, tipo)
        if not lista:
            continue
        destino = carpeta / "videos" / tipo
        destino.mkdir(parents=True, exist_ok=True)
        opciones = {
            "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
            "merge_output_format": "mp4",
            "outtmpl": str(destino / "%(extractor_key)s-%(id)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "playlistend": maximo,
            "extractor_args": _extractor_args(extractor_args),
        }
        if cookies_navegador:
            opciones["cookiesfrombrowser"] = (cookies_navegador,)
        with YoutubeDL(opciones) as ydl:
            for url in lista:
                try:
                    info = ydl.extract_info(url, download=not solo_metadatos)
                except DownloadError as error:
                    fallos += 1
                    print(f"  ✗ {url}\n    {str(error).splitlines()[-1][:200]}")
                    continue
                for item in info.get("entries") or [info]:
                    if not item:
                        continue
                    meta = _meta(item, tipo)
                    (analisis / f"{meta['id']}.meta.json").write_text(
                        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                    vistas = meta["vistas"] if meta["vistas"] is not None else "?"
                    print(f"  ✓ {meta['id']}  {vistas} vistas  — {(meta['titulo'] or '')[:60]}")
    if fallos:
        print(f"\n{nombre(carpeta)}: {fallos} fallaron. Si pide iniciar sesión, repite con "
              "--cookies-navegador safari (o chrome); si el video es privado, ponlo a mano en videos/.")
    return fallos
