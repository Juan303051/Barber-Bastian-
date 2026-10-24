"""Servidor local de Iris: cuentas, referencias, trabajos y archivos. Solo escucha en este equipo."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import comun

from . import calidad, datos, escenas as unidor, formatos, interprete, produccion, seguridad
from .direccion import ia, perfil as perfiles

WEB = datos.RAIZ_APP / "web"
COOKIE = "iris_sesion"
EXTENSIONES = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
EXTENSIONES_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
EXTENSIONES_LOGO = produccion.EXTENSIONES_LOGO
MAX_BYTES_LOGO = 8 * 1024**2
TIPOS_AUDIO = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac", ".ogg": "audio/ogg", ".opus": "audio/ogg"}
MAX_BYTES_AUDIO = 300 * 1024**2
LICENCIAS = set(calidad.LICENCIAS)
MAX_BYTES = int(float(os.environ.get("IRIS_MAX_GB", "4")) * 1024**3)
MAX_MINUTOS = 45
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


PASO_DE = {texto: clave for clave, texto in produccion.ETAPAS.items()}


def _pasos_de(config: dict, n_escenas: int) -> list[dict]:
    return [{"clave": c, "texto": produccion.ETAPAS[c]} for c in produccion.pasos_de(config, n_escenas)]


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

    def usuario_publico(u: dict | None) -> dict | None:
        """Lo que el navegador puede saber de una cuenta (nunca claves ni cifrados)."""
        if u is None:
            return None
        return {"id": u["id"], "correo": u["correo"], "nombre": u["nombre"], "acepto": u.get("acepto_version") == seguridad.VERSION_POLITICAS}

    @app.get("/api/sesion")
    def sesion(request: Request):
        encontrado = seguridad.usuario_de_token(request.cookies.get(COOKIE))
        cuantos = datos.uno("SELECT COUNT(*) AS n FROM usuarios")["n"]
        return {"autenticado": encontrado is not None, "usuario": usuario_publico(encontrado), "primera_vez": cuantos == 0}

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
        if cuerpo.get("acepto") is not True:  # el consentimiento es una acción de la persona: nunca viene marcado de antemano
            errores["acepto"] = "Para crear la cuenta, acepta los términos y la política de privacidad."
        if errores:
            raise error(422, "Revisa los datos marcados.", campos=errores)
        if datos.uno("SELECT id FROM usuarios WHERE correo = ?", (correo,)):
            raise error(409, "Ya hay una cuenta con ese correo.", campos={"correo": "Ya hay una cuenta con ese correo."})
        sal, clave = seguridad.crear_clave(contrasena)
        datos.insertar("usuarios", {"correo": correo, "nombre": nombre, "sal": sal, "clave": clave, "creado": datos.ahora(),
                                    "acepto_version": seguridad.VERSION_POLITICAS, "acepto_en": datos.ahora()})
        nuevo = usuario_publico(datos.uno("SELECT id, correo, nombre, acepto_version FROM usuarios WHERE correo = ?", (correo,)))
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
        return {"usuario": usuario_publico(fila)}

    @app.post("/api/salir")
    def salir(request: Request, respuesta: Response):
        seguridad.cerrar_sesion(request.cookies.get(COOKIE))
        respuesta.delete_cookie(COOKIE, path="/")
        return {"ok": True}

    @app.post("/api/cuenta/aceptar")
    async def aceptar_politicas(request: Request):
        """Para cuentas anteriores a los textos legales: la persona acepta la versión actual."""
        yo = usuario(request)
        if (await _json(request)).get("acepto") is not True:
            raise error(422, "Para seguir usando Iris, acepta los términos y la política de privacidad.")
        datos.ejecutar("UPDATE usuarios SET acepto_version = ?, acepto_en = ? WHERE id = ?", (seguridad.VERSION_POLITICAS, datos.ahora(), yo["id"]))
        return {"ok": True}

    @app.get("/api/cuenta/exportar")
    def exportar_cuenta(request: Request):
        """Todo lo que Iris guarda de la persona, en un archivo que se puede leer: cuenta, videos (sin los archivos pesados), referencias, música y ajustes. Nunca la clave."""
        yo = usuario(request)
        fila = datos.uno("SELECT correo, nombre, creado, acepto_version, acepto_en FROM usuarios WHERE id = ?", (yo["id"],))
        ajustes = ia._leer_archivo()
        contenido = {
            "exportado_en": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version_de_los_textos": seguridad.VERSION_POLITICAS,
            "cuenta": {"correo": fila["correo"], "nombre": fila["nombre"], "creada": fila["creado"], "acepto_los_textos": fila["acepto_version"], "acepto_en": fila["acepto_en"]},
            "trabajos": [{"id": t["id"], "titulo": t["titulo"], "marca": t["marca"], "instrucciones": t["prompt"], "opciones": t["opciones"], "estado": t["estado"], "creado": t["creado"],
                          "escenas": [{"nombre": e["nombre"], "duracion": e["duracion"]} for e in produccion.escenas_de(t)], "notas": t["notas"], "calidad": t["calidad"],
                          "cumplimiento": t["cumplimiento"], "ia": t["ia_info"]} for t in datos.todos("SELECT * FROM trabajos WHERE usuario_id = ? ORDER BY creado", (yo["id"],))],
            "referencias": [{"titulo": r["titulo"], "tipo": r["tipo"], "origen": r["origen"], "estado": r["estado"], "perfil": r["perfil"], "creada": r["creada"]}
                            for r in datos.todos("SELECT * FROM referencias WHERE usuario_id = ? ORDER BY creada", (yo["id"],))],
            "musica": [{"titulo": m_["titulo"], "licencia_declarada": m_["licencia"], "analisis": {k: (m_["analisis"] or {}).get(k) for k in ("bpm", "ritmo", "intensidad", "duracion")}, "creada": m_["creada"]}
                       for m_ in datos.todos("SELECT * FROM musica WHERE usuario_id = ? ORDER BY creada", (yo["id"],))],
            "test_del_director": {(p["marca"] or "general"): p["datos"] for p in datos.todos("SELECT * FROM perfiles")},
            "ajustes_de_ia": {"activa": bool(ajustes.get("activa", True)), "modelo": ajustes.get("modelo"), "ver_fotogramas": bool(ajustes.get("ver_fotogramas", False)),
                              "consentimiento_envio_de_datos": ajustes.get("consentimiento_ia"), "hay_clave_guardada": bool(ajustes.get("clave"))},
            "archivos": "Tus videos, escenas, canciones y logos están en la carpeta de datos de Iris (app/datos/); no se incluyen aquí por su tamaño.",
        }
        return JSONResponse(contenido, headers={"Content-Disposition": 'attachment; filename="mis-datos-iris.json"', "Cache-Control": "no-store"})

    @app.delete("/api/cuenta")
    async def eliminar_cuenta(request: Request, respuesta: Response):
        yo = usuario(request)
        cuerpo = await _json(request)
        fila = datos.uno("SELECT * FROM usuarios WHERE id = ?", (yo["id"],))
        if not seguridad.verificar_clave(str(cuerpo.get("contrasena", "")), fila["sal"], fila["clave"]):
            raise error(403, "La contraseña no coincide.", campos={"contrasena": "La contraseña no coincide."})
        borrar_todo = bool(cuerpo.get("borrar_todo") or cuerpo.get("borrar_trabajos"))
        if borrar_todo:
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
        if borrar_todo and datos.uno("SELECT COUNT(*) AS n FROM usuarios")["n"] == 0:
            # Era la última cuenta: no queda nadie para quien guardar nada. Se borran también los logos, el test del director y la clave de la IA.
            shutil.rmtree(datos.DATOS / "marcas", ignore_errors=True)
            datos.ejecutar("DELETE FROM perfiles")
            ia._archivo().unlink(missing_ok=True)
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
            salida.append({"id": carpeta.name, "nombre": comun.nombre(carpeta), "acento": acento, "logo": _logo_de(carpeta.name) is not None})
        return salida

    # ----------------------------------------------------------------------------------------------- logo de la marca
    def marca_existente(marca: str) -> str:
        valida = _marca_valida(marca)
        if valida is None:
            raise error(404, "No existe esa marca.")
        return valida

    @app.put("/api/marcas/{marca}/logo")
    async def logo_subir(marca: str, request: Request, nombre: str = "logo.png", derechos: int = 0):
        usuario(request)
        marca = marca_existente(marca)
        if derechos != 1:
            raise error(422, "Confirma que tienes derecho a usar este logo (es tuyo o de la marca).")
        carpeta = datos.DATOS / "marcas" / marca
        ruta = await _guardar_archivo(request, carpeta / "logo", nombre, EXTENSIONES_LOGO, MAX_BYTES_LOGO, "El logo tiene que ser una imagen PNG, WEBP o JPG (mejor PNG con fondo transparente).")
        try:
            sonda = unidor.sondear_imagen(ruta)
        except ValueError:
            ruta.unlink(missing_ok=True)
            raise error(422, "Ese archivo no es una imagen que pueda leer. Prueba con un PNG.") from None
        for otro in carpeta.glob("logo.*"):
            if otro != ruta:
                otro.unlink(missing_ok=True)
        return {"ok": True, "ancho": sonda["ancho"], "alto": sonda["alto"], "transparente": sonda["transparente"]}

    @app.delete("/api/marcas/{marca}/logo")
    def logo_borrar(marca: str, request: Request):
        usuario(request)
        marca = marca_existente(marca)
        logo = _logo_de(marca)
        if logo is not None:
            logo.unlink(missing_ok=True)
        return {"ok": True}

    @app.get("/api/marcas/{marca}/logo")
    def logo_ver(marca: str, request: Request):
        usuario(request)
        logo = _logo_de(marca_existente(marca))
        if logo is None:
            raise error(404, "Esta marca no tiene logo.")
        return _archivo(logo, {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}[logo.suffix.lower()], cache="no-store")

    def publica_referencia(r: dict) -> dict:
        tiene = (produccion.carpeta_de_referencia(r["id"]) / "miniatura.jpg").exists()
        return {"id": r["id"], "tipo": r["tipo"], "titulo": r["titulo"], "origen": r["origen"], "estado": r["estado"], "etapa": r["etapa"],
                "progreso": r["progreso"], "error": r["error"], "perfil": r["perfil"], "activa": bool(r["activa"]), "miniatura": tiene}

    def publico_trabajo(t: dict) -> dict:
        base = produccion.carpeta_de_trabajo(t["id"])
        if t["estado"] == "listo" and not (base / "resultado.mp4").exists():  # alguien borró el archivo a mano: se avisa en vez de mostrar un video roto
            t = {**t, "estado": "interrumpido", "resultado": None, "mensaje": "El video ya no está en este equipo. Puedes volver a crearlo."}
        config = interprete.efectivo(t["prompt"] or "", t["opciones"] or {})
        lista = produccion.escenas_de(t)
        return {"id": t["id"], "marca": t["marca"], "titulo": t["titulo"], "prompt": t["prompt"], "opciones": t["opciones"] or {},
                "escenas": [{"id": e["id"], "nombre": e["nombre"], "duracion": e["duracion"], "vertical": bool(e.get("vertical", True))} for e in lista],
                "efectivo": _efectivo_publico(config), "tiene_logo": bool(_logo_de(t["marca"])), "menores_marca": _marca_con_menores(t["marca"]),
                "fuente_nombre": t["fuente_nombre"], "fuente_duracion": t["fuente_duracion"], "vertical": bool(t["fuente_vertical"]), "estado": t["estado"], "etapa": t["etapa"],
                "progreso": t["progreso"], "mensaje": t["mensaje"], "error": t["error"], "resultado": bool(t["resultado"]),
                "fotogramas_total": t["fotogramas_total"], "fotogramas_listos": t["fotogramas_listos"], "eta": t["eta"],
                "miniatura": (base / "miniatura.jpg").exists(), "entendido": interprete.resumen(config, bool(_logo_de(t["marca"]))), "pendiente": config["pendiente"],
                "actualizado": t["actualizado"], "notas": t["notas"] or [],
                "pasos": _pasos_de(config, len(lista)), "paso": PASO_DE.get(t["etapa"]) or ("cola" if t["estado"] == "en_cola" else None),
                "calidad": t["calidad"], "ia": t["ia_info"], "direccion": _direccion_publica(t["plan"]), "musica": _musica_de_trabajo(t["musica_id"]),
                "cumplimiento": t["cumplimiento"] or []}

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
        return {"referencias": referencias, "trabajos": trabajos, "musica": musica, "ia": ia.estado_publico(), "formatos": formatos.publicos()}

    @app.post("/api/interpretar")
    async def interpretar(request: Request):
        usuario(request)
        cuerpo = await _json(request)
        config = interprete.efectivo(str(cuerpo.get("prompt", ""))[:4000], cuerpo.get("opciones") if isinstance(cuerpo.get("opciones"), dict) else {})
        marca = _marca_valida(cuerpo.get("marca"))
        return {"entendido": interprete.resumen(config, bool(_logo_de(marca))), "pendiente": config["pendiente"], "efectivo": _efectivo_publico(config)}

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
        cambios = {k: cuerpo[k] for k in ("activa", "ver_fotogramas", "modelo", "clave", "consentimiento") if k in cuerpo}
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
            cambios["opciones"] = _opciones_validas(cuerpo["opciones"])
        datos.actualizar("trabajos", id_, cambios)
        return {"ok": True}

    @app.put("/api/trabajos/{id_}/escenas")
    async def escena_subir(id_: str, request: Request, nombre: str = "escena.mp4"):
        usuario(request)
        t = _existe("trabajos", id_)
        _sin_trabajo_activo(t)
        lista = list(produccion.escenas_de(t))
        if len(lista) >= unidor.MAX_ESCENAS:
            raise error(422, f"Un video admite hasta {unidor.MAX_ESCENAS} escenas.")
        escena = await _guardar_escena(id_, request, nombre, sum(e["duracion"] for e in lista))
        lista.append(escena)
        _guardar_escenas(id_, lista)
        return {"escena": {"id": escena["id"], "nombre": escena["nombre"], "duracion": escena["duracion"]}, "total": round(sum(e["duracion"] for e in lista), 2)}

    @app.put("/api/trabajos/{id_}/video")
    async def trabajo_video(id_: str, request: Request, nombre: str = "video.mp4"):
        """Compatibilidad: sube un video como única escena (reemplaza las que hubiera)."""
        usuario(request)
        t = _existe("trabajos", id_)
        _sin_trabajo_activo(t)
        escena = await _guardar_escena(id_, request, nombre, 0.0)
        for vieja in produccion.escenas_de(t):
            _borrar_archivos_de_escena(id_, vieja)
        _guardar_escenas(id_, [escena])
        return {"duracion": escena["duracion"]}

    @app.patch("/api/trabajos/{id_}/escenas")
    async def escenas_ordenar(id_: str, request: Request):
        usuario(request)
        t = _existe("trabajos", id_)
        _sin_trabajo_activo(t)
        lista = produccion.escenas_de(t)
        orden = (await _json(request)).get("orden")
        if not isinstance(orden, list) or sorted(map(str, orden)) != sorted(e["id"] for e in lista):
            raise error(422, "El orden no coincide con las escenas de este video.")
        por_id = {e["id"]: e for e in lista}
        _guardar_escenas(id_, [por_id[str(i)] for i in orden], conservar_resultado=True)
        return {"ok": True}

    @app.delete("/api/trabajos/{id_}/escenas/{sid}")
    def escena_borrar(id_: str, sid: str, request: Request):
        usuario(request)
        t = _existe("trabajos", id_)
        _sin_trabajo_activo(t)
        lista = produccion.escenas_de(t)
        quitada = next((e for e in lista if e["id"] == sid), None)
        if quitada is None:
            raise error(404, "No existe esa escena.")
        _borrar_archivos_de_escena(id_, quitada)
        _guardar_escenas(id_, [e for e in lista if e["id"] != sid])
        return {"ok": True}

    @app.get("/api/trabajos/{id_}/escenas/{sid}/miniatura")
    def escena_miniatura(id_: str, sid: str, request: Request):
        usuario(request)
        _existe("trabajos", id_)
        if not re.fullmatch(r"[0-9a-f]{12}|unica", sid):
            raise error(404, "No existe.")
        base = produccion.carpeta_de_trabajo(_id(id_))
        ruta = base / "escenas" / f"{sid}.jpg"
        return _archivo(ruta if ruta.exists() or sid != "unica" else base / "miniatura.jpg", "image/jpeg")

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
        if not produccion.escenas_de(t):
            raise error(422, "Sube primero el video que quieres editar.")
        activas = [r["id"] for r in datos.todos("SELECT id FROM referencias WHERE activa = 1 AND estado = 'lista'")]
        datos.actualizar("trabajos", id_, {"estado": "en_cola", "etapa": "En espera", "progreso": 0, "error": None, "mensaje": "Esperando su turno", "referencias": activas,
                                           "resultado": None, "fotogramas_listos": 0, "fotogramas_total": 0, "eta": None, "actualizado": datos.ahora()})
        produccion.encolar("trabajo", id_)
        return {"ok": True}

    @app.post("/api/trabajos/{id_}/permiso-menores")
    async def permiso_menores(id_: str, request: Request):
        """La persona confirma que tiene la autorización de los padres. Se guarda y el informe de calidad se actualiza sin volver a crear el video."""
        usuario(request)
        t = _existe("trabajos", id_)
        confirmo = bool((await _json(request)).get("confirmo"))
        opciones = dict(t["opciones"] or {"_v": interprete.VERSION_OPCIONES})
        opciones["permiso_menores"] = confirmo
        cambios: dict = {"opciones": opciones}
        if confirmo and t["calidad"]:
            cambios["calidad"] = calidad.confirmar_menores(t["calidad"])
        datos.actualizar("trabajos", id_, cambios)
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


def _sondear(ruta: Path, ya_subido: float = 0.0) -> dict:
    """Lee el video recién subido; si no es un video o sumado a lo anterior pasa del límite, lo borra y avisa."""
    try:
        sonda = unidor.sondear(ruta)
    except ValueError:
        ruta.unlink(missing_ok=True)
        raise error(422, "Ese archivo no es un video que pueda leer. Prueba con MP4 o MOV.") from None
    if sonda["duracion"] + ya_subido > MAX_MINUTOS * 60:
        ruta.unlink(missing_ok=True)
        raise error(413, f"Entre todas las escenas pasan de {MAX_MINUTOS} minutos. Por ahora recórtalas antes de subirlas.")
    return sonda


def _sin_trabajo_activo(t: dict) -> None:
    if t["estado"] in {"en_cola", "trabajando"}:
        raise error(409, "Este video se está creando: espera a que termine o cancélalo.")


async def _guardar_escena(id_: str, request: Request, nombre: str, ya_subido: float) -> dict:
    """Guarda una escena subida, la lee y le saca la miniatura. Devuelve su registro."""
    sid = uuid.uuid4().hex[:12]
    base = produccion.carpeta_de_trabajo(id_)
    ruta = await _guardar_video(request, base / "fuente" / sid, nombre)
    sonda = _sondear(ruta, ya_subido)
    miniatura = base / "escenas" / f"{sid}.jpg"
    miniatura.parent.mkdir(parents=True, exist_ok=True)
    produccion._miniatura(ruta, miniatura, min(1.0, sonda["duracion"] / 3))
    return {"id": sid, "archivo": str(ruta.relative_to(datos.DATOS)), "nombre": nombre[:120], "duracion": sonda["duracion"], "vertical": sonda["vertical"],
            "ancho": sonda["ancho"], "alto": sonda["alto"], "audio": sonda["audio"]}


def _borrar_archivos_de_escena(id_: str, escena: dict) -> None:
    (datos.DATOS / escena["archivo"]).unlink(missing_ok=True)
    (produccion.carpeta_de_trabajo(id_) / "escenas" / f"{escena['id']}.jpg").unlink(missing_ok=True)


def _guardar_escenas(id_: str, lista: list[dict], conservar_resultado: bool = False) -> None:
    """Guarda la lista de escenas y el resumen que usan el resto de pantallas (nombre, duración total, orientación, miniatura del video)."""
    base = produccion.carpeta_de_trabajo(id_)
    cambios: dict = {"escenas": lista, "actualizado": datos.ahora(), "fuente_archivo": lista[0]["archivo"] if lista else None,
                     "fuente_nombre": (lista[0]["nombre"] if len(lista) == 1 else f"{len(lista)} escenas") if lista else None,
                     "fuente_duracion": round(sum(e["duracion"] for e in lista), 2) if lista else None, "fuente_vertical": 1 if (lista[0]["vertical"] if lista else True) else 0}
    if not conservar_resultado:
        cambios.update(estado="borrador", error=None, mensaje=None, resultado=None)
    datos.actualizar("trabajos", id_, cambios)
    primera = base / "escenas" / f"{lista[0]['id']}.jpg" if lista else None
    if primera is not None and primera.exists():
        shutil.copyfile(primera, base / "miniatura.jpg")
    elif not lista:
        (base / "miniatura.jpg").unlink(missing_ok=True)


def _opciones_validas(opciones: dict) -> dict:
    """Solo se guardan las opciones conocidas y con el tipo correcto; lo demás se descarta."""
    limpias: dict = {"_v": interprete.VERSION_OPCIONES}
    for clave in interprete.INTERRUPTORES:
        if isinstance(opciones.get(clave), bool):
            limpias[clave] = opciones[clave]
    if isinstance(opciones.get("permiso_menores"), bool):
        limpias["permiso_menores"] = opciones["permiso_menores"]
    if opciones.get("formato") in formatos.FORMATOS:
        limpias["formato"] = opciones["formato"]
    if opciones.get("calidad") in ("borrador", "completa"):
        limpias["calidad"] = opciones["calidad"]
    if opciones.get("acabado") in ("auto", "ninguno", "natural", "calido", "frio", "cine", "vibrante"):
        limpias["acabado"] = opciones["acabado"]
    if opciones.get("idioma") in ("es", "en", "pt"):
        limpias["idioma"] = opciones["idioma"]
    return limpias


def _efectivo_publico(config: dict) -> dict:
    """Lo que la pantalla muestra en cada interruptor: el valor que tendrá y de dónde sale («tu texto», «formato», o lo decide el director)."""
    claves = ("quitar_pausas", "acercamientos", "insignias", "contadores", "cierre", "color_referencias", "musica", "ia", "calculadora", "transiciones", "sonidos", "logo")
    return {"formato": config["formato"], "formato_origen": config["formato_origen"], "valores": {k: config[k] for k in claves}, "origenes": config["origenes"]}


def _marca_con_menores(marca: str | None) -> bool:
    """¿Esta marca habla a niños o de niños? Entonces se pide la casilla de autorización de los padres antes de crear."""
    if not marca:
        return False
    return calidad.hay_menores([], marca, produccion._ficha_de_marca(produccion.carpeta_de_marca(marca))[1])


def _logo_de(marca: str | None) -> Path | None:
    return produccion.logo_de(marca)


def _titulo_de(nombre: str) -> str:
    return re.sub(r"[_\-]+", " ", Path(nombre).stem).strip()[:80] or "Referencia"


def _archivo(ruta: Path, tipo: str, cache: str = "private, max-age=3600") -> FileResponse:
    if not ruta.exists():
        raise error(404, "No existe.")
    return FileResponse(ruta, media_type=tipo, headers={"Cache-Control": cache})


def _sondear(ruta: Path, ya_subido: float = 0.0) -> dict:
    """Lee el video recién subido; si no es un video o sumado a lo anterior pasa del límite, lo borra y avisa."""
    try:
        sonda = unidor.sondear(ruta)
    except ValueError:
        ruta.unlink(missing_ok=True)
        raise error(422, "Ese archivo no es un video que pueda leer. Prueba con MP4 o MOV.") from None
    if sonda["duracion"] + ya_subido > MAX_MINUTOS * 60:
        ruta.unlink(missing_ok=True)
        raise error(413, f"Entre todas las escenas pasan de {MAX_MINUTOS} minutos. Por ahora recórtalas antes de subirlas.")
    return sonda


def _sin_trabajo_activo(t: dict) -> None:
    if t["estado"] in {"en_cola", "trabajando"}:
        raise error(409, "Este video se está creando: espera a que termine o cancélalo.")


async def _guardar_escena(id_: str, request: Request, nombre: str, ya_subido: float) -> dict:
    """Guarda una escena subida, la lee y le saca la miniatura. Devuelve su registro."""
    sid = uuid.uuid4().hex[:12]
    base = produccion.carpeta_de_trabajo(id_)
    ruta = await _guardar_video(request, base / "fuente" / sid, nombre)
    sonda = _sondear(ruta, ya_subido)
    miniatura = base / "escenas" / f"{sid}.jpg"
    miniatura.parent.mkdir(parents=True, exist_ok=True)
    produccion._miniatura(ruta, miniatura, min(1.0, sonda["duracion"] / 3))
    return {"id": sid, "archivo": str(ruta.relative_to(datos.DATOS)), "nombre": nombre[:120], "duracion": sonda["duracion"], "vertical": sonda["vertical"],
            "ancho": sonda["ancho"], "alto": sonda["alto"], "audio": sonda["audio"]}


def _borrar_archivos_de_escena(id_: str, escena: dict) -> None:
    (datos.DATOS / escena["archivo"]).unlink(missing_ok=True)
    (produccion.carpeta_de_trabajo(id_) / "escenas" / f"{escena['id']}.jpg").unlink(missing_ok=True)


def _guardar_escenas(id_: str, lista: list[dict], conservar_resultado: bool = False) -> None:
    """Guarda la lista de escenas y el resumen que usan el resto de pantallas (nombre, duración total, orientación, miniatura del video)."""
    base = produccion.carpeta_de_trabajo(id_)
    cambios: dict = {"escenas": lista, "actualizado": datos.ahora(), "fuente_archivo": lista[0]["archivo"] if lista else None,
                     "fuente_nombre": (lista[0]["nombre"] if len(lista) == 1 else f"{len(lista)} escenas") if lista else None,
                     "fuente_duracion": round(sum(e["duracion"] for e in lista), 2) if lista else None, "fuente_vertical": 1 if (lista[0]["vertical"] if lista else True) else 0}
    if not conservar_resultado:
        cambios.update(estado="borrador", error=None, mensaje=None, resultado=None)
    datos.actualizar("trabajos", id_, cambios)
    primera = base / "escenas" / f"{lista[0]['id']}.jpg" if lista else None
    if primera is not None and primera.exists():
        shutil.copyfile(primera, base / "miniatura.jpg")
    elif not lista:
        (base / "miniatura.jpg").unlink(missing_ok=True)


def _opciones_validas(opciones: dict) -> dict:
    """Solo se guardan las opciones conocidas y con el tipo correcto; lo demás se descarta."""
    limpias: dict = {"_v": interprete.VERSION_OPCIONES}
    for clave in interprete.INTERRUPTORES:
        if isinstance(opciones.get(clave), bool):
            limpias[clave] = opciones[clave]
    if isinstance(opciones.get("permiso_menores"), bool):
        limpias["permiso_menores"] = opciones["permiso_menores"]
    if opciones.get("formato") in formatos.FORMATOS:
        limpias["formato"] = opciones["formato"]
    if opciones.get("calidad") in ("borrador", "completa"):
        limpias["calidad"] = opciones["calidad"]
    if opciones.get("acabado") in ("auto", "ninguno", "natural", "calido", "frio", "cine", "vibrante"):
        limpias["acabado"] = opciones["acabado"]
    if opciones.get("idioma") in ("es", "en", "pt"):
        limpias["idioma"] = opciones["idioma"]
    return limpias


def _efectivo_publico(config: dict) -> dict:
    """Lo que la pantalla muestra en cada interruptor: el valor que tendrá y de dónde sale («tu texto», «formato», o lo decide el director)."""
    claves = ("quitar_pausas", "acercamientos", "insignias", "contadores", "cierre", "color_referencias", "musica", "ia", "calculadora", "transiciones", "sonidos", "logo")
    return {"formato": config["formato"], "formato_origen": config["formato_origen"], "valores": {k: config[k] for k in claves}, "origenes": config["origenes"]}


def _logo_de(marca: str | None) -> Path | None:
    """Logo que la persona subió para esta marca (vive en la carpeta de datos, no en el repositorio)."""
    if not marca:
        return None
    carpeta = datos.DATOS / "marcas" / marca
    return next((p for p in sorted(carpeta.glob("logo.*")) if p.suffix.lower() in EXTENSIONES_LOGO), None) if carpeta.is_dir() else None


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
