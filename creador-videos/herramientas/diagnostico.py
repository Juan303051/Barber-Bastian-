"""./creador probar: comprueba la instalación y recorre el flujo completo con un video de prueba."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import boveda
from comun import BOVEDA, EMPRESAS, RAIZ, correr, empresas


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
                           ("yaml", "PyYAML (propiedades de las notas)")):
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


def _remotion(r: Resultado, temporal: Path) -> None:
    print("\n5. Generar un video con Remotion (la primera vez descarga un navegador de unos 100 MB y tarda)")
    import render
    guion = temporal / "guion.json"
    guion.write_text(json.dumps({"formato": "prueba", "ancho": 360, "alto": 640, "escenas": [
        {"tipo": "gancho", "duracion": 0.6, "texto": "Prueba"}, {"tipo": "cta", "duracion": 0.6, "texto": "Listo"}]}), encoding="utf-8")
    salida = temporal / "prueba-remotion.mp4"
    try:
        resultado = render.render(empresas()[0], str(guion), salida, capturar=True)
    except SystemExit as error:
        r.paso("se genera el video", False, str(error), "ejecuta ./instalar.sh")
        return
    ok = resultado.returncode == 0 and salida.exists()
    r.paso("se genera el video", ok, "" if ok else (resultado.stderr or resultado.stdout or "")[-300:].strip(),
           "revisa que node esté instalado y que haya internet la primera vez")
    if ok:
        sonda = correr(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", str(salida)])
        r.paso("el video mide 360×640 y dura ≈1.2 s", "360,640" in sonda.stdout, sonda.stdout.strip().replace("\n", " "), "")


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
        else:
            print("\n(Se omiten las pruebas 3 y 4: faltan ffmpeg o PyYAML)")
        if rapido:
            print("\n5. Remotion: omitido (--rapido)")
        elif (RAIZ / "remotion" / "node_modules").exists() and shutil.which("npx"):
            _remotion(r, temporal)
        else:
            print("\n5. Remotion: omitido porque no está instalado")
    print("\n" + ("Todo en orden." if r.fallos == 0 else f"{r.fallos} comprobaciones fallaron: arregla la primera y repite ./creador probar."))
    return 1 if r.fallos else 0
