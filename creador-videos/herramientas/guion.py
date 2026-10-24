"""Completa y revisa un guion antes de pasarlo a Remotion: los errores se dicen en claro, no como un fallo de Remotion."""
from __future__ import annotations

import json
import re
from pathlib import Path

from comun import EMPRESAS, TIPOS, correr, seguro

ESCENAS = {"gancho", "contenido", "cta", "pantalla"}
CAPAS = {"contador": ("desde", "hasta"), "insignia": ("numero",), "tarjeta": ("variante",), "mira": (),
         "texto-curvo": ("texto",), "palabra": ("texto",), "titulo": ("texto",)}
LOOKS = {"natural", "calido", "frio", "cine", "vibrante"}
VARIANTES = {"comentario", "notificacion", "estadistica", "foto"}
DISENOS = {"pleno", "antes-despues"}


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def recursos(props: dict) -> list[str]:
    """Archivos que el guion usa, como rutas relativas a empresas/ (sin repetir)."""
    rutas = [e["clip"] for e in props.get("escenas", []) if e.get("clip")]
    if props.get("base"):
        rutas.append(props["base"]["clip"])
    rutas += [c["imagen"] for c in props.get("capas", []) if c.get("imagen")]
    rutas += [props[k] for k in ("voz",) if props.get(k)]
    if props.get("musica"):
        rutas.append(props["musica"]["archivo"])
    if props.get("marca", {}).get("logo"):
        rutas.append(props["marca"]["logo"])
    return list(dict.fromkeys(r for r in rutas if not r.startswith(("http://", "https://"))))


def completar(props: dict) -> None:
    """Rellena lo que se puede calcular: las palabras con tiempo del análisis y la duración de la toma base."""
    desde = (props.get("base") or {}).get("desde", 0)
    origen = props.pop("palabras_de", None)
    if origen and "palabras" not in props:
        archivo = EMPRESAS / origen
        if not archivo.is_file():
            raise SystemExit(f"No encuentro {origen} (ruta relativa a empresas/): ejecuta ./creador analizar primero.")
        palabras = (json.loads(archivo.read_text(encoding="utf-8")).get("voz") or {}).get("palabras")
        if not palabras:
            raise SystemExit(f"{origen} no tiene palabras con tiempo: ejecuta ./creador analizar sin --sin-voz.")
        props["palabras"] = [[max(0, round(i - desde, 2)), round(f - desde, 2), p] for i, f, p in palabras if f > desde]
    if "duracion" not in props and props.get("base"):
        archivo = EMPRESAS / props["base"]["clip"]
        if archivo.is_file():
            sonda = correr(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(archivo)])
            try:
                props["duracion"] = round(float(sonda.stdout.strip()) - desde, 2)
            except ValueError:
                pass


def revisar(props: dict) -> list[str]:
    """Lista de problemas del guion; vacía si está bien."""
    errores: list[str] = []
    escenas = props.get("escenas", [])
    if not escenas and not _numero(props.get("duracion")):
        errores.append("falta 'escenas' o 'duracion' (y con una toma 'base', la duración se calcula sola)")
    if props.get("diseno") not in (None, *DISENOS):
        errores.append(f"'diseno' debe ser uno de: {', '.join(sorted(DISENOS))}")
    base = props.get("base")
    if base is not None and not (isinstance(base, dict) and isinstance(base.get("clip"), str)):
        errores.append("'base' debe tener un 'clip'")

    for i, e in enumerate(escenas, 1):
        donde = f"escena {i}"
        if e.get("tipo") not in ESCENAS:
            errores.append(f"{donde}: 'tipo' debe ser uno de: {', '.join(sorted(ESCENAS))}")
        if not _numero(e.get("duracion")) or e["duracion"] <= 0:
            errores.append(f"{donde}: 'duracion' debe ser un número de segundos mayor que 0")
        if e.get("ini") is not None and (not _numero(e["ini"]) or e["ini"] < 0):
            errores.append(f"{donde}: 'ini' debe ser un segundo mayor o igual que 0")
        for f in e.get("focos", []):
            faltan = [k for k in ("x", "y", "ancho", "alto", "ini", "fin") if not _numero(f.get(k))]
            if faltan:
                errores.append(f"{donde}: un foco no tiene {', '.join(faltan)}")
        if e.get("zoom") is not None and not all(_numero(e["zoom"].get(k)) for k in ("escala", "x", "y")):
            errores.append(f"{donde}: 'zoom' necesita escala, x e y")

    total = props.get("duracion") if _numero(props.get("duracion")) else max(
        [sum(e["duracion"] for e in escenas if _numero(e.get("duracion")) and e.get("ini") is None)]
        + [e["ini"] + e["duracion"] for e in escenas if _numero(e.get("ini")) and _numero(e.get("duracion"))])
    for i, c in enumerate(props.get("capas", []), 1):
        donde = f"capa {i} ({c.get('tipo')})"
        if c.get("tipo") not in CAPAS:
            errores.append(f"capa {i}: 'tipo' debe ser uno de: {', '.join(sorted(CAPAS))}")
            continue
        if not (_numero(c.get("ini")) and _numero(c.get("fin")) and c["ini"] < c["fin"]):
            errores.append(f"{donde}: necesita 'ini' y 'fin' en segundos, con ini menor que fin")
        elif total and c["ini"] >= total:
            errores.append(f"{donde}: empieza en {c['ini']} s pero el video dura {total} s")
        errores += [f"{donde}: falta '{k}'" for k in CAPAS[c["tipo"]] if c.get(k) is None]
        if c["tipo"] == "tarjeta" and c.get("variante") not in VARIANTES:
            errores.append(f"{donde}: 'variante' debe ser una de: {', '.join(sorted(VARIANTES))}")

    for i, z in enumerate(props.get("zooms", []), 1):
        if not (_numero(z.get("ini")) and _numero(z.get("fin")) and z["ini"] < z["fin"] and _numero(z.get("escala")) and z["escala"] > 0):
            errores.append(f"zoom {i}: necesita ini < fin y una escala mayor que 0")
    for i, s in enumerate(props.get("subtitulos", []), 1):
        if not (_numero(s.get("ini")) and _numero(s.get("fin")) and s["ini"] < s["fin"] and isinstance(s.get("texto"), str)):
            errores.append(f"subtítulo {i}: necesita ini < fin y texto")
    acabado = props.get("acabado")
    if acabado is not None and not (isinstance(acabado, dict) and acabado.get("look") in LOOKS):
        errores.append(f"'acabado' necesita un 'look' de: {', '.join(sorted(LOOKS))}")
    pulso = props.get("pulso")
    if pulso is not None and not (isinstance(pulso, dict) and isinstance(pulso.get("tiempos"), list) and all(_numero(x) for x in pulso["tiempos"])):
        errores.append("'pulso' necesita 'tiempos': una lista de segundos")
    palabras = props.get("palabras", [])
    malas = [i for i, p in enumerate(palabras, 1) if not (isinstance(p, list) and len(p) == 3 and _numero(p[0]) and _numero(p[1]) and isinstance(p[2], str))]
    if malas:
        errores.append(f"'palabras': el elemento {malas[0]} no es [inicio, fin, palabra]")
    return errores


def borrador(nombre: str, clip: str, analisis: str, diseno: str, palabras: list) -> dict:
    """Guion de partida para un video en bruto: subtítulos palabra por palabra y un acercamiento en una de cada dos frases."""
    zooms, inicio, frase = [], None, 0
    for i, (ini, fin, texto) in enumerate(palabras):
        inicio = ini if inicio is None else inicio
        if re.search(r"[.?!]$", texto.strip()) or i == len(palabras) - 1:
            if frase % 2 == 1 and fin - inicio >= 1.0:
                zooms.append({"ini": round(inicio, 2), "fin": round(fin, 2), "escala": 1.22, "x": 50, "y": 38})
            frase, inicio = frase + 1, None
    return {"formato": nombre, "diseno": diseno, "base": {"clip": clip}, "palabras_de": analisis,
            "estiloPalabras": {"maxPalabras": 3, "claves": [], "serif": [], "posicion": "centro"},
            "correcciones": {}, "zooms": zooms, "capas": []}


def crear(carpeta: Path, video: str, diseno: str, nombre: str | None, forzar: bool) -> Path:
    """Escribe empresas/<empresa>/formatos/<nombre>.json a partir de un video ya analizado."""
    ruta = next((carpeta / "videos" / t / video for t in TIPOS if (carpeta / "videos" / t / video).is_file()), None)
    if ruta is None:
        raise SystemExit(f"No encuentro {video} en {carpeta.name}/videos/propios ni en videos/referencias.")
    analisis = carpeta / "analisis" / f"{ruta.stem}.analisis.json"
    if not analisis.is_file():
        raise SystemExit(f"Falta analizar el video: ejecuta ./creador analizar --empresa {carpeta.name}")
    palabras = (json.loads(analisis.read_text(encoding="utf-8")).get("voz") or {}).get("palabras")
    if not palabras:
        raise SystemExit("El video no tiene transcripción: ejecuta ./creador analizar --forzar --empresa " + carpeta.name + " (sin --sin-voz)")
    nombre = seguro(nombre or ruta.stem)
    destino = carpeta / "formatos" / f"{nombre}.json"
    if destino.exists() and not forzar:
        raise SystemExit(f"{destino.name} ya existe y puede tener tus cambios: usa --nombre otro o --forzar para reemplazarlo.")
    datos = borrador(nombre, f"{carpeta.name}/{ruta.relative_to(carpeta)}".replace("\\", "/"),
                     f"{carpeta.name}/analisis/{analisis.name}", diseno, palabras)
    texto = json.dumps(datos, ensure_ascii=False, indent=2)
    texto = re.sub(r"\[\s+([^\[\]{}]*?)\s+\]", lambda m: "[" + re.sub(r"\s+", " ", m.group(1)) + "]", texto)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(texto + "\n", encoding="utf-8")
    return destino
