"""Contraseñas, sesiones, límite de intentos y comprobaciones de origen."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from urllib.parse import urlsplit

from . import datos

VERSION_POLITICAS = "2026-10-24"  # cambia cuando cambian los textos legales: así se vuelve a pedir la aceptación
SESION_RECORDADA = 30 * 24 * 3600
SESION_CORTA = 12 * 3600
VENTANA_INTENTOS = 15 * 60
MAX_INTENTOS_CORREO = 5
MAX_INTENTOS_IP = 30
CORREO = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
COMUNES = {"12345678", "123456789", "1234567890", "password", "password1", "contrasena", "contraseña", "qwertyui", "qwerty123",
           "iloveyou", "11111111", "00000000", "abc12345", "admin123", "letmein1", "bienvenido", "12341234", "87654321"}
# Contraseña falsa: se calcula igual cuando el correo no existe para que no se note por el tiempo de respuesta.
_SAL_FALSA = b"\x00" * 16


def _scrypt(contrasena: str, sal: bytes) -> bytes:
    return hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, n=2**14, r=8, p=1, maxmem=64 * 1024 * 1024, dklen=32)


def crear_clave(contrasena: str) -> tuple[bytes, bytes]:
    sal = secrets.token_bytes(16)
    return sal, _scrypt(contrasena, sal)


def verificar_clave(contrasena: str, sal: bytes | None, clave: bytes | None) -> bool:
    calculada = _scrypt(contrasena, sal or _SAL_FALSA)
    return sal is not None and clave is not None and hmac.compare_digest(calculada, clave)


def validar_registro(correo: str, nombre: str, contrasena: str) -> dict[str, str]:
    """Errores por campo, en lenguaje claro; vacío si todo está bien."""
    errores: dict[str, str] = {}
    if not CORREO.match(correo) or len(correo) > 254:
        errores["correo"] = "Escribe un correo válido, por ejemplo ana@empresa.com."
    if not 1 <= len(nombre.strip()) <= 60:
        errores["nombre"] = "Escribe tu nombre (hasta 60 letras)."
    if len(contrasena) < 8:
        errores["contrasena"] = "Usa al menos 8 caracteres."
    elif len(contrasena) > 128:
        errores["contrasena"] = "Usa como máximo 128 caracteres."
    elif contrasena.lower() in COMUNES or contrasena.lower() == correo.lower():
        errores["contrasena"] = "Esa contraseña es muy común. Elige otra más difícil de adivinar."
    return errores


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def crear_sesion(usuario_id: int, recordar: bool) -> tuple[str, int | None]:
    """Devuelve el token (solo viaja en la cookie) y su duración en segundos (None: hasta cerrar el navegador)."""
    token = secrets.token_urlsafe(32)
    duracion = SESION_RECORDADA if recordar else SESION_CORTA
    ahora = datos.ahora()
    datos.insertar("sesiones", {"token": _hash_token(token), "usuario_id": usuario_id, "creada": ahora, "expira": ahora + duracion})
    datos.ejecutar("DELETE FROM sesiones WHERE expira < ?", (ahora,))
    return token, (SESION_RECORDADA if recordar else None)


def usuario_de_token(token: str | None) -> dict | None:
    if not token:
        return None
    return datos.uno(
        "SELECT u.id, u.correo, u.nombre, u.acepto_version FROM sesiones s JOIN usuarios u ON u.id = s.usuario_id WHERE s.token = ? AND s.expira > ?",
        (_hash_token(token), datos.ahora()))


def cerrar_sesion(token: str | None) -> None:
    if token:
        datos.ejecutar("DELETE FROM sesiones WHERE token = ?", (_hash_token(token),))


def segundos_de_espera(clave: str, maximo: int) -> int:
    """0 si se puede intentar; si no, cuántos segundos faltan para el siguiente intento."""
    desde = datos.ahora() - VENTANA_INTENTOS
    filas = datos.todos("SELECT momento FROM intentos WHERE clave = ? AND momento > ? ORDER BY momento", (clave, desde))
    if len(filas) < maximo:
        return 0
    return max(1, int(filas[len(filas) - maximo]["momento"] + VENTANA_INTENTOS - datos.ahora()) + 1)


def anotar_fallo(clave: str) -> None:
    datos.insertar("intentos", {"clave": clave, "momento": datos.ahora()})
    datos.ejecutar("DELETE FROM intentos WHERE momento < ?", (datos.ahora() - VENTANA_INTENTOS,))


def borrar_fallos(clave: str) -> None:
    datos.ejecutar("DELETE FROM intentos WHERE clave = ?", (clave,))


def host_permitido(host: str | None, puerto: int, extra: frozenset | set = frozenset()) -> bool:
    """Solo se atiende a quien llega por localhost (o por el nombre exacto que Iris dio en el modo Wi-Fi): frena el «DNS rebinding»."""
    if not host:
        return False
    nombre, dos_puntos, resto = host.lower().partition(":")
    if dos_puntos and resto != str(puerto):
        return False
    return nombre in {"127.0.0.1", "localhost"} | set(extra)


def origen_permitido(origen: str | None, sitio: str | None, puerto: int, extra: frozenset | set = frozenset()) -> bool:
    """Peticiones que modifican datos: si vienen de un navegador, tienen que venir de esta misma página."""
    if sitio is not None and sitio not in {"same-origin", "none"}:
        return False
    if origen is None:
        return True
    partes = urlsplit(origen)
    return partes.scheme == "http" and (partes.hostname or "").lower() in {"127.0.0.1", "localhost"} | set(extra) and partes.port == puerto
