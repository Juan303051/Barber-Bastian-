"""Base de datos local (SQLite) de la app: personas, sesiones, referencias y trabajos."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

RAIZ_APP = Path(__file__).resolve().parent.parent
DATOS = Path(os.environ.get("IRIS_DATOS") or RAIZ_APP / "datos")

_candado = threading.RLock()
_conexion: sqlite3.Connection | None = None
_ruta_abierta: Path | None = None

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT, correo TEXT UNIQUE NOT NULL, nombre TEXT NOT NULL,
  sal BLOB NOT NULL, clave BLOB NOT NULL, creado REAL NOT NULL);
CREATE TABLE IF NOT EXISTS sesiones (
  token TEXT PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
  creada REAL NOT NULL, expira REAL NOT NULL);
CREATE TABLE IF NOT EXISTS intentos (clave TEXT NOT NULL, momento REAL NOT NULL);
CREATE INDEX IF NOT EXISTS ix_intentos ON intentos(clave, momento);
CREATE TABLE IF NOT EXISTS referencias (
  id TEXT PRIMARY KEY, usuario_id INTEGER, tipo TEXT NOT NULL, titulo TEXT NOT NULL, origen TEXT, archivo TEXT,
  estado TEXT NOT NULL, etapa TEXT, progreso REAL DEFAULT 0, error TEXT, perfil TEXT, activa INTEGER DEFAULT 1, creada REAL NOT NULL);
CREATE TABLE IF NOT EXISTS trabajos (
  id TEXT PRIMARY KEY, usuario_id INTEGER, marca TEXT, titulo TEXT, prompt TEXT DEFAULT '', opciones TEXT DEFAULT '{}',
  fuente_archivo TEXT, fuente_nombre TEXT, fuente_duracion REAL, estado TEXT NOT NULL, etapa TEXT, progreso REAL DEFAULT 0,
  mensaje TEXT, error TEXT, resultado TEXT, referencias TEXT DEFAULT '[]', fotogramas_total INTEGER DEFAULT 0,
  fotogramas_listos INTEGER DEFAULT 0, eta REAL, creado REAL NOT NULL, actualizado REAL NOT NULL, orden INTEGER DEFAULT 0, notas TEXT, fuente_vertical INTEGER DEFAULT 1,
  plan TEXT, calidad TEXT, musica_id TEXT, ia_info TEXT);
CREATE TABLE IF NOT EXISTS musica (
  id TEXT PRIMARY KEY, usuario_id INTEGER, titulo TEXT NOT NULL, archivo TEXT, estado TEXT NOT NULL, etapa TEXT, error TEXT,
  analisis TEXT, licencia TEXT DEFAULT 'sin-confirmar', activa INTEGER DEFAULT 1, creada REAL NOT NULL);
CREATE TABLE IF NOT EXISTS perfiles (marca TEXT PRIMARY KEY, datos TEXT NOT NULL, actualizado REAL NOT NULL);
"""

CAMPOS_JSON = {"opciones", "perfil", "referencias", "notas", "plan", "calidad", "ia_info", "analisis", "datos"}


def abrir() -> sqlite3.Connection:
    """Una sola conexión protegida por un candado; se vuelve a abrir si cambia la carpeta de datos (pruebas)."""
    global _conexion, _ruta_abierta
    with _candado:
        ruta = DATOS / "iris.db"
        if _conexion is None or _ruta_abierta != ruta:
            if _conexion is not None:
                _conexion.close()
            DATOS.mkdir(parents=True, exist_ok=True)
            _conexion = sqlite3.connect(ruta, check_same_thread=False, isolation_level=None)
            _conexion.row_factory = sqlite3.Row
            _conexion.execute("PRAGMA journal_mode=WAL")
            _conexion.execute("PRAGMA foreign_keys=ON")
            _conexion.executescript(ESQUEMA)
            _completar_columnas(_conexion)
            _ruta_abierta = ruta
        return _conexion


def _completar_columnas(conexion: sqlite3.Connection) -> None:
    """Si la base viene de una versión anterior, añade las columnas que le faltan en vez de fallar."""
    nuevas = {"notas": "TEXT", "fuente_vertical": "INTEGER DEFAULT 1", "plan": "TEXT", "calidad": "TEXT", "musica_id": "TEXT", "ia_info": "TEXT"}
    existentes = {f["name"] for f in conexion.execute("PRAGMA table_info(trabajos)").fetchall()}
    for columna, definicion in nuevas.items():
        if columna not in existentes:
            conexion.execute(f"ALTER TABLE trabajos ADD COLUMN {columna} {definicion}")


def cerrar() -> None:
    global _conexion, _ruta_abierta
    with _candado:
        if _conexion is not None:
            _conexion.close()
        _conexion, _ruta_abierta = None, None


def _fila(fila: sqlite3.Row | None) -> dict | None:
    if fila is None:
        return None
    datos = dict(fila)
    for campo in CAMPOS_JSON & datos.keys():
        datos[campo] = json.loads(datos[campo]) if datos[campo] else None
    return datos


def uno(sql: str, parametros: tuple = ()) -> dict | None:
    with _candado:
        return _fila(abrir().execute(sql, parametros).fetchone())


def todos(sql: str, parametros: tuple = ()) -> list[dict]:
    with _candado:
        return [_fila(f) for f in abrir().execute(sql, parametros).fetchall()]


def ejecutar(sql: str, parametros: tuple = ()) -> int:
    with _candado:
        return abrir().execute(sql, parametros).rowcount


def insertar(tabla: str, valores: dict) -> None:
    columnas = ", ".join(valores)
    marcas = ", ".join("?" for _ in valores)
    ejecutar(f"INSERT INTO {tabla} ({columnas}) VALUES ({marcas})", tuple(_serializar(k, v) for k, v in valores.items()))


def actualizar(tabla: str, id_: str | int, valores: dict) -> None:
    if not valores:
        return
    asignaciones = ", ".join(f"{k} = ?" for k in valores)
    ejecutar(f"UPDATE {tabla} SET {asignaciones} WHERE id = ?", tuple(_serializar(k, v) for k, v in valores.items()) + (id_,))


def _serializar(campo: str, valor):
    return json.dumps(valor, ensure_ascii=False) if campo in CAMPOS_JSON and valor is not None else valor


def ahora() -> float:
    return time.time()
