"""Cola de trabajo: analiza referencias y construye videos, avisando del avance paso a paso."""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import traceback
from pathlib import Path

import analizar
import comun
import descargar
import guion as revisor
import render

from . import datos, estilo, interprete, pausas

NEUTRA = "maquetas-estilo"  # carpeta de la biblioteca compartida: aquí se guarda lo que no pertenece a una marca
FPS = 30
PESOS = {"preparar": 4, "pausas": 8, "voz": 28, "guion": 3, "render": 50, "final": 7}
ETAPAS = {
    "preparar": "Preparando tu video",
    "pausas": "Quitando las pausas largas",
    "voz": "Escuchando y transcribiendo la voz",
    "guion": "Armando el guion con lo que pediste",
    "render": "Construyendo el video",
    "final": "Sumando el sonido y terminando",
}
RUIDO = ("Detected differing", "Memory reported", "inadvertently", "Using the lower")


class Cancelado(Exception):
    """La persona canceló el trabajo."""


_cola: "queue.Queue[tuple[str, str]]" = queue.Queue()
_cancelados: set[str] = set()
_procesos: dict[str, subprocess.Popen] = {}
_candado = threading.Lock()
_hilo: threading.Thread | None = None


def modelo_de_voz() -> str:
    return os.environ.get("IRIS_MODELO_VOZ") or "small"


def carpeta_de_trabajo(id_: str) -> Path:
    return datos.DATOS / "trabajos" / id_


def carpeta_de_referencia(id_: str) -> Path:
    return datos.DATOS / "referencias" / id_


def carpeta_de_marca(marca: str | None) -> Path:
    destino = comun.EMPRESAS / (marca or NEUTRA)
    return destino if destino.is_dir() else comun.EMPRESAS / NEUTRA


# ---------------------------------------------------------------------------------------------------------------------
# Cola
# ---------------------------------------------------------------------------------------------------------------------

def iniciar() -> None:
    """Arranca el hilo que trabaja y marca como interrumpido lo que quedó a medias en un cierre anterior."""
    global _hilo
    with _candado:
        if _hilo is not None and _hilo.is_alive():
            return
        datos.ejecutar("UPDATE trabajos SET estado = 'interrumpido', mensaje = 'Se cerró la app mientras trabajaba. Puedes volver a crearlo.' "
                       "WHERE estado IN ('en_cola', 'trabajando')")
        datos.ejecutar("UPDATE referencias SET estado = 'error', error = 'Se cerró la app mientras analizaba. Quítala y vuelve a añadirla.' "
                       "WHERE estado IN ('en_cola', 'analizando')")
        _hilo = threading.Thread(target=_trabajar, name="iris-cola", daemon=True)
        _hilo.start()


def encolar(tipo: str, id_: str) -> None:
    _cancelados.discard(id_)
    _cola.put((tipo, id_))


def cancelar(id_: str) -> None:
    _cancelados.add(id_)
    proceso = _procesos.get(id_)
    if proceso and proceso.poll() is None:
        try:
            os.killpg(os.getpgid(proceso.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


def detener() -> None:
    """Cierre ordenado: para lo que esté corriendo (render, ffmpeg) para que no quede nada huérfano."""
    for id_ in list(_procesos):
        cancelar(id_)


def _revisar(id_: str) -> None:
    if id_ in _cancelados:
        raise Cancelado()


def _trabajar() -> None:
    while True:
        tipo, id_ = _cola.get()
        try:
            if tipo == "referencia":
                _analizar_referencia(id_)
            else:
                _construir(id_)
        except Cancelado:
            if tipo == "trabajo":
                datos.actualizar("trabajos", id_, {"estado": "cancelado", "etapa": None, "mensaje": "Cancelaste este video.", "eta": None, "actualizado": datos.ahora()})
            else:
                datos.actualizar("referencias", id_, {"estado": "error", "error": "Se canceló el análisis.", "creada": datos.ahora()})
        except Exception as error:  # cualquier fallo se cuenta en claro y no tumba la cola
            _registrar(tipo, id_, error)
        finally:
            _cancelados.discard(id_)
            _procesos.pop(id_, None)


def _mensaje_claro(error: Exception, tipo: str = "trabajo") -> str:
    texto = str(error).strip() or error.__class__.__name__
    minus = texto.lower()
    if isinstance(error, FileNotFoundError) and "ffmpeg" in minus:
        return "Falta ffmpeg en este equipo. Ejecuta ./instalar.sh o ./creador probar."
    if tipo == "referencia" and error.__class__.__module__.startswith("yt_dlp"):
        return "No pude bajar ese enlace. Instagram, TikTok y otras redes suelen pedir sesión o bloquear las descargas: descarga el video y súbelo como archivo."
    if tipo == "trabajo" and ("browser" in minus or "chrome" in minus):
        return "Remotion no pudo abrir su navegador. Ejecuta ./creador probar para ver qué falta."
    return texto[:300]


def _registrar(tipo: str, id_: str, error: Exception) -> None:
    base = carpeta_de_trabajo(id_) if tipo == "trabajo" else carpeta_de_referencia(id_)
    base.mkdir(parents=True, exist_ok=True)
    (base / "registro.txt").write_text(traceback.format_exc(), encoding="utf-8")
    claro = _mensaje_claro(error, tipo)
    if tipo == "trabajo":
        datos.actualizar("trabajos", id_, {"estado": "error", "etapa": None, "error": claro, "mensaje": None, "eta": None, "actualizado": datos.ahora()})
    else:
        datos.actualizar("referencias", id_, {"estado": "error", "error": claro, "etapa": None})


# ---------------------------------------------------------------------------------------------------------------------
# Referencias
# ---------------------------------------------------------------------------------------------------------------------

def _miniatura(video: Path, destino: Path, segundo: float = 1.0) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{segundo:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(destino)],
                   capture_output=True)
    if not destino.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(destino)], capture_output=True)


def _analizar_referencia(id_: str) -> None:
    ref = datos.uno("SELECT * FROM referencias WHERE id = ?", (id_,))
    if ref is None:
        return
    base = carpeta_de_referencia(id_)
    base.mkdir(parents=True, exist_ok=True)
    datos.actualizar("referencias", id_, {"estado": "analizando", "etapa": "Preparando", "progreso": 0.02})
    if ref["tipo"] == "enlace" and not ref["archivo"]:
        datos.actualizar("referencias", id_, {"etapa": "Descargando el video", "progreso": 0.05})
        try:
            meta, ruta = descargar.bajar_uno(ref["origen"], base)
        except Exception as error:
            ultima = (str(error).strip().splitlines() or ["error desconocido"])[-1]
            raise RuntimeError("No pude descargar ese enlace (" + re.sub(r"^ERROR: ", "", ultima)[:160] + "). Sube el archivo del video en su lugar.") from error
        datos.actualizar("referencias", id_, {"archivo": str(ruta.relative_to(datos.DATOS)), "titulo": (meta.get("titulo") or ref["titulo"])[:120]})
        ref = datos.uno("SELECT * FROM referencias WHERE id = ?", (id_,))
    ruta = datos.DATOS / ref["archivo"]
    _revisar(id_)

    def avance(fraccion: float) -> None:
        _revisar(id_)
        datos.actualizar("referencias", id_, {"progreso": round(0.25 + 0.65 * fraccion, 3)})

    datos.actualizar("referencias", id_, {"etapa": "Escuchando la voz y midiendo el ritmo", "progreso": 0.25})
    analisis = analizar.medir_video(ruta, "referencia", ref["archivo"], 0.3, True, modelo_de_voz(), base / "medios", con_planos=False, avance=avance)
    if analisis is None:
        raise RuntimeError("No pude leer ese video. Prueba con un archivo MP4 o MOV.")
    (base / "analisis.json").write_text(json.dumps(analisis, ensure_ascii=False), encoding="utf-8")
    datos.actualizar("referencias", id_, {"etapa": "Aprendiendo su estilo", "progreso": 0.93})
    acento = estilo.color_dominante(ruta, analisis["duracion"])
    _miniatura(ruta, base / "miniatura.jpg", min(1.0, analisis["duracion"] / 3))
    datos.actualizar("referencias", id_, {"estado": "lista", "etapa": None, "progreso": 1.0, "error": None, "perfil": estilo.perfil_de(analisis, acento)})


# ---------------------------------------------------------------------------------------------------------------------
# Trabajos
# ---------------------------------------------------------------------------------------------------------------------

class Avance:
    """Convierte «etapa N, fracción f» en un porcentaje total estable que nunca retrocede."""

    def __init__(self, id_: str, pasos: list[str]) -> None:
        self.id = id_
        self.pasos = pasos
        self.total = sum(PESOS[p] for p in pasos)
        self.maximo = 0.0

    def poner(self, paso: str, fraccion: float = 0.0, mensaje: str | None = None, **extra) -> None:
        _revisar(self.id)
        previo = sum(PESOS[p] for p in self.pasos[:self.pasos.index(paso)])
        porcentaje = (previo + PESOS[paso] * min(1.0, max(0.0, fraccion))) / self.total
        self.maximo = max(self.maximo, porcentaje)
        datos.actualizar("trabajos", self.id, {"estado": "trabajando", "etapa": ETAPAS[paso], "progreso": round(self.maximo, 4), "mensaje": mensaje,
                                              "actualizado": datos.ahora(), **extra})


def _perfil_de_referencias(ids: list[str]) -> dict | None:
    perfiles = []
    for id_ in ids:
        fila = datos.uno("SELECT perfil FROM referencias WHERE id = ? AND estado = 'lista'", (id_,))
        if fila and fila["perfil"]:
            perfiles.append(fila["perfil"])
    return estilo.agregar(perfiles)


def _voz_en_cache(modelo: str) -> bool:
    cache = Path.home() / ".cache" / "huggingface" / "hub"
    return cache.exists() and any(cache.glob(f"models--*faster-whisper-{modelo}"))


def _construir(id_: str) -> None:
    t = datos.uno("SELECT * FROM trabajos WHERE id = ?", (id_,))
    if t is None or not t["fuente_archivo"]:
        raise RuntimeError("Falta subir el video de este trabajo.")
    base = carpeta_de_trabajo(id_)
    config = interprete.efectivo(t["prompt"] or "", t["opciones"] or {})
    pasos = ["preparar"] + (["pausas"] if config["quitar_pausas"] else []) + ["voz", "guion", "render", "final"]
    avance = Avance(id_, pasos)
    inicio = datos.ahora()
    datos.actualizar("trabajos", id_, {"estado": "trabajando", "error": None, "resultado": None, "fotogramas_listos": 0, "fotogramas_total": 0, "eta": None})

    avance.poner("preparar", 0.1)
    fuente = datos.DATOS / t["fuente_archivo"]
    carpeta = carpeta_de_marca(t["marca"])
    duracion_fuente = t["fuente_duracion"] or 0.0
    video = fuente
    shutil.rmtree(base / "fotos", ignore_errors=True)
    shutil.rmtree(base / "render", ignore_errors=True)

    if config["quitar_pausas"]:
        avance.poner("pausas", 0.1, "Buscando silencios")
        sonda = analizar._sondear(fuente)
        corte = pausas.quitar(fuente, base / "sin-pausas.mp4", sonda["duracion"], sonda["tiene_audio"])
        video = corte["archivo"]
        avance.poner("pausas", 1.0, f"Quité {corte['quitado']:.1f} s de pausas" if corte["quitado"] else "No había pausas largas que quitar")

    modelo = modelo_de_voz()
    mensaje_voz = None if _voz_en_cache(modelo) else "La primera vez se descarga el modelo de voz: puede tardar unos minutos."
    avance.poner("voz", 0.0, mensaje_voz)
    analisis = analizar.medir_video(video, "propio", video.name, 0.3, True, modelo, base / "medios", con_planos=False,
                                    avance=lambda f: avance.poner("voz", f, mensaje_voz), idioma=config["idioma"])
    if analisis is None:
        raise RuntimeError("No pude leer el video. Prueba con un archivo MP4 o MOV.")
    (base / "analisis.json").write_text(json.dumps(analisis, ensure_ascii=False), encoding="utf-8")
    duracion = analisis["duracion"]

    avance.poner("guion", 0.2, "Aplicando lo que aprendí de tus referencias" if t["referencias"] else None)
    enlace = carpeta / "videos" / "propios" / f"iris-{id_}.mp4"
    enlace.parent.mkdir(parents=True, exist_ok=True)
    enlace.unlink(missing_ok=True)
    try:
        os.link(video, enlace)
    except OSError:
        shutil.copy2(video, enlace)
    try:
        colores = _colores_de_marca(carpeta)
        guion, notas = interprete.construir_guion(f"iris-{id_}", config, analisis, _perfil_de_referencias(t["referencias"] or []),
                                                  colores, f"{carpeta.name}/videos/propios/{enlace.name}")
        (base / "guion.json").write_text(json.dumps(guion, ensure_ascii=False, indent=1), encoding="utf-8")
        datos.actualizar("trabajos", id_, {"notas": notas})
        avance.poner("guion", 1.0, " · ".join(notas)[:600])
        _renderizar(id_, base, carpeta, guion, duracion, avance)
        _terminar(id_, base, video, analisis, duracion, carpeta, t, avance, inicio)
    finally:
        enlace.unlink(missing_ok=True)
        shutil.rmtree(base / "fotos", ignore_errors=True)
        shutil.rmtree(base / "render", ignore_errors=True)
        (base / "sin-pausas.mp4").unlink(missing_ok=True)


def _colores_de_marca(carpeta: Path) -> dict:
    ficha = carpeta / "marca.json"
    if ficha.exists():
        try:
            return dict(json.loads(ficha.read_text(encoding="utf-8")).get("colores") or {})
        except (ValueError, OSError):
            return {}
    return {}


def _renderizar(id_: str, base: Path, carpeta: Path, guion: dict, duracion: float, avance: Avance) -> None:
    total = max(1, round(guion["duracion"] * FPS))
    avance.poner("render", 0.0, "Preparando Remotion", fotogramas_total=total)
    props, publica, _ = _preparar(carpeta, base)
    fotos = base / "fotos"
    registro = base / "render.log"
    navegador = os.environ.get("CREADOR_NAVEGADOR")
    comando = ["npx", "remotion", "render", "src/index.ts", "Formato", str(fotos), "--sequence", "--image-format=jpeg", "--jpeg-quality=92",
               f"--props={props}", f"--public-dir={publica}"] + ([f"--browser-executable={navegador}"] if navegador else [])
    with open(registro, "w", encoding="utf-8") as salida:
        proceso = subprocess.Popen(comando, cwd=render.REMOTION, stdout=salida, stderr=subprocess.STDOUT, start_new_session=True)
        _procesos[id_] = proceso
        arranque = time.time()
        listos = 0
        try:
            while proceso.poll() is None:
                time.sleep(0.5)
                _revisar(id_)
                listos = sum(1 for _ in os.scandir(fotos)) if fotos.exists() else 0
                transcurrido = time.time() - arranque
                eta = (total - listos) / (listos / transcurrido) if listos >= 6 and transcurrido > 1 else None
                avance.poner("render", listos / total, f"Fotograma {min(listos, total)} de {total}", fotogramas_listos=listos, eta=eta)
        except BaseException:
            if proceso.poll() is None:
                try:
                    os.killpg(os.getpgid(proceso.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
            raise
    listos = sum(1 for _ in os.scandir(fotos)) if fotos.exists() else 0
    _revisar(id_)
    if proceso.returncode != 0 or listos < total:
        cola = [l for l in registro.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip() and not any(r in l for r in RUIDO)]
        raise RuntimeError("Remotion no pudo construir el video: " + (cola[-1].strip() if cola else "sin detalles") + " (más detalles en el registro del trabajo)")
    datos.actualizar("trabajos", id_, {"fotogramas_listos": listos, "eta": None})


def _preparar(carpeta: Path, base: Path):
    try:
        return render.preparar(carpeta, str(base / "guion.json"), cache=base / "render")
    except SystemExit as error:  # preparar() cuenta los problemas del guion con SystemExit
        raise RuntimeError(str(error)) from error


def _terminar(id_: str, base: Path, video: Path, analisis: dict, duracion: float, carpeta: Path, t: dict, avance: Avance, inicio: float) -> None:
    avance.poner("final", 0.1, "Mezclando la voz")
    fotos = base / "fotos"
    archivos = sorted(f for f in os.listdir(fotos) if f.endswith(".jpeg"))
    digitos = len(re.search(r"(\d+)\.jpeg$", archivos[0]).group(1))
    salida = base / "resultado.mp4"
    entrada = ["-framerate", str(FPS), "-i", str(fotos / f"element-%0{digitos}d.jpeg")]
    if analisis.get("audio") is not None:
        entrada += ["-i", str(video)]
        mapa = ["-map", "0:v", "-map", "1:a", "-af", "apad", "-c:a", "aac", "-b:a", "192k"]
    else:
        mapa = ["-map", "0:v"]
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entrada, *mapa, "-t", f"{duracion:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(salida)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not salida.exists():
        raise RuntimeError("No pude unir el video y el sonido: " + (r.stderr.strip().splitlines() or ["error desconocido"])[-1])
    avance.poner("final", 0.8, "Guardando")
    _miniatura(salida, base / "miniatura.jpg", min(1.0, duracion / 3))
    nombre = comun.seguro(t["titulo"] or "video") or "video"
    copia = carpeta / "salidas" / f"{nombre}-{id_[:6]}.mp4"
    copia.parent.mkdir(parents=True, exist_ok=True)
    copia.unlink(missing_ok=True)
    try:
        os.link(salida, copia)
    except OSError:
        shutil.copy2(salida, copia)
    datos.actualizar("trabajos", id_, {"estado": "listo", "etapa": None, "progreso": 1.0, "mensaje": f"Listo en {round(datos.ahora() - inicio)} s", "eta": None,
                                      "resultado": "resultado.mp4", "actualizado": datos.ahora()})
