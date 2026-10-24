"""./creador probar: comprueba la instalación y recorre el flujo completo con un video de prueba."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import boveda
from comun import BOVEDA, EMPRESAS, RAIZ, correr, empresas


def _cola(texto: str, largo: int = 300) -> str:
    """Final de un mensaje de error, sin el ruido de memoria de Docker que Remotion imprime."""
    util = [l for l in texto.splitlines() if not any(k in l for k in ("Detected differing", "Memory reported", "inadvertently", "Using the lower"))]
    return "\n".join(util)[-largo:].strip()


class Resultado:
    def __init__(self) -> None:
        self.fallos = 0

    def paso(self, titulo: str, ok: bool, detalle: str = "", arreglo: str = "") -> bool:
        print(f"  {'✓' if ok else '✗'} {titulo}" + (f" — {detalle}" if detalle else ""))
        if not ok:
            self.fallos += 1
            if arreglo:
                print(f"      Cómo arreglarlo: {arreglo}")
        return ok


def _entorno(r: Resultado) -> None:
    print("\n1. Programas necesarios")
    r.paso("Python 3.10 o superior", sys.version_info >= (3, 10), sys.version.split()[0],
           "ejecuta ./instalar.sh: instala un Python moderno y lo usa solo")
    for programa in ("ffmpeg", "ffprobe"):
        r.paso(programa, shutil.which(programa) is not None, shutil.which(programa) or "",
               "brew install ffmpeg")
    for modulo, nombre in (("yt_dlp", "yt-dlp (descargas)"), ("faster_whisper", "faster-whisper (voz a texto)"),
                           ("yaml", "PyYAML (propiedades de las notas)"),
                           ("fastapi", "FastAPI (la app Iris)"), ("uvicorn", "Uvicorn (servidor de la app Iris)")):
        r.paso(nombre, importlib.util.find_spec(modulo) is not None, "", "ejecuta ./instalar.sh")
    for programa in ("node", "npx"):
        r.paso(f"{programa} (Remotion)", shutil.which(programa) is not None, shutil.which(programa) or "",
               "brew install node")
    r.paso("Remotion instalado", (RAIZ / "remotion" / "node_modules" / ".bin" / "remotion").exists(), "",
           "cd remotion && npm install")
    cache = Path.home() / ".cache" / "huggingface" / "hub"
    modelos = sorted(p.name.split("faster-whisper-")[-1] for p in cache.glob("models--*faster-whisper-*")) if cache.exists() else []
    print(f"  · Modelos de voz descargados: {', '.join(modelos) if modelos else 'ninguno (la primera transcripción descargará el modelo, unos 150–460 MB)'}")


def _escritura(r: Resultado) -> None:
    print("\n2. Permisos y carpetas")
    for etiqueta, carpeta in (("empresas/", EMPRESAS), ("boveda/", BOVEDA)):
        try:
            with tempfile.NamedTemporaryFile(dir=carpeta, prefix=".prueba-"):
                pass
            r.paso(f"se puede escribir en {etiqueta}", True)
        except OSError as error:
            r.paso(f"se puede escribir en {etiqueta}", False, str(error), "revisa los permisos de la carpeta")
    faltan = [f"{c.name}/{s}" for c in empresas() for s in ("videos/referencias", "videos/propios", "analisis")
              if not (c / s).is_dir()]
    r.paso("carpetas de cada empresa", not faltan, ", ".join(faltan[:3]), "ejecuta ./creador preparar")


def _video_de_prueba(destino: Path) -> Path:
    ruta = destino / "prueba.mp4"
    correr(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=red:s=360x640:d=2:r=30", "-f", "lavfi", "-i", "color=c=blue:s=360x640:d=2:r=30",
            "-f", "lavfi", "-i", "color=c=yellow:s=360x640:d=2:r=30", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
            "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0[v]", "-map", "[v]", "-map", "3:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(ruta)])
    return ruta


def _analisis(r: Resultado, temporal: Path) -> None:
    print("\n3. Análisis de un video de prueba (3 tomas de 2 segundos)")
    import analizar
    import notas
    video = _video_de_prueba(temporal)
    if not r.paso("se crea el video de prueba", video.exists(), "", "revisa que ffmpeg funcione"):
        return
    fila = analizar.medir_video(video, "referencia", "videos/referencias/prueba.mp4", 0.3, False, "base", temporal / "medios")
    if not r.paso("se lee el video", fila is not None):
        return
    r.paso("detecta los 2 cortes", fila["ritmo"]["n_cortes"] == 2, f"detectó {fila['ritmo']['n_cortes']}", "")
    r.paso("mide el volumen", bool(fila["audio"]) and fila["audio"]["lufs"] is not None, "", "")
    medios = temporal / "medios"
    esperadas = ["gancho.jpg", "hoja.jpg"] + [f"plano-{n:02d}.jpg" for n in (1, 2, 3)]
    r.paso("genera los fotogramas", all((medios / e).exists() for e in esperadas), "", "revisa que ffmpeg funcione")
    fila["meta"] = {}
    texto = notas._nota(fila, "empresa-de-prueba", temporal)
    props = boveda.leer_frontmatter(texto) or {}
    r.paso("escribe la nota de la bóveda", props.get("tipo") == "referencia" and props.get("generado") is True)


def _validador(r: Resultado, temporal: Path) -> None:
    print("\n4. Validador de la bóveda")
    sana = temporal / "boveda-sana"
    rota = temporal / "boveda-rota"
    for base, cuerpo in ((sana, "# Nota\nEnlace a [[02-empresas/prueba/00-ficha]]\n"),
                         (rota, "# Nota\nEnlace roto [[02-empresas/prueba/no-existe]]\n")):
        carpeta = base / "02-empresas" / "prueba"
        carpeta.mkdir(parents=True)
        (carpeta / "00-ficha.md").write_text('---\ntipo: "ficha"\nempresa: "prueba"\n---\n# Ficha\n', encoding="utf-8")
        (carpeta / "nota.md").write_text('---\ntipo: "idea"\nempresa: "prueba"\n---\n' + cuerpo, encoding="utf-8")
    (rota / "02-empresas" / "prueba" / "mezclada.md").write_text('---\ntipo: "idea"\nempresa: "otra"\n---\n# X\n', encoding="utf-8")
    originales = boveda.BOVEDA, boveda.EMPRESAS
    (temporal / "datos").mkdir()
    try:
        boveda.EMPRESAS = temporal / "datos"
        resultados = {}
        for nombre, base in (("sana", sana), ("rota", rota)):
            boveda.BOVEDA = base
            with contextlib.redirect_stdout(io.StringIO()):
                resultados[nombre] = boveda.validar()
    finally:
        boveda.BOVEDA, boveda.EMPRESAS = originales
    r.paso("acepta una bóveda sana", resultados["sana"] == 0)
    r.paso("detecta un enlace roto y una nota de otra empresa", resultados["rota"] == 2, f"errores: {resultados['rota']}")
    with contextlib.redirect_stdout(io.StringIO()) as salida:
        errores = boveda.validar()
    r.paso("tu bóveda real no tiene errores", errores == 0, "" if errores == 0 else "ejecuta ./creador validar para ver cuáles",
           "ejecuta ./creador validar y corrige lo que indique")
    del salida


def _guiones(r: Resultado) -> None:
    print("\n5. Guiones y piezas de estilo")
    import guion
    bueno = {"escenas": [{"tipo": "gancho", "duracion": 2}],
             "capas": [{"tipo": "contador", "ini": 0, "fin": 1, "desde": 0, "hasta": 5}], "palabras": [[0, 1, "hola"]]}
    malo = {"escenas": [{"tipo": "inventado", "duracion": 0}], "capas": [{"tipo": "tarjeta", "ini": 2, "fin": 1}]}
    r.paso("acepta un guion correcto", guion.revisar(bueno) == [])
    r.paso("detecta los errores de un guion malo", len(guion.revisar(malo)) >= 4, f"{len(guion.revisar(malo))} problemas")
    pares = [[0.0, 0.4, "uno."], [0.4, 0.9, "dos"], [0.9, 1.5, "tres."], [1.5, 2.2, "cuatro"], [2.2, 3.0, "cinco."]]
    prueba = guion.borrador("x", "e/v.mp4", "e/a.json", "antes-despues", pares)
    r.paso("crea el guion borrador de un video analizado", guion.revisar({**prueba, "duracion": 3}) == [] and len(prueba["zooms"]) == 1,
           f"{len(prueba['zooms'])} acercamiento(s)")
    if shutil.which("npm") and (RAIZ / "remotion" / "node_modules").exists():
        resultado = subprocess.run(["npm", "run", "-s", "probar"], cwd=RAIZ / "remotion", capture_output=True, text=True)
        r.paso("pruebas de la lógica de subtítulos y contadores", resultado.returncode == 0,
               "" if resultado.returncode == 0 else _cola(resultado.stderr or resultado.stdout),
               "si el mensaje habla de --experimental-strip-types: brew upgrade node; si dice ERR_ASSERTION es un fallo del programa: mándame este mensaje")


def _remotion(r: Resultado, temporal: Path) -> None:
    print("\n6. Generar un video con todas las piezas de estilo (la primera vez Remotion descarga un navegador de unos 100 MB y tarda)")
    import render
    guion = temporal / "guion.json"
    guion.write_text(json.dumps({
        "formato": "prueba", "ancho": 360, "alto": 640, "diseno": "antes-despues",
        "escenas": [{"tipo": "gancho", "duracion": 0.8, "texto": "Prueba"},
                    {"tipo": "cta", "duracion": 0.8, "clave": "CLAVE", "texto": "Listo"}],
        "palabras": [[0.1, 0.4, "hola"], [0.4, 0.8, "mundo"]], "estiloPalabras": {"claves": ["mundo"]},
        "capas": [{"tipo": "insignia", "ini": 0.2, "fin": 1.4, "x": 15, "y": 12, "numero": 1},
                  {"tipo": "contador", "ini": 0.2, "fin": 1.4, "y": 28, "desde": 0, "hasta": 100},
                  {"tipo": "tarjeta", "variante": "estadistica", "ini": 0.2, "fin": 1.4, "y": 60, "cifra": "1"},
                  {"tipo": "mira", "ini": 0.2, "fin": 1.4, "y": 45, "etiqueta": "Prueba"},
                  {"tipo": "texto-curvo", "ini": 0.2, "fin": 1.4, "y": 20, "texto": "Prueba"},
                  {"tipo": "palabra", "ini": 0.2, "fin": 1.4, "y": 35, "texto": "OK"}]}), encoding="utf-8")
    salida = temporal / "prueba-remotion.mp4"
    try:
        resultado = render.render(empresas()[0], str(guion), salida, capturar=True)
    except SystemExit as error:
        r.paso("se genera el video", False, str(error), "ejecuta ./instalar.sh")
        return
    ok = resultado.returncode == 0 and salida.exists()
    r.paso("se genera el video", ok, "" if ok else _cola(resultado.stderr or resultado.stdout or ""),
           "si habla de descargar un navegador: revisa internet y repite; si habla de una pieza, es un fallo del programa: mándame este mensaje")
    if ok:
        sonda = correr(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", str(salida)])
        r.paso("el video mide 360×640 y dura 1.6 s", "360,640,1.6" in sonda.stdout, sonda.stdout.strip().replace("\n", " "), "")


def _app(r: Resultado, completo: bool) -> None:
    print("\n7. App Iris: piezas, cuentas, seguridad, subida" + (" y un video completo" if completo else "") + " (todo en una carpeta temporal)")
    faltan = [m for m in ("fastapi", "uvicorn", "httpx") if importlib.util.find_spec(m) is None]
    if faltan:
        r.paso("componentes de la app", False, ", ".join(faltan), "ejecuta ./instalar.sh")
        return
    entorno = {**os.environ, "PYTHONPATH": str(RAIZ / "herramientas")}
    pruebas = (("piezas de la app (interprete, pausas, estilo, seguridad)", ["-m", "servidor.pruebas"]),
               ("la app de punta a punta", ["-m", "servidor.pruebas_api", *(["--completo"] if completo else [])]))
    for titulo, argumentos in pruebas:
        resultado = subprocess.run([sys.executable, *argumentos], cwd=RAIZ / "app", env=entorno, capture_output=True, text=True)
        malas = [l.strip() for l in resultado.stdout.splitlines() if "✗" in l] or [_cola(resultado.stderr or resultado.stdout)]
        r.paso(titulo, resultado.returncode == 0, "" if resultado.returncode == 0 else " · ".join(malas),
               "si falla algo, es un error del programa: mándame este mensaje")


def probar(rapido: bool) -> int:
    print("Autodiagnóstico de Creador de videos")
    r = Resultado()
    _entorno(r)
    _escritura(r)
    with tempfile.TemporaryDirectory(prefix="creador-prueba-") as carpeta:
        temporal = Path(carpeta)
        if shutil.which("ffmpeg") and shutil.which("ffprobe") and importlib.util.find_spec("yaml"):
            _analisis(r, temporal)
            _validador(r, temporal)
            _guiones(r)
        else:
            print("\n(Se omiten las pruebas 3 y 4: faltan ffmpeg o PyYAML)")
        if rapido:
            print("\n6. Remotion: omitido (--rapido)")
        elif (RAIZ / "remotion" / "node_modules").exists() and shutil.which("npx"):
            _remotion(r, temporal)
        else:
            print("\n6. Remotion: omitido porque no está instalado")
        _app(r, completo=not rapido and (RAIZ / "remotion" / "node_modules").exists() and shutil.which("npx") is not None)
    print("\n" + ("Todo en orden." if r.fallos == 0 else f"{r.fallos} comprobaciones fallaron: arregla la primera y repite ./creador probar."))
    return 1 if r.fallos else 0
