"""Arranque de Iris desde la Terminal y gestión de cuentas (restablecer contraseña, listar)."""
from __future__ import annotations

import getpass
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

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


def _elegir_puerto(puerto: int | None = None) -> tuple[int | None, bool]:
    """(puerto, ya_abierta). Si Iris ya está abierta en uno de los puertos, devuelve ese; si ninguno sirve, (None, False)."""
    elegido = puerto or PUERTO_BASE
    for candidato in range(elegido, elegido + 11):
        if not _ocupado(candidato):
            return candidato, False
        if _es_iris(candidato):
            return candidato, True
    return None, False


def iniciar(abrir_navegador: bool = True, puerto: int | None = None) -> int:
    try:
        import uvicorn
        from .principal import crear_app
    except ImportError as error:
        print(f"Falta un componente de Iris ({error.name}). Ejecuta ./instalar.sh para instalarlo.")
        return 1

    elegido, ya_abierta = _elegir_puerto(puerto)
    if elegido is None:
        print(f"Los puertos {puerto or PUERTO_BASE}–{(puerto or PUERTO_BASE) + 10} están ocupados. Cierra otros programas e inténtalo de nuevo.")
        return 1
    if ya_abierta:
        print(f"Iris ya está abierta en http://127.0.0.1:{elegido}")
        if abrir_navegador:
            webbrowser.open(f"http://127.0.0.1:{elegido}")
        return 0

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


# ------------------------------------------------------------------------------------------------------------------
# Celular por cable
# ------------------------------------------------------------------------------------------------------------------

def _buscar_adb() -> str | None:
    candidatos = [shutil.which("adb"), str(Path.home() / "Library/Android/sdk/platform-tools/adb"), "/opt/homebrew/bin/adb", "/usr/local/bin/adb"]
    return next((c for c in candidatos if c and os.access(c, os.X_OK)), None)


def _dispositivos(adb: str) -> tuple[list[str], list[str]]:
    """(listos, sin autorizar) según `adb devices`."""
    salida = subprocess.run([adb, "devices"], capture_output=True, text=True).stdout
    listos, sin = [], []
    for linea in salida.splitlines()[1:]:
        partes = linea.split()
        if len(partes) >= 2:
            (listos if partes[1] == "device" else sin if partes[1] == "unauthorized" else []).append(partes[0])
    return listos, sin


def celular(serie: str | None = None, abrir_servidor: bool = True) -> int:
    """Pasa Iris a un celular Android conectado por cable. Usa `adb reverse`: el teléfono ve el servidor de tu computador como si fuera suyo
    (127.0.0.1), así que Iris sigue escuchando solo en tu computador y nada se expone a la red."""
    adb = _buscar_adb()
    if adb is None:
        print("Para pasar Iris a un celular Android por cable hace falta «adb» (las herramientas de Android).\n"
              "  1. Instálalo:  brew install --cask android-platform-tools\n"
              "  2. En el celular: Ajustes → Acerca del teléfono → toca 7 veces «Número de compilación»;\n"
              "     luego Ajustes → Opciones de desarrollador → activa «Depuración por USB».\n"
              "  3. Conecta el cable, acepta el aviso en el celular y repite:  ./creador celular\n"
              "Con un iPhone no hay un equivalente por cable que mantenga Iris solo en tu computador: dímelo y preparamos otra vía.")
        return 1
    listos, sin = _dispositivos(adb)
    if not listos:
        print("No veo ningún celular listo." + (" Hay uno esperando permiso: mira la pantalla del celular y pulsa «Permitir» en el aviso de depuración por USB." if sin
                                                else " Conéctalo por cable, activa «Depuración por USB» (Opciones de desarrollador) y vuelve a probar."))
        return 1
    if serie is None and len(listos) > 1:
        print("Hay varios celulares conectados: " + ", ".join(listos) + ". Desconecta los que sobren y vuelve a probar.")
        return 1
    destino = serie or listos[0]
    puerto, ya_abierta = _elegir_puerto()
    if puerto is None:
        print("No encuentro un puerto libre para Iris. Cierra otros programas e inténtalo de nuevo.")
        return 1
    base = [adb, "-s", destino]
    reverso = subprocess.run(base + ["reverse", f"tcp:{puerto}", f"tcp:{puerto}"], capture_output=True, text=True)
    if reverso.returncode != 0:
        print("No pude conectar el celular con tu computador: " + (reverso.stderr.strip() or reverso.stdout.strip() or "error desconocido"))
        return 1
    direccion = f"http://127.0.0.1:{puerto}"
    subprocess.run(base + ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", direccion], capture_output=True, text=True)
    print(f"Listo: el celular ({destino}) abrió {direccion}, que en realidad es Iris en tu computador (por el cable).")
    print("En Chrome del celular puedes usar el menú ⋮ → «Añadir a la pantalla de inicio» para tenerla como una app.")
    if not abrir_servidor:
        return 0
    if ya_abierta:
        print("Iris ya estaba abierta en tu computador: dejé el celular conectado a ella.")
        return 0
    print("Mantén esta ventana abierta mientras uses el celular. Control + C la cierra.")
    try:
        return iniciar(abrir_navegador=False, puerto=puerto)
    finally:
        subprocess.run(base + ["reverse", "--remove", f"tcp:{puerto}"], capture_output=True, text=True)


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
