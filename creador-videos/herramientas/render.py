"""Convierte un guion JSON en video con Remotion (render) o lo abre para previsualizar (estudio)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from comun import EMPRESAS, RAIZ, nombre

REMOTION = RAIZ / "remotion"
CACHE = REMOTION / ".cache"


def _guion(carpeta: Path, indicado: str) -> Path:
    directo = Path(indicado)
    if directo.is_file():
        return directo
    dentro = carpeta / "formatos" / (indicado if indicado.endswith(".json") else indicado + ".json")
    if dentro.is_file():
        return dentro
    disponibles = sorted(p.stem for p in (carpeta / "formatos").glob("*.json")) if (carpeta / "formatos").exists() else []
    raise SystemExit(f"No encuentro el guion '{indicado}'. En {carpeta.name}/formatos hay: {', '.join(disponibles) or 'ninguno'}")


def _recursos(props: dict) -> list[str]:
    rutas = [e["clip"] for e in props["escenas"] if e.get("clip")]
    rutas += [props[k] for k in ("voz",) if props.get(k)]
    if props.get("musica"):
        rutas.append(props["musica"]["archivo"])
    if props["marca"].get("logo"):
        rutas.append(props["marca"]["logo"])
    # Un mismo clip puede aparecer en varias escenas: se enlaza una sola vez.
    return list(dict.fromkeys(r for r in rutas if not r.startswith(("http://", "https://"))))


def preparar(carpeta: Path, indicado: str) -> tuple[Path, Path, Path]:
    """Devuelve (props.json, carpeta pública, guion). Solo incluye los archivos que el guion usa."""
    guion = _guion(carpeta, indicado)
    props = json.loads(guion.read_text(encoding="utf-8"))
    ficha = carpeta / "marca.json"
    props["marca"] = {"nombre": nombre(carpeta)} | (json.loads(ficha.read_text(encoding="utf-8")) if ficha.exists() else {}) | props.get("marca", {})
    if not ficha.exists():
        print(f"  (sin {ficha.relative_to(RAIZ)}: uso colores y fuente por defecto)")

    publica = CACHE / "publico"
    shutil.rmtree(publica, ignore_errors=True)
    faltan = []
    for ruta in _recursos(props):
        origen = EMPRESAS / ruta
        if not origen.is_file():
            faltan.append(ruta)
            continue
        destino = publica / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        try:  # Remotion no sirve enlaces simbólicos (404); un enlace duro no ocupa espacio extra
            os.link(origen, destino)
        except OSError:
            shutil.copy2(origen, destino)
    if faltan:
        raise SystemExit("Faltan archivos (rutas relativas a empresas/):\n  " + "\n  ".join(faltan))
    publica.mkdir(parents=True, exist_ok=True)

    archivo = CACHE / "props.json"
    archivo.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    return archivo, publica, guion


def _remotion(args: list[str]) -> int:
    if not (REMOTION / "node_modules").exists():
        raise SystemExit("Falta instalar Remotion: ejecuta ./instalar.sh (o 'npm install' dentro de remotion/).")
    navegador = os.environ.get("CREADOR_NAVEGADOR")  # opcional: usar un Chrome/Chromium ya instalado
    extra = [f"--browser-executable={navegador}"] if navegador else []
    return subprocess.run(["npx", "remotion", *args, *extra], cwd=REMOTION).returncode


def render(carpeta: Path, indicado: str) -> int:
    props, publica, guion = preparar(carpeta, indicado)
    formato = json.loads(props.read_text(encoding="utf-8")).get("formato") or guion.stem
    salida = carpeta / "salidas" / f"{formato}.mp4"
    salida.parent.mkdir(exist_ok=True)
    codigo = _remotion(["render", "src/index.ts", "Formato", str(salida),
                        f"--props={props}", f"--public-dir={publica}"])
    if codigo == 0:
        print(f"\n  video: {salida.relative_to(RAIZ)}")
    return codigo


def estudio(carpeta: Path, indicado: str) -> int:
    props, publica, _ = preparar(carpeta, indicado)
    return _remotion(["studio", "src/index.ts", f"--props={props}", f"--public-dir={publica}"])
