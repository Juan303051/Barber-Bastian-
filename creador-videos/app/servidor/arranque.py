"""Arranque de Iris desde la Terminal y gestión de cuentas (restablecer contraseña, listar)."""
from __future__ import annotations

import getpass
import json
import socket
import sys
import threading
import time
import urllib.request
import webbrowser

from . import datos, produccion, seguridad

PUERTO_BASE = 8765


def _ocupado(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def _es_iris(puerto: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/sesion", timeout=1.5) as r:
            return "primera_vez" in json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return False


def iniciar(abrir_navegador: bool = True, puerto: int | None = None) -> int:
    try:
        import uvicorn
        from .principal import crear_app
    except ImportError as error:
        print(f"Falta un componente de Iris ({error.name}). Ejecuta ./instalar.sh para instalarlo.")
        return 1

    elegido = puerto or PUERTO_BASE
    for candidato in range(elegido, elegido + 11):
        if not _ocupado(candidato):
            elegido = candidato
            break
        if _es_iris(candidato):
            print(f"Iris ya está abierta en http://127.0.0.1:{candidato}")
            if abrir_navegador:
                webbrowser.open(f"http://127.0.0.1:{candidato}")
            return 0
    else:
        print(f"Los puertos {elegido}–{elegido + 10} están ocupados. Cierra otros programas e inténtalo de nuevo.")
        return 1

    direccion = f"http://127.0.0.1:{elegido}"
    app = crear_app(elegido)
    print(f"\nIris está lista en {direccion}")
    print("Déjala abierta mientras trabajas. Para cerrarla, pulsa Control + C en esta ventana.")
    print(f"Tus datos se guardan en {datos.DATOS}\n")
    if abrir_navegador:
        threading.Timer(1.2, lambda: webbrowser.open(direccion)).start()
    try:
        uvicorn.run(app, host="127.0.0.1", port=elegido, log_level="warning", access_log=False)
    except KeyboardInterrupt:
        pass
    finally:
        produccion.detener()
        datos.cerrar()
    print("\nIris se cerró. Lo que estaba creándose a medias se puede volver a crear la próxima vez.")
    return 0


def cuentas(accion: str | None, correo: str | None) -> int:
    datos.abrir()
    try:
        if accion in (None, "lista"):
            filas = datos.todos("SELECT correo, nombre, creado FROM usuarios ORDER BY creado")
            if not filas:
                print("Todavía no hay cuentas: se crea la primera al abrir Iris.")
            for f in filas:
                print(f"  {f['correo']}  ·  {f['nombre']}  ·  creada {time.strftime('%d/%m/%Y', time.localtime(f['creado']))}")
            return 0
        if accion == "restablecer":
            if not correo:
                print("Uso: ./creador cuenta restablecer tu@correo.com")
                return 2
            correo = correo.strip().lower()
            fila = datos.uno("SELECT id FROM usuarios WHERE correo = ?", (correo,))
            if not fila:
                print(f"No hay ninguna cuenta con el correo {correo}. Mira las que existen con:  ./creador cuenta lista")
                return 1
            nueva = getpass.getpass("Nueva contraseña (no se ve al escribir): ")
            repetida = getpass.getpass("Escríbela otra vez: ")
            if nueva != repetida:
                print("No coinciden. No se cambió nada.")
                return 1
            errores = seguridad.validar_registro(correo, "x", nueva)
            if "contrasena" in errores:
                print(errores["contrasena"])
                return 1
            sal, clave = seguridad.crear_clave(nueva)
            datos.ejecutar("UPDATE usuarios SET sal = ?, clave = ? WHERE id = ?", (sal, clave, fila["id"]))
            datos.ejecutar("DELETE FROM sesiones WHERE usuario_id = ?", (fila["id"],))
            datos.ejecutar("DELETE FROM intentos WHERE clave = ?", (f"correo:{correo}",))
            print("Listo. La contraseña cambió y se cerraron las sesiones abiertas de esa cuenta.")
            return 0
        print("Uso: ./creador cuenta lista   |   ./creador cuenta restablecer tu@correo.com")
        return 2
    finally:
        datos.cerrar()


if __name__ == "__main__":
    sys.exit(iniciar())
