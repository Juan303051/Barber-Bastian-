"""Escritura segura y validación de la bóveda de Obsidian."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

import yaml

from comun import BOVEDA, EMPRESAS, escribir_atomico

VIDEOS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
TIPOS_NOTA = {"leeme", "ficha", "referencia", "propio", "analisis", "formato", "idea",
              "investigacion", "conocimiento", "informe", "bandeja"}
MAX_BYTES = 5 * 1024 * 1024
NOMBRE_SEGURO = re.compile(r"^[A-Za-z0-9._-]+$")
BLOQUES_CODIGO = re.compile(r"```.*?```|`[^`\n]*`", re.S)
ENLACE_WIKI = re.compile(r"\[\[([^\]|#]*)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
ENLACE_MD = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CABECERA = re.compile(r"---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.S)


def frontmatter(campos: dict) -> str:
    """Propiedades de Obsidian. JSON es YAML válido, así que nunca se rompe con comillas o acentos."""
    lineas = ["---"] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in campos.items()] + ["---", ""]
    return "\n".join(lineas)


def leer_frontmatter(texto: str) -> dict | None:
    """None si la nota no tiene propiedades; {'__error__': ...} si están mal escritas."""
    m = CABECERA.match(texto)
    if not m:
        return None
    try:
        datos = yaml.safe_load(m.group(1))
    except yaml.YAMLError as error:
        return {"__error__": str(error).splitlines()[0]}
    return datos if isinstance(datos, dict) else {}


def escribir_generado(ruta: Path, texto: str) -> bool:
    """Reescribe solo notas marcadas `generado: true`; jamás pisa lo escrito a mano."""
    if ruta.exists():
        actual = leer_frontmatter(ruta.read_text(encoding="utf-8")) or {}
        if actual.get("generado") is not True:
            print(f"  ⚠ {ruta.relative_to(BOVEDA)} existe y no es generada: no la toco")
            return False
    escribir_atomico(ruta, texto)
    return True


def _indice(archivos: list[Path]) -> dict[str, list[Path]]:
    indice: dict[str, list[Path]] = {}
    for ruta in archivos:
        clave = ruta.stem if ruta.suffix == ".md" else ruta.name
        indice.setdefault(clave.lower(), []).append(ruta)
    return indice


def _destino_wiki(destino: str, indice: dict[str, list[Path]]) -> list[Path]:
    destino = destino.strip()
    if "/" in destino:
        base = BOVEDA / destino
        return [p for p in (base, Path(str(base) + ".md")) if p.is_file()]
    if destino.lower().endswith(".md"):
        destino = destino[:-3]
    return indice.get(destino.lower(), [])


def _destino_md(url: str, nota: Path) -> bool:
    url = unquote(url.split("#", 1)[0])
    if not url:
        return True
    base = (nota.parent / url).resolve()
    return base.is_file() or Path(str(base) + ".md").is_file()


def validar() -> int:
    """Revisa la bóveda entera. Devuelve el número de errores (los avisos no cuentan)."""
    if not BOVEDA.is_dir():
        raise SystemExit(f"No existe la bóveda: {BOVEDA}")
    errores: list[str] = []
    avisos: list[str] = []
    faltan_medios: set[str] = set()
    archivos = [p for p in BOVEDA.rglob("*")
                if p.is_file() and ".obsidian" not in p.parts and not p.name.endswith(".tmp")]
    indice = _indice(archivos)

    def rel(ruta: Path) -> str:
        return str(ruta.relative_to(BOVEDA))

    for ruta in archivos:
        if ruta.suffix.lower() in VIDEOS:
            errores.append(f"{rel(ruta)}: un video no puede estar en la bóveda (va en empresas/<empresa>/videos/)")
        elif ruta.stat().st_size > MAX_BYTES:
            errores.append(f"{rel(ruta)}: pesa más de 5 MB")
        if not NOMBRE_SEGURO.match(ruta.name):
            avisos.append(f"{rel(ruta)}: el nombre tiene espacios, acentos o símbolos; usa letras, números, - y _")

    for ruta in (p for p in archivos if p.suffix == ".md" and "03-plantillas" not in p.parts):
        texto = ruta.read_text(encoding="utf-8")
        props = leer_frontmatter(texto)
        legible = True
        if props is None:
            errores.append(f"{rel(ruta)}: la nota no tiene propiedades (--- tipo: ... ---)")
            props, legible = {}, False
        elif "__error__" in props:
            errores.append(f"{rel(ruta)}: propiedades mal escritas ({props['__error__']})")
            props, legible = {}, False
        tipo = props.get("tipo")
        if legible and not tipo:
            errores.append(f"{rel(ruta)}: falta la propiedad 'tipo'")
        elif tipo and tipo not in TIPOS_NOTA:
            avisos.append(f"{rel(ruta)}: tipo '{tipo}' desconocido (usa: {', '.join(sorted(TIPOS_NOTA))})")

        partes = ruta.relative_to(BOVEDA).parts
        if len(partes) >= 3 and partes[0] == "02-empresas" and legible and props.get("empresa") != partes[1]:
            errores.append(f"{rel(ruta)}: 'empresa' es {props.get('empresa')!r} pero está en la carpeta de '{partes[1]}'")
        if tipo == "investigacion" and not props.get("fuentes") and props.get("estado") != "borrador":
            errores.append(f"{rel(ruta)}: una investigación necesita 'fuentes' (o estado: borrador)")
        guion = props.get("guion")
        if tipo == "formato" and guion and not (EMPRESAS.parent / guion).is_file():
            avisos.append(f"{rel(ruta)}: el guion '{guion}' todavía no existe")

        limpio = BLOQUES_CODIGO.sub("", texto)
        for destino in ENLACE_WIKI.findall(limpio):
            destino = destino.rstrip("\\")  # en tablas el alias va tras "\|"
            if not destino.strip() or "{{" in destino:
                continue
            encontrados = _destino_wiki(destino, indice)
            if not encontrados:
                errores.append(f"{rel(ruta)}: enlace roto [[{destino}]]")
            elif len(encontrados) > 1 and "/" not in destino:
                avisos.append(f"{rel(ruta)}: [[{destino}]] es ambiguo ({len(encontrados)} notas); usa la ruta completa")
        for url in ENLACE_MD.findall(limpio):
            if re.match(r"(https?:|mailto:|#|obsidian:)", url) or "{{" in url:
                continue
            if not _destino_md(url, ruta):
                if "/medios/" in url:  # los fotogramas no viajan por git: se regeneran con ./creador analizar
                    faltan_medios.add(rel(ruta))
                else:
                    errores.append(f"{rel(ruta)}: enlace o imagen rota ({url})")

    if faltan_medios:
        avisos.append(f"{len(faltan_medios)} notas apuntan a fotogramas que no están en esta copia de la bóveda; "
                      "se regeneran con ./creador analizar (necesita los videos)")
    base = BOVEDA / "02-empresas"
    en_boveda = {p.name for p in base.iterdir() if p.is_dir()} if base.is_dir() else set()
    con_datos = {p.name for p in EMPRESAS.iterdir() if p.is_dir()}
    for slug in sorted(en_boveda - con_datos):
        avisos.append(f"02-empresas/{slug}: no tiene carpeta de datos en empresas/")
    for slug in sorted(con_datos - en_boveda):
        avisos.append(f"empresas/{slug}: no tiene carpeta en la bóveda (02-empresas/)")

    pendientes = []
    for ruta in sorted(base.glob("*/referencias/*.md")) + sorted(base.glob("*/propios/*.md")):
        if not (ruta.parents[1] / "analisis" / ruta.name).exists():
            pendientes.append(f"{ruta.parents[1].name}/{ruta.stem}")

    for titulo, lista in (("ERRORES", errores), ("AVISOS", avisos)):
        if lista:
            print(f"\n{titulo} ({len(lista)})")
            for linea in lista:
                print(f"  - {linea}")
    if pendientes:
        print(f"\nPENDIENTES DE ANALIZAR ({len(pendientes)}): {', '.join(pendientes)}")
    print(f"\nBóveda: {len(archivos)} archivos, {len(errores)} errores, {len(avisos)} avisos")
    return len(errores)
