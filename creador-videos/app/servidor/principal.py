"""Servidor local de Iris: cuentas, referencias, trabajos y archivos. Solo escucha en este equipo."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import comun

from . import calidad, datos, interprete, produccion, seguridad
from .direccion import ia, perfil as perfiles

WEB = datos.RAIZ_APP / "web"
COOKIE = "iris_sesion"
EXTENSIONES = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
EXTENSIONES_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
TIPOS_AUDIO = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".ogg": "audio/ogg", ".opus": "audio/ogg"}
MAX_BYTES_AUDIO = 300 * 1024**2
LICENCIAS = set(calidad.LICENCIAS)
MAX_BYTES = int(float(os.environ.get("IRIS_MAX_GB", "4")) * 1024**3)
MAX_MINUTOS = 45
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


PASO_DE = {texto: clave for clave, texto in produccion.ETAPAS.items()}


def _pasos_de(opciones: dict) -> list[dict]:
    claves = ["preparar"] + (["pausas"] if opciones.get("quitar_pausas") else []) + ["voz", "direccion", "guion", "render", "final", "revision"]
    return [{"clave": c, "texto": produccion.ETAPAS[c]} for c in claves]


def error(estado: int, mensaje: str, **extra) -> HTTPException:
    return HTTPException(estado, {"mensaje": mensaje, **extra})


class Defensas(BaseHTTPMiddleware):
    """Rechaza peticiones que no vienen de esta misma página y pone las cabeceras de seguridad."""

    def __init__(self, app, puerto: int) -> None:
        super().__init__(app)
        self.puerto = puerto

    async def dispatch(self, request: Request, siguiente):
        if not seguridad.host_permitido(request.headers.get("host"), self.puerto):
            return JSONResponse({"mensaje": "Esta app solo se abre desde este equipo."}, status_code=421)
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not seguridad.origen_permitido(
                request.headers.get("origin"), request.headers.get("sec-fetch-site"), self.puerto):
            return JSONResponse({"mensaje": "Petición rechazada por seguridad."}, status_code=403)
        respuesta = await siguiente(request)
        respuesta.headers["Content-Security-Policy"] = CSP
        respuesta.headers["X-Content-Type-Options"] = "nosniff"
        respuesta.headers["Referrer-Policy"] = "no-referrer"
        respuesta.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        if request.url.path.startswith("/api/") and "cache-control" not in respuesta.headers:
            respuesta.headers["Cache-Control"] = "no-store"
        return respuesta


def crear_app(puerto: int = 8765) -> FastAPI:
    app = FastAPI(title="Iris", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Defensas, puerto=puerto)
    datos.abrir()
    produccion.iniciar()

    # ------------------------------------------------------------------------------------------------------ cuentas
    def usuario(request: Request) -> dict:
        encontrado = seguridad.usuario_de_token(request.cookies.get(COOKIE))
        if encontrado is None:
            raise error(401, "Inicia sesión para continuar.")
        return encontrado

    def poner_cookie(respuesta: Response, token: str, duracion: int | None) -> None:
        respuesta.set_cookie(COOKIE, token, max_age=duracion, httponly=True, samesite="strict", path="/")

    @app.get("/api/sesion")
    def sesion(request: Request):
        encontrado = seguridad.usuario_de_token(request.cookies.get(COOKIE))
        cuantos = datos.uno("SELECT COUNT(*) AS n FROM usuarios")["n"]
        return {"autenticado": encontrado is not None, "usuario": encontrado, "primera_vez": cuantos == 0}

    @app.post("/api/registro")
    async def registro(request: Request, respuesta: Response):
        cuerpo = await _json(request)
        correo = str(cuerpo.get("correo", "")).strip().lower()
        nombre = str(cuerpo.get("nombre", "")).strip()
        contrasena = str(cuerpo.get("contrasena", ""))
        cuantos = datos.uno("SELECT COUNT(*) AS n FROM usuarios")["n"]
        quien = seguridad.usuario_de_token(request.cookies.get(COOKIE))
        if cuantos > 0 and quien is None:
            raise error(403, "Solo una persona que ya entró puede añadir a otra al equipo.")
        errores = seguridad.validar_registro(correo, nombre, contrasena)
        if errores:
            raise error(422, "Revisa los datos marcados.", campos=errores)
        if datos.uno("SELECT id FROM usuarios WHERE correo = ?", (correo,)):
            raise error(409, "Ya hay una cuenta con ese correo.", campos={"correo": "Ya hay una cuenta con ese correo."})
        sal, clave = seguridad.crear_clave(contrasena)
        datos.insertar("usuarios", {"correo": correo, "nombre": nombre, "sal": sal, "clave": clave, "creado": datos.ahora()})
        nuevo = datos.uno("SELECT id, correo, nombre FROM usuarios WHERE correo = ?", (correo,))
        if quien is None:  # primera cuenta: entra directamente
            token, duracion = seguridad.crear_sesion(nuevo["id"], bool(cuerpo.get("recordar", True)))
            poner_cookie(respuesta, token, duracion)
        return {"usuario": nuevo, "entro": quien is None}

    @app.post("/api/entrar")
    async def entrar(request: Request, respuesta: Response):
        cuerpo = await _json(request)
        correo = str(cuerpo.get("correo", "")).strip().lower()
        contrasena = str(cuerpo.get("contrasena", ""))
        ip = request.client.host if request.client else "?"
        espera = max(seguridad.segundos_de_espera(f"correo:{correo}", seguridad.MAX_INTENTOS_CORREO),
                     seguridad.segundos_de_espera(f"ip:{ip}", seguridad.MAX_INTENTOS_IP))
        if espera:
            raise HTTPException(429, {"mensaje": f"Demasiados intentos. Inténtalo de nuevo en {max(1, round(espera / 60))} min.", "espera": espera},
                                headers={"Retry-After": str(espera)})
        fila = datos.uno("SELECT * FROM usuarios WHERE correo = ?", (correo,))
        if not seguridad.verificar_clave(contrasena, fila["sal"] if fila else None, fila["clave"] if fila else None):
            seguridad.anotar_fallo(f"correo:{correo}")
            seguridad.anotar_fallo(f"ip:{ip}")
            raise error(401, "El correo o la contraseña no coinciden.")
        seguridad.borrar_fallos(f"correo:{correo}")
        token, duracion = seguridad.crear_sesion(fila["id"], bool(cuerpo.get("recordar", False)))
        poner_cookie(respuesta, token, duracion)
        return {"usuario": {"id": fila["id"], "correo": fila["correo"], "nombre": fila["nombre"]}}

    @app.post("/api/salir")
    def salir(request: Request, respuesta: Response):
        seguridad.cerrar_sesion(request.cookies.get(COOKIE))
        respuesta.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.delete("/api/cuenta")
    async def eliminar_cuenta(request: Request, respuesta: Response):
        yo = usuario(request)
        cuerpo = await _json(request)
        fila = datos.uno("SELECT * FROM usuarios WHERE id = ?", (yo["id"],))
        if not seguridad.verificar_clave(str(cuerpo.get("contrasena", "")), fila["sal"], fila["clave"]):
            raise error(403, "La contraseña no coincide.", campos={"contrasena": "La contraseña no coincide."})
        if cuerpo.get("borrar_trabajos"):
            for t in datos.todos("SELECT id FROM trabajos WHERE usuario_id = ?", (yo["id"],)):
                _borrar_trabajo(t["id"])
            for r in datos.todos("SELECT id FROM referencias WHERE usuario_id = ?", (yo["id"],)):
                _borrar_referencia(r["id"])
            for m in datos.todos("SELECT id FROM musica WHERE usuario_id = ?", (yo["id"],)):
                shutil.rmtree(produccion.carpeta_de_cancion(m["id"]), ignore_errors=True)
                datos.ejecutar("DELETE FROM musica WHERE id = ?", (m["id"],))
        datos.ejecutar("UPDATE trabajos SET usuario_id = NULL WHERE usuario_id = ?", (yo["id"],))
        datos.ejecutar("UPDATE referencias SET usuario_id = NULL WHERE usuario_id = ?", (yo["id"],))
        datos.ejecutar("UPDATE musica SET usuario_id = NULL WHERE usuario_id = ?", (yo["id"],))
        datos.ejecutar("DELETE FROM usuarios WHERE id = ?", (yo["id"],))
        respuesta.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    # ------------------------------------------------------------------------------------------------- panel
    @app.get("/api/marcas")
    def marcas(request: Request):
        usuario(request)
        salida = []
        for carpeta in comun.empresas():
            if carpeta.name == produccion.NEUTRA:
                continue
            acento = produccion._colores_de_marca(carpeta).get("acento")
            salida.append({"id": carpeta.name, "nombre": comun.nombre(carpeta), "acento": acento})
        return salida

    def publica_referencia(r: dict) -> dict:
        tiene = (produccion.carpeta_de_referencia(r["id"]) / "miniatura.jpg").exists()
        return {"id": r["id"], "tipo": r["tipo"], "titulo": r["titulo"], "origen": r["origen"], "estado": r["estado"], "etapa": r["etapa"],
                "progreso": r["progreso"], "error": r["error"], "perfil": r["perfil"], "activa": bool(r["activa"]), "miniatura": tiene}

    def publico_trabajo(t: dict) -> dict:
        base = produccion.carpeta_de_trabajo(t["id"])
        if t["estado"] == "listo" and not (base / "resultado.mp4").exists():  # alguien borró el archivo a mano: se avisa en vez de mostrar un video roto
            t = {**t, "estado": "interrumpido", "resultado": None, "mensaje": "El video ya no está en este equipo. Puedes volver a crearlo."}
        config = interprete.efectivo(t["prompt"] or "", t["opciones"] or {})
        return {"id": t["id"], "marca": t["marca"], "titulo": t["titulo"], "prompt": t["prompt"], "opciones": t["opciones"] or {},
                "fuente_nombre": t["fuente_nombre"], "fuente_duracion": t["fuente_duracion"], "vertical": bool(t["fuente_vertical"]), "estado": t["estado"], "etapa": t["etapa"],
                "progreso": t["progreso"], "mensaje": t["mensaje"], "error": t["error"], "resultado": bool(t["resultado"]),
                "fotogramas_total": t["fotogramas_total"], "fotogramas_listos": t["fotogramas_listos"], "eta": t["eta"],
                "miniatura": (base / "miniatura.jpg").exists(), "entendido": interprete.resumen(config), "pendiente": config["pendiente"],
                "sugerencias": _sugerencias(config, t["opciones"] or {}), "actualizado": t["actualizado"], "notas": t["notas"] or [],
                "pasos": _pasos_de(t["opciones"] or {}), "paso": PASO_DE.get(t["etapa"]) or ("cola" if t["estado"] == "en_cola" else None),
                "calidad": t["calidad"], "ia": t["ia_info"], "direccion": _direccion_publica(t["plan"]), "musica": _musica_de_trabajo(t["musica_id"])}

    def publica_cancion(m: dict) -> dict:
        a = m["analisis"] or {}
        return {"id": m["id"], "titulo": m["titulo"], "estado": m["estado"], "etapa": m["etapa"], "error": m["error"], "licencia": m["licencia"], "activa": bool(m["activa"]),
                "bpm": a.get("bpm"), "ritmo": a.get("ritmo"), "intensidad": a.get("intensidad"), "confianza": a.get("confianza"), "duracion": a.get("duracion"),
                "lufs": (a.get("volumen") or {}).get("lufs"), "caidas": len(a.get("caidas") or [])}

    @app.get("/api/estado")
    def estado(request: Request):
        usuario(request)
        referencias = [publica_referencia(r) for r in datos.todos("SELECT * FROM referencias ORDER BY creada")]
        trabajos = [publico_trabajo(t) for t in datos.todos("SELECT * FROM trabajos ORDER BY orden, creado")]
        musica = [publica_cancion(m) for m in datos.todos("SELECT * FROM musica ORDER BY creada")]
        return {"referencias": referencias, "trabajos": trabajos, "musica": musica, "ia": ia.estado_publico()}

    @app.post("/api/interpretar")
    async def interpretar(request: Request):
        usuario(request)
        cuerpo = await _json(request)
        config = interprete.efectivo(str(cuerpo.get("prompt", ""))[:4000], cuerpo.get("opciones") or {})
        return {"entendido": interprete.resumen(config), "pendiente": config["pendiente"], "sugerencias": _sugerencias(config, cuerpo.get("opciones") or {})}

    # --------------------------------------------------------------------------------------------- referencias
    @app.post("/api/referencias/enlace")
    async def referencia_enlace(request: Request):
        yo = usuario(request)
        url = str((await _json(request)).get("url", "")).strip()
        if not re.match(r"^https?://[^\s]+$", url) or len(url) > 500:
            raise error(422, "Pega un enlace completo, por ejemplo https://www.instagram.com/reel/…")
        id_ = uuid.uuid4().hex[:12]
        datos.insertar("referencias", {"id": id_, "usuario_id": yo["id"], "tipo": "enlace", "titulo": re.sub(r"^https?://(www\.)?", "", url)[:80], "origen": url,
                                       "estado": "en_cola", "etapa": "En espera", "creada": datos.ahora()})
        produccion.encolar("referencia", id_)
        return {"id": id_}

    @app.put("/api/referencias/archivo")
    async def referencia_archivo(request: Request, nombre: str = "referencia.mp4"):
        yo = usuario(request)
        id_ = uuid.uuid4().hex[:12]
        base = produccion.carpeta_de_referencia(id_)
        ruta = await _guardar_video(request, base / "video", nombre)
        datos.insertar("referencias", {"id": id_, "usuario_id": yo["id"], "tipo": "archivo", "titulo": _titulo_de(nombre), "archivo": str(ruta.relative_to(datos.DATOS)),
                                       "estado": "en_cola", "etapa": "En espera", "creada": datos.ahora()})
        produccion.encolar("referencia", id_)
        return {"id": id_}

    @app.patch("/api/referencias/{id_}")
    async def referencia_cambiar(id_: str, request: Request):
        usuario(request)
        _existe("referencias", id_)
        cuerpo = await _json(request)
        if "activa" in cuerpo:
            datos.actualizar("referencias", id_, {"activa": 1 if cuerpo["activa"] else 0})
        return {"ok": True}

    @app.delete("/api/referencias/{id_}")
    def referencia_borrar(id_: str, request: Request):
        usuario(request)
        _existe("referencias", id_)
        produccion.cancelar(id_)
        _borrar_referencia(id_)
        return {"ok": True}

    @app.get("/api/referencias/{id_}/miniatura")
    def referencia_miniatura(id_: str, request: Request):
        usuario(request)
        return _archivo(produccion.carpeta_de_referencia(_id(id_)) / "miniatura.jpg", "image/jpeg")

    # --------------------------------------------------------------------------------------------------- música
    @app.put("/api/musica/archivo")
    async def musica_subir(request: Request, nombre: str = "cancion.mp3"):
        yo = usuario(request)
        id_ = uuid.uuid4().hex[:12]
        ruta = await _guardar_archivo(request, produccion.carpeta_de_cancion(id_) / "pista", nombre, EXTENSIONES_AUDIO, MAX_BYTES_AUDIO,
                                      "Ese tipo de archivo no es música compatible. Usa MP3, WAV, M4A, AAC, FLAC u OGG.")
        datos.insertar("musica", {"id": id_, "usuario_id": yo["id"], "titulo": _titulo_de(nombre)[:80] or "Canción", "archivo": str(ruta.relative_to(datos.DATOS)),
                                  "estado": "en_cola", "etapa": "En espera", "licencia": "sin-confirmar", "creada": datos.ahora()})
        produccion.encolar("musica", id_)
        return {"id": id_}

    @app.patch("/api/musica/{id_}")
    async def musica_cambiar(id_: str, request: Request):
        usuario(request)
        _existe("musica", id_)
        cuerpo = await _json(request)
        cambios: dict = {}
        if "licencia" in cuerpo:
            if cuerpo["licencia"] not in LICENCIAS:
                raise error(422, "Elige una de las licencias de la lista.")
            cambios["licencia"] = cuerpo["licencia"]
        if "activa" in cuerpo:
            cambios["activa"] = 1 if cuerpo["activa"] else 0
        if "titulo" in cuerpo and str(cuerpo["titulo"]).strip():
            cambios["titulo"] = str(cuerpo["titulo"]).strip()[:80]
        datos.actualizar("musica", id_, cambios)
        return {"ok": True}

    @app.delete("/api/musica/{id_}")
    def musica_borrar(id_: str, request: Request):
        usuario(request)
        _existe("musica", id_)
        produccion.cancelar(id_)
        shutil.rmtree(produccion.carpeta_de_cancion(id_), ignore_errors=True)
        datos.ejecutar("DELETE FROM musica WHERE id = ?", (id_,))
        return {"ok": True}

    @app.get("/api/musica/{id_}/audio")
    def musica_audio(id_: str, request: Request):
        usuario(request)
        m = _existe("musica", id_)
        ruta = datos.DATOS / (m["archivo"] or "")
        return _archivo(ruta, TIPOS_AUDIO.get(ruta.suffix.lower(), "application/octet-stream"))

    # ------------------------------------------------------------------------------------------------------ IA
    @app.get("/api/ia")
    def ia_estado(request: Request):
        usuario(request)
        return ia.estado_publico()

    @app.put("/api/ia")
    async def ia_guardar(request: Request):
        usuario(request)
        cuerpo = await _json(request)
        cambios = {k: cuerpo[k] for k in ("activa", "ver_fotogramas", "modelo", "clave") if k in cuerpo}
        if "clave" in cambios and (not isinstance(cambios["clave"], str) or len(cambios["clave"]) > 300 or re.search(r"\s", cambios["clave"].strip())):
            raise error(422, "Esa clave no parece válida: pégala completa y sin espacios.")
        ia.guardar_ajustes(cambios)
        return ia.estado_publico()

    @app.post("/api/ia/probar")
    def ia_probar(request: Request):
        usuario(request)
        ok, mensaje = ia.probar_clave(ia.estado_publico()["modelo"])
        return {"ok": ok, "mensaje": mensaje}

    # ------------------------------------------------------------------------------- test del director
    @app.get("/api/perfil")
    def perfil_leer(request: Request, marca: str = ""):
        usuario(request)
        marca_ok = _marca_valida(marca)
        return {"preguntas": perfiles.PREGUNTAS, "respuestas": perfiles.leer_exacto(marca_ok) or {}, "marca": marca_ok,
                "general": perfiles.leer_exacto(None) or {} if marca_ok else None}

    @app.put("/api/perfil")
    async def perfil_guardar(request: Request):
        usuario(request)
        cuerpo = await _json(request)
        marca_ok = _marca_valida(cuerpo.get("marca"))
        limpias, errores = perfiles.validar(cuerpo.get("respuestas") if isinstance(cuerpo.get("respuestas"), dict) else {})
        if errores:
            raise error(422, "Revisa las respuestas marcadas.", campos=errores)
        perfiles.guardar(marca_ok, limpias)
        return {"ok": True, "respuestas": limpias}

    # ------------------------------------------------------------------------------------------------ trabajos
    @app.post("/api/trabajos")
    async def trabajo_nuevo(request: Request):
        yo = usuario(request)
        cuerpo = await _json(request)
        id_ = uuid.uuid4().hex[:12]
        n = datos.uno("SELECT COUNT(*) AS n FROM trabajos")["n"]
        marca = _marca_valida(cuerpo.get("marca"))
        datos.insertar("trabajos", {"id": id_, "usuario_id": yo["id"], "marca": marca, "titulo": str(cuerpo.get("titulo") or f"Video {n + 1}")[:80],
                                    "prompt": "", "opciones": {}, "estado": "borrador", "referencias": [], "creado": datos.ahora(), "actualizado": datos.ahora(),
                                    "orden": int(datos.ahora())})
        return {"id": id_}

    @app.patch("/api/trabajos/{id_}")
    async def trabajo_cambiar(id_: str, request: Request):
        usuario(request)
        t = _existe("trabajos", id_)
        if t["estado"] in {"en_cola", "trabajando"}:
            raise error(409, "Este video se está creando: espera a que termine o cancélalo.")
        cuerpo = await _json(request)
        cambios: dict = {"actualizado": datos.ahora()}
        if "prompt" in cuerpo:
            cambios["prompt"] = str(cuerpo["prompt"])[:4000]
        if "titulo" in cuerpo:
            cambios["titulo"] = str(cuerpo["titulo"]).strip()[:80] or t["titulo"]
        if "marca" in cuerpo:
            cambios["marca"] = _marca_valida(cuerpo["marca"])
        if "opciones" in cuerpo and isinstance(cuerpo["opciones"], dict):
            permitidas = {"formato", "quitar_pausas", "acercamientos", "insignias", "contadores", "cierre", "color_referencias", "idioma", "calidad", "musica", "acabado", "ia"}
            cambios["opciones"] = {k: v for k, v in cuerpo["opciones"].items() if k in permitidas}
        datos.actualizar("trabajos", id_, cambios)
        return {"ok": True}

    @app.put("/api/trabajos/{id_}/video")
    async def trabajo_video(id_: str, request: Request, nombre: str = "video.mp4"):
        usuario(request)
        t = _existe("trabajos", id_)
        if t["estado"] in {"en_cola", "trabajando"}:
            raise error(409, "Este video se está creando: espera a que termine.")
        base = produccion.carpeta_de_trabajo(id_)
        ruta = await _guardar_video(request, base / "fuente", nombre)
        sonda = _sondear(ruta)
        miniatura = base / "miniatura.jpg"
        produccion._miniatura(ruta, miniatura, min(1.0, sonda["duracion"] / 3))
        datos.actualizar("trabajos", id_, {"fuente_archivo": str(ruta.relative_to(datos.DATOS)), "fuente_nombre": nombre[:120], "fuente_duracion": sonda["duracion"], "fuente_vertical": 1 if sonda["vertical"] else 0,
                                           "estado": "borrador", "error": None, "mensaje": None, "resultado": None, "actualizado": datos.ahora()})
        return {"duracion": sonda["duracion"]}

    @app.delete("/api/trabajos/{id_}")
    def trabajo_borrar(id_: str, request: Request):
        usuario(request)
        _existe("trabajos", id_)
        produccion.cancelar(id_)
        _borrar_trabajo(id_)
        return {"ok": True}

    @app.post("/api/trabajos/{id_}/crear")
    def trabajo_crear(id_: str, request: Request):
        usuario(request)
        t = _existe("trabajos", id_)
        if t["estado"] in {"en_cola", "trabajando"}:
            raise error(409, "Este video ya se está creando.")
        if not t["fuente_archivo"]:
            raise error(422, "Sube primero el video que quieres editar.")
        activas = [r["id"] for r in datos.todos("SELECT id FROM referencias WHERE activa = 1 AND estado = 'lista'")]
        datos.actualizar("trabajos", id_, {"estado": "en_cola", "etapa": "En espera", "progreso": 0, "error": None, "mensaje": "Esperando su turno", "referencias": activas,
                                           "resultado": None, "fotogramas_listos": 0, "fotogramas_total": 0, "eta": None, "actualizado": datos.ahora()})
        produccion.encolar("trabajo", id_)
        return {"ok": True}

    @app.post("/api/trabajos/{id_}/cancelar")
    def trabajo_cancelar(id_: str, request: Request):
        usuario(request)
        t = _existe("trabajos", id_)
        if t["estado"] not in {"en_cola", "trabajando"}:
            return {"ok": True}
        produccion.cancelar(id_)
        if t["estado"] == "en_cola":
            datos.actualizar("trabajos", id_, {"estado": "cancelado", "etapa": None, "mensaje": "Cancelaste este video.", "actualizado": datos.ahora()})
        return {"ok": True}

    @app.get("/api/trabajos/{id_}/fotograma")
    def trabajo_fotograma(id_: str, request: Request, n: int = 0):
        usuario(request)
        t = _existe("trabajos", id_)
        fotos = produccion.carpeta_de_trabajo(_id(id_)) / "fotos"
        total = max(1, t["fotogramas_total"] or 1)
        n = max(0, min(int(n), total - 1))
        for digitos in range(len(str(total - 1)), 7):
            ruta = fotos / f"element-{n:0{digitos}d}.jpeg"
            if ruta.exists():
                return _archivo(ruta, "image/jpeg", cache="no-store")
        raise error(404, "Ese fotograma todavía no está listo.")

    @app.get("/api/trabajos/{id_}/miniatura")
    def trabajo_miniatura(id_: str, request: Request):
        usuario(request)
        return _archivo(produccion.carpeta_de_trabajo(_id(id_)) / "miniatura.jpg", "image/jpeg")

    @app.get("/api/trabajos/{id_}/resultado")
    def trabajo_resultado(id_: str, request: Request, descargar: int = 0):
        usuario(request)
        t = _existe("trabajos", id_)
        ruta = produccion.carpeta_de_trabajo(_id(id_)) / "resultado.mp4"
        if not t["resultado"] or not ruta.exists():
            raise error(404, "Este video todavía no está listo.")
        nombre = (comun.seguro(t["titulo"] or "video") or "video") + ".mp4"
        return FileResponse(ruta, media_type="video/mp4", filename=nombre if descargar else None, headers={"Cache-Control": "no-store"})

    manejar_errores(app)
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app


# ------------------------------------------------------------------------------------------------------ ayudantes

async def _json(request: Request) -> dict:
    try:
        cuerpo = await request.json()
    except ValueError:
        raise error(400, "No entendí la petición.")
    if not isinstance(cuerpo, dict):
        raise error(400, "No entendí la petición.")
    return cuerpo


def _id(valor: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{12}", valor):
        raise error(404, "No existe.")
    return valor


def _existe(tabla: str, id_: str) -> dict:
    fila = datos.uno(f"SELECT * FROM {tabla} WHERE id = ?", (_id(id_),))
    if fila is None:
        raise error(404, "No existe.")
    return fila


def _marca_valida(marca) -> str | None:
    if not marca:
        return None
    return marca if isinstance(marca, str) and marca != produccion.NEUTRA and (comun.EMPRESAS / marca).is_dir() and "/" not in marca else None


def _direccion_publica(plan: dict | None) -> dict | None:
    """Lo que el director decidió, para contárselo a la persona (sin los tiempos internos)."""
    if not plan:
        return None
    return {"origen": plan.get("origen"), "resumen": plan["concepto"]["resumen"], "tono": plan["concepto"]["tono"], "tipo_de_gancho": plan["concepto"]["tipo_de_gancho"],
            "gancho": plan["gancho"]["texto"], "alternativas": plan["gancho"]["alternativas"], "alertas": plan.get("alertas", []),
            "look": plan["acabado"]["look"], "advertencias": plan.get("advertencias_ia", [])}


def _musica_de_trabajo(id_: str | None) -> dict | None:
    if not id_:
        return None
    m = datos.uno("SELECT titulo, licencia, analisis FROM musica WHERE id = ?", (id_,))
    if not m:
        return None
    a = m["analisis"] or {}
    return {"titulo": m["titulo"], "licencia": m["licencia"], "bpm": a.get("bpm"), "confianza": a.get("confianza")}


def _titulo_de(nombre: str) -> str:
    return re.sub(r"[_\-]+", " ", Path(nombre).stem).strip()[:80] or "Referencia"


def _archivo(ruta: Path, tipo: str, cache: str = "private, max-age=3600") -> FileResponse:
    if not ruta.exists():
        raise error(404, "No existe.")
    return FileResponse(ruta, media_type=tipo, headers={"Cache-Control": cache})


def _sugerencias(config: dict, opciones: dict) -> list[dict]:
    """Cosas que el texto pide y los interruptores todavía no tienen: se ofrecen como botón, no se aplican solas."""
    etiquetas = {"quitar_pausas": "Quitar pausas largas", "formato": "Formato «Antes y después»", "musica": "Poner música de fondo"}
    salida = []
    for clave, valor in config["sugerencias"].items():
        actual = opciones.get(clave, True) if clave == "musica" else opciones.get(clave)
        if clave == "musica" and valor is False:
            etiquetas["musica"] = "Quitar la música"
        if actual != valor and not (clave == "formato" and (actual or "subtitulos") == valor):
            salida.append({"clave": clave, "valor": valor, "texto": etiquetas.get(clave, clave)})
    return salida


def _sondear(ruta: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", str(ruta)], capture_output=True, text=True)
    vertical = True
    try:
        info = json.loads(r.stdout or "{}")
        duracion = float(info.get("format", {}).get("duration", 0))
        videos = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
        hay_video = bool(videos)
        if videos and videos[0].get("width") and videos[0].get("height"):
            vertical = videos[0]["height"] >= videos[0]["width"]
    except (ValueError, TypeError):
        duracion, hay_video = 0.0, False
    if not hay_video or duracion <= 0:
        ruta.unlink(missing_ok=True)
        raise error(422, "Ese archivo no es un video que pueda leer. Prueba con MP4 o MOV.")
    if duracion > MAX_MINUTOS * 60:
        ruta.unlink(missing_ok=True)
        raise error(413, f"El video dura más de {MAX_MINUTOS} minutos. Por ahora recórtalo antes de subirlo.")
    return {"duracion": round(duracion, 2), "vertical": vertical}


async def _guardar_video(request: Request, destino_sin_extension: Path, nombre: str) -> Path:
    return await _guardar_archivo(request, destino_sin_extension, nombre, EXTENSIONES, MAX_BYTES,
                                  "Ese tipo de archivo no es un video compatible. Usa MP4, MOV, M4V, WEBM o MKV.")


async def _guardar_archivo(request: Request, destino_sin_extension: Path, nombre: str, extensiones: set[str], maximo: int, mensaje_tipo: str) -> Path:
    """Recibe un archivo como flujo, lo escribe a disco por partes y respeta el tamaño máximo."""
    extension = Path(nombre).suffix.lower()
    if extension not in extensiones:
        raise error(415, mensaje_tipo)
    destino = destino_sin_extension.with_suffix(extension)
    destino.parent.mkdir(parents=True, exist_ok=True)
    for viejo in destino.parent.glob(destino.stem + ".*"):
        viejo.unlink(missing_ok=True)
    temporal = destino.with_suffix(destino.suffix + ".parte")
    escrito = 0
    try:
        with open(temporal, "wb") as salida:
            async for pedazo in request.stream():
                escrito += len(pedazo)
                if escrito > maximo:
                    raise error(413, f"El archivo pesa más de {maximo // 1024**2} MB." if maximo < 1024**3 else f"El archivo pesa más de {maximo // 1024**3} GB.")
                salida.write(pedazo)
        if escrito == 0:
            raise error(422, "El archivo llegó vacío.")
        os.replace(temporal, destino)
    finally:
        temporal.unlink(missing_ok=True)
    return destino


def _borrar_trabajo(id_: str) -> None:
    shutil.rmtree(produccion.carpeta_de_trabajo(id_), ignore_errors=True)
    datos.ejecutar("DELETE FROM trabajos WHERE id = ?", (id_,))


def _borrar_referencia(id_: str) -> None:
    shutil.rmtree(produccion.carpeta_de_referencia(id_), ignore_errors=True)
    datos.ejecutar("DELETE FROM referencias WHERE id = ?", (id_,))


def manejar_errores(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _(request: Request, exc: HTTPException):
        detalle = exc.detail if isinstance(exc.detail, dict) else {"mensaje": str(exc.detail)}
        return JSONResponse(detalle, status_code=exc.status_code, headers=getattr(exc, "headers", None))
