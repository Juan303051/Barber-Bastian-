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
import audio
import comun
import descargar
import guion as revisor
import mezcla
import musica as analisis_musical
import numeros
import render
import sonidos

from . import calidad, cumplimiento, datos, escenas as unidor, estilo, interprete, pausas
from .direccion import ia, perfil as perfiles, plan as planes

NEUTRA = "maquetas-estilo"  # carpeta de la biblioteca compartida: aquí se guarda lo que no pertenece a una marca
FPS = 30
PESOS = {"preparar": 3, "unir": 8, "pausas": 8, "voz": 28, "direccion": 6, "guion": 2, "render": 46, "final": 8, "revision": 4}
ETAPAS = {
    "preparar": "Preparando tu video",
    "unir": "Uniendo tus escenas",
    "pausas": "Quitando las pausas largas",
    "voz": "Escuchando y transcribiendo la voz",
    "direccion": "Dirigiendo el video",
    "guion": "Armando el guion con lo que pediste",
    "render": "Construyendo el video",
    "final": "Mezclando y nivelando el sonido",
    "revision": "Revisando la calidad",
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


def carpeta_de_cancion(id_: str) -> Path:
    return datos.DATOS / "musica" / id_


EXTENSIONES_LOGO = {".png", ".webp", ".jpg", ".jpeg"}


def logo_de(marca: str | None) -> Path | None:
    """Logo que la persona subió para esta marca (vive en la carpeta de datos, no en el repositorio)."""
    if not marca:
        return None
    carpeta = datos.DATOS / "marcas" / marca
    return next((p for p in sorted(carpeta.glob("logo.*")) if p.suffix.lower() in EXTENSIONES_LOGO), None) if carpeta.is_dir() else None


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
        datos.ejecutar("UPDATE musica SET estado = 'error', error = 'Se cerró la app mientras analizaba. Quítala y vuelve a añadirla.' "
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
            elif tipo == "musica":
                _analizar_cancion(id_)
            else:
                _construir(id_)
        except Cancelado:
            if tipo == "trabajo":
                datos.actualizar("trabajos", id_, {"estado": "cancelado", "etapa": None, "mensaje": "Cancelaste este video.", "eta": None, "actualizado": datos.ahora()})
            elif tipo == "musica":
                datos.actualizar("musica", id_, {"estado": "error", "error": "Se canceló el análisis."})
            else:
                datos.actualizar("referencias", id_, {"estado": "error", "error": "Se canceló el análisis.", "creada": datos.ahora()})
        except Exception as error:  # cualquier fallo se cuenta en claro y no tumba la cola
            _registrar(tipo, id_, error)
        finally:
            _cancelados.discard(id_)
            _procesos.pop(id_, None)


def _analizar_cancion(id_: str) -> None:
    cancion = datos.uno("SELECT * FROM musica WHERE id = ?", (id_,))
    if cancion is None:
        return
    datos.actualizar("musica", id_, {"estado": "analizando", "etapa": "Midiendo tempo, pulsos y energía"})
    _revisar(id_)
    try:
        resultado = analisis_musical.analizar(datos.DATOS / cancion["archivo"])
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    _revisar(id_)
    datos.actualizar("musica", id_, {"estado": "lista", "etapa": None, "error": None, "analisis": resultado})


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
    base = carpeta_de_trabajo(id_) if tipo == "trabajo" else carpeta_de_referencia(id_) if tipo == "referencia" else carpeta_de_cancion(id_)
    base.mkdir(parents=True, exist_ok=True)
    (base / "registro.txt").write_text(traceback.format_exc(), encoding="utf-8")
    claro = _mensaje_claro(error, tipo)
    if tipo == "trabajo":
        datos.actualizar("trabajos", id_, {"estado": "error", "etapa": None, "error": claro, "mensaje": None, "eta": None, "actualizado": datos.ahora()})
    elif tipo == "musica":
        datos.actualizar("musica", id_, {"estado": "error", "error": claro, "etapa": None})
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


def _ficha_de_marca(carpeta: Path) -> tuple[str, str]:
    """(nombre, texto de la ficha de la bóveda) de la marca; vacíos si es la carpeta neutra o no hay ficha."""
    if carpeta.name == NEUTRA:
        return "", ""
    ficha = comun.boveda_empresa(carpeta) / "00-ficha.md"
    try:
        texto = ficha.read_text(encoding="utf-8") if ficha.exists() else ""
    except OSError:
        texto = ""
    return comun.nombre(carpeta), re.sub(r"^---.*?---\s*", "", texto, count=1, flags=re.S).strip()


def _biblioteca() -> list[dict]:
    filas = datos.todos("SELECT * FROM musica WHERE activa = 1 AND estado = 'lista'")
    return [{"id": f["id"], "titulo": f["titulo"], "licencia": f["licencia"], "archivo": datos.DATOS / f["archivo"], "analisis": f["analisis"]}
            for f in filas if f["analisis"] and (datos.DATOS / f["archivo"]).exists()]


def _elegir_cancion(energia: str | None, ritmo: str | None, duracion: float) -> dict | None:
    pista = analisis_musical.elegir_pista(_biblioteca(), energia, ritmo)
    if pista is None:
        return None
    a = pista["analisis"]
    entrada = analisis_musical.punto_de_entrada(a, duracion)
    inicio = entrada["inicio"]
    limite = inicio + duracion
    return {"id": pista["id"], "titulo": pista["titulo"], "licencia": pista["licencia"], "archivo": pista["archivo"], "inicio": inicio, "repetir": entrada["repetir"],
            "lufs": (a.get("volumen") or {}).get("lufs"), "bpm": a["bpm"], "ritmo": a["ritmo"], "intensidad": a["intensidad"], "confianza": a["confianza"],
            "caida_en": entrada["caida_en"],
            "pulsos": [round(x - inicio, 3) for x in a["pulsos"] if inicio <= x <= limite],
            "fuertes": [round(x - inicio, 3) for x in a["tiempos_fuertes"] if inicio <= x <= limite]}


def escenas_de(t: dict) -> list[dict]:
    """Las escenas del video en orden. Un trabajo guardado por una versión anterior tiene un solo archivo: se trata como una escena."""
    lista = list(t.get("escenas") or [])
    if not lista and t.get("fuente_archivo"):
        lista = [{"id": "unica", "archivo": t["fuente_archivo"], "nombre": t["fuente_nombre"], "duracion": t["fuente_duracion"] or 0.0, "vertical": bool(t["fuente_vertical"]), "audio": True}]
    return lista


def pasos_de(config: dict, n_escenas: int) -> list[str]:
    return ["preparar"] + (["unir"] if n_escenas > 1 else []) + (["pausas"] if config["quitar_pausas"] else []) + ["voz", "direccion", "guion", "render", "final", "revision"]


def _construir(id_: str) -> None:
    t = datos.uno("SELECT * FROM trabajos WHERE id = ?", (id_,))
    escenas = escenas_de(t) if t else []
    if t is None or not escenas:
        raise RuntimeError("Falta subir el video de este trabajo.")
    base = carpeta_de_trabajo(id_)
    config = interprete.efectivo(t["prompt"] or "", t["opciones"] or {})
    pasos = pasos_de(config, len(escenas))
    avance = Avance(id_, pasos)
    inicio = datos.ahora()
    datos.actualizar("trabajos", id_, {"estado": "trabajando", "error": None, "resultado": None, "fotogramas_listos": 0, "fotogramas_total": 0, "eta": None,
                                       "calidad": None, "plan": None, "ia_info": None, "musica_id": None, "cumplimiento": None})

    avance.poner("preparar", 0.1)
    fuente = datos.DATOS / escenas[0]["archivo"]
    carpeta = carpeta_de_marca(t["marca"])
    video = fuente
    cortes: list[dict] = []  # instantes donde hay un corte de verdad: ahí caben las transiciones
    pausas_quitadas: float | None = None
    shutil.rmtree(base / "fotos", ignore_errors=True)
    shutil.rmtree(base / "render", ignore_errors=True)

    if len(escenas) > 1:
        avance.poner("unir", 0.05, f"Uniendo {len(escenas)} escenas")
        vertical = bool(escenas[0].get("vertical", True))
        ancho, alto = (1080, 1920) if vertical else (1920, 1080)
        if config["borrador"]:
            ancho, alto = ancho // 2, alto // 2
        union = unidor.unir([{"archivo": datos.DATOS / e["archivo"], "duracion": e["duracion"], "audio": e.get("audio", True)} for e in escenas], base / "union.mp4", ancho, alto)
        fuente = video = union["archivo"]
        cortes = [{"t": x, "tipo": "escena"} for x in union["limites"]]
        avance.poner("unir", 1.0, f"{len(escenas)} escenas unidas ({union['duracion']:.0f} s)")

    if config["quitar_pausas"]:
        avance.poner("pausas", 0.1, "Buscando silencios")
        sonda = analizar._sondear(fuente)
        corte = pausas.quitar(fuente, base / "sin-pausas.mp4", sonda["duracion"], sonda["tiene_audio"])
        video = corte["archivo"]
        pausas_quitadas = corte["quitado"]
        cortes = [{"t": round(pausas.remapear(c["t"], corte["tramos"]), 3), "tipo": c["tipo"]} for c in cortes] + [{"t": x, "tipo": "pausa"} for x in corte["instantes"]]
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

    # Dirección: la ficha y el test de la marca, la música candidata y el plan (con IA, o por reglas)
    avance.poner("direccion", 0.1, "Leyendo la ficha de la marca y tus preferencias")
    marca_nombre, ficha = _ficha_de_marca(carpeta)
    perfil_creativo = perfiles.leer(t["marca"])
    referencia = _perfil_de_referencias(t["referencias"] or [])
    palabras = [list(p) for p in (analisis.get("voz") or {}).get("palabras", [])]
    contexto = {"brief": t["prompt"] or "", "duracion": duracion, "palabras": palabras, "ficha": ficha, "marca_nombre": marca_nombre,
                "perfil": perfil_creativo, "referencia": referencia, "config": config, "vertical": bool(analisis.get("vertical", True)), "musica": None,
                "cortes": cortes, "tiene_logo": logo_de(t["marca"]) is not None, "escenas": len(escenas)}
    base_plan = planes.plan_base(contexto)
    candidata = _elegir_cancion(base_plan["musica"]["energia"], base_plan["musica"]["ritmo"], duracion) if config["musica"] and base_plan["musica"]["usar"] else None
    contexto["musica"] = candidata
    notas_direccion: list[str] = []
    resultado_ia = {"plan": None, "origen": "reglas", "motivo": None, "advertencias": [], "modelo": None, "uso": None, "costo_usd": None}
    if config["ia"] and palabras:
        avance.poner("direccion", 0.3, "Consultando al director con IA")
        resultado_ia = ia.generar_plan(contexto, video)
        _revisar(id_)
    plan = resultado_ia["plan"] or base_plan
    if resultado_ia["plan"]:
        notas_direccion.append(f"Dirigido con IA ({ia.MODELOS.get(resultado_ia['modelo'], {}).get('nombre', resultado_ia['modelo'])})")
    elif resultado_ia["motivo"]:
        notas_direccion.append(f"Sin IA: {resultado_ia['motivo']} Usé las reglas.")
    notas_direccion += resultado_ia["advertencias"]
    elegida = None
    if config["musica"] and plan["musica"]["usar"]:
        elegida = _elegir_cancion(plan["musica"]["energia"], plan["musica"]["ritmo"], duracion)
        if elegida is None and not _biblioteca():
            notas_direccion.append("No usé música: tu biblioteca no tiene canciones listas.")
        elif elegida:
            notas_direccion.append(f"Música «{elegida['titulo']}» ({elegida['bpm']:.0f} BPM)")
    datos.actualizar("trabajos", id_, {"plan": {**plan, "advertencias_ia": resultado_ia["advertencias"]}, "musica_id": elegida["id"] if elegida else None,
                                       "ia_info": {"usada": bool(resultado_ia["plan"]), "modelo": resultado_ia["modelo"], "motivo": resultado_ia["motivo"],
                                                   "uso": resultado_ia["uso"], "costo_usd": resultado_ia["costo_usd"]}})
    avance.poner("direccion", 1.0, " · ".join(notas_direccion)[:600] or None)

    avance.poner("guion", 0.2, "Aplicando lo que aprendí de tus referencias" if t["referencias"] else None)
    logo_origen = logo_de(t["marca"])
    config = interprete.resolver(config, plan, logo_origen is not None, bool(numeros.operaciones(numeros.encontrar(palabras))))
    enlace = carpeta / "videos" / "propios" / f"iris-{id_}.mp4"
    enlace.parent.mkdir(parents=True, exist_ok=True)
    enlace.unlink(missing_ok=True)
    try:
        os.link(video, enlace)
    except OSError:
        shutil.copy2(video, enlace)
    enlace_logo = None
    if config["logo"] and logo_origen is not None:
        enlace_logo = carpeta / "videos" / "propios" / f"iris-{id_}-logo{logo_origen.suffix.lower()}"
        enlace_logo.unlink(missing_ok=True)
        try:
            os.link(logo_origen, enlace_logo)
        except OSError:
            shutil.copy2(logo_origen, enlace_logo)
    try:
        colores = _colores_de_marca(carpeta)
        pulsos = {"pulsos": elegida["pulsos"], "fuertes": elegida["fuertes"], "confianza": elegida["confianza"]} if elegida else None
        guion, notas = interprete.construir_guion(f"iris-{id_}", config, analisis, referencia, colores, f"{carpeta.name}/videos/propios/{enlace.name}",
                                                  plan=plan, musica=pulsos, marca_nombre=marca_nombre, cortes=cortes,
                                                  logo=f"{carpeta.name}/videos/propios/{enlace_logo.name}" if enlace_logo else None)
        notas = notas_direccion + notas
        (base / "guion.json").write_text(json.dumps(guion, ensure_ascii=False, indent=1), encoding="utf-8")
        datos.actualizar("trabajos", id_, {"notas": notas})
        avance.poner("guion", 1.0, " · ".join(notas)[:600])
        _renderizar(id_, base, carpeta, guion, duracion, avance)
        _terminar(id_, base, video, analisis, duracion, carpeta, t, avance, inicio, guion=guion, contexto=contexto, plan=plan, musica=elegida, config=config,
                   extra={"pausas_quitadas": pausas_quitadas, "hay_cortes": bool(cortes), "tiene_logo": logo_origen is not None, "marca_nombre": marca_nombre, "ficha": ficha})
    finally:
        enlace.unlink(missing_ok=True)
        if enlace_logo is not None:
            enlace_logo.unlink(missing_ok=True)
        shutil.rmtree(base / "fotos", ignore_errors=True)
        shutil.rmtree(base / "render", ignore_errors=True)
        (base / "sin-pausas.mp4").unlink(missing_ok=True)
        (base / "union.mp4").unlink(missing_ok=True)
        (base / "audio-final.m4a").unlink(missing_ok=True)
        (base / "efectos.wav").unlink(missing_ok=True)


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


def _terminar(id_: str, base: Path, video: Path, analisis: dict, duracion: float, carpeta: Path, t: dict, avance: Avance, inicio: float,
              guion: dict, contexto: dict, plan: dict, musica: dict | None, config: dict, extra: dict | None = None) -> None:
    extra = extra or {}
    avance.poner("final", 0.1, "Limpiando la voz y nivelando el volumen")
    fotos = base / "fotos"
    archivos = sorted(f for f in os.listdir(fotos) if f.endswith(".jpeg"))
    digitos = len(re.search(r"(\d+)\.jpeg$", archivos[0]).group(1))
    salida = base / "resultado.mp4"
    entrada = ["-framerate", str(FPS), "-i", str(fotos / f"element-%0{digitos}d.jpeg")]
    tiene_voz = analisis.get("audio") is not None
    audio_final = base / "audio-final.m4a"
    nota_audio = None
    efectos = None
    if config.get("sonidos") and tiene_voz:
        nivel = (plan.get("sonidos") or {}).get("nivel") or "sutil"
        eventos = sonidos.eventos_de_guion(guion, nivel if nivel in mezcla.NIVELES_EFECTOS else "sutil")
        if eventos:
            sonidos.escribir(sonidos.pista(eventos, duracion), base / "efectos.wav")
            efectos = {"archivo": base / "efectos.wav", "nivel": nivel if nivel in mezcla.NIVELES_EFECTOS else "sutil", "cantidad": len(eventos)}
    try:
        cancion = {"archivo": musica["archivo"], "inicio": musica["inicio"], "repetir": musica["repetir"], "lufs": musica["lufs"]} if musica else None
        informe = mezcla.masterizar(video if tiene_voz else None, audio_final, duracion, cancion, efectos=efectos)
    except RuntimeError as error:  # si la mezcla falla, el video sale con el audio original en vez de no salir
        informe, nota_audio = None, f"No pude mezclar y nivelar el audio ({error}); dejé el sonido original."
        audio_final.unlink(missing_ok=True)
    if informe is not None and efectos is not None:
        notas_previas = (datos.uno("SELECT notas FROM trabajos WHERE id = ?", (id_,)) or {}).get("notas") or []
        datos.actualizar("trabajos", id_, {"notas": notas_previas + [f"{efectos['cantidad']} efectos de sonido ({efectos['nivel']}) bajo tu voz"]})
    if informe is not None and audio_final.exists():
        entrada += ["-i", str(audio_final)]
        mapa = ["-map", "0:v", "-map", "1:a", "-c:a", "copy"]
    elif tiene_voz:
        entrada += ["-i", str(video)]
        mapa = ["-map", "0:v", "-map", "1:a", "-af", "apad", "-c:a", "aac", "-b:a", "192k"]
    else:
        mapa = ["-map", "0:v"]
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", *entrada, *mapa, "-t", f"{duracion:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(salida)], capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not salida.exists():
        raise RuntimeError("No pude unir el video y el sonido: " + (r.stderr.strip().splitlines() or ["error desconocido"])[-1])
    avance.poner("final", 0.9, "Guardando")
    _miniatura(salida, base / "miniatura.jpg", min(1.0, duracion / 3))

    avance.poner("revision", 0.2, "Midiendo volumen, picos, negros y zonas seguras")
    try:
        menores = calidad.hay_menores(contexto.get("palabras", []), t["marca"] or "", extra.get("ficha", ""))
        informe_calidad = calidad.revisar(salida, guion, contexto, plan, musica, bool(config.get("borrador")),
                                          extra={"efectos": efectos, "menores": menores, "permiso_menores": bool((t["opciones"] or {}).get("permiso_menores"))})
    except Exception as error:  # noqa: BLE001 - revisar no debe impedir entregar el video
        informe_calidad = {"veredicto": "revisar", "resumen": "No pude completar la revisión automática.", "pruebas": [
            {"id": "revision", "nivel": "aviso", "texto": f"No pude completar la revisión automática ({type(error).__name__})."}]}
    if nota_audio:
        informe_calidad["pruebas"].insert(0, {"id": "mezcla", "nivel": "aviso", "texto": nota_audio})
        informe_calidad["veredicto"] = "revisar" if informe_calidad["veredicto"] == "listo" else informe_calidad["veredicto"]
    nombre = comun.seguro(t["titulo"] or "video") or "video"
    copia = carpeta / "salidas" / f"{nombre}-{id_[:6]}.mp4"
    copia.parent.mkdir(parents=True, exist_ok=True)
    copia.unlink(missing_ok=True)
    try:
        os.link(salida, copia)
    except OSError:
        shutil.copy2(salida, copia)
    try:
        filas = cumplimiento.evaluar(config, plan, guion, efectos=efectos, musica=musica, tiene_logo=bool(extra.get("tiene_logo")),
                                     pausas_quitadas=extra.get("pausas_quitadas"), hay_cortes=bool(extra.get("hay_cortes")))
    except Exception:  # noqa: BLE001 - el resumen de lo pedido nunca debe impedir entregar el video
        filas = []
    datos.actualizar("trabajos", id_, {"estado": "listo", "etapa": None, "progreso": 1.0, "mensaje": f"Listo en {round(datos.ahora() - inicio)} s", "eta": None,
                                      "resultado": "resultado.mp4", "calidad": informe_calidad, "cumplimiento": filas, "actualizado": datos.ahora()})
