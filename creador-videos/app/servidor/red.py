"""Modo opcional «iPhone por Wi-Fi» (`./creador iphone`): abre Iris a los aparatos de tu red de casa, con emparejamiento.

Por defecto Iris solo escucha en 127.0.0.1. Este modo existe porque un iPhone no puede usar el cable como el Android (`adb reverse`).
Lo que lo mantiene acotado:
- Solo se enciende si la persona lo pide con `./creador iphone` y lo confirma escribiendo SI; nunca queda activado de un día para otro.
- Escucha en 127.0.0.1 y en **una** dirección de la red local (no en todas las interfaces).
- Atiende solo a aparatos con dirección de red privada (192.168.x.x, 10.x.x.x, 172.16–31.x.x) y al nombre exacto de ese equipo (frena el «DNS rebinding»).
- Un aparato nuevo no ve nada de Iris hasta que escribe el código que aparece **en la Terminal del Mac**: 8 caracteres al azar, vence a los 10 minutos,
  sirve para 3 aparatos y se bloquea tras 5 fallos. Pulsar Enter en la Terminal da uno nuevo (y quita el bloqueo).
- Los aparatos emparejados viven solo en memoria y duran 12 horas: al cerrar Iris se pierden todos.
- El tráfico va por HTTP sin cifrar. Solo es razonable en una red de casa que controlas.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import secrets
import socket
import threading
import time

COOKIE = "iris_dispositivo"
ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin I, O, 0 ni 1: no se confunden al leerlos
LARGO_CODIGO = 8
VIDA_CODIGO = 10 * 60
USOS_CODIGO = 3
MAX_FALLOS = 5
BLOQUEO = 15 * 60
VIDA_DISPOSITIVO = 12 * 3600
MAX_DISPOSITIVOS = 5
BUCLE_LOCAL = {"127.0.0.1", "::1"}
# Lo único que ve un aparato sin emparejar: la página del código y lo que esa página necesita para dibujarse.
RUTAS_ABIERTAS = {"/emparejar.html", "/emparejar.js", "/util.js", "/estilos.css", "/icono.svg", "/icono-192.png", "/api/emparejar"}


def ip_privada(ip: str | None) -> bool:
    """True para direcciones de una red de casa u oficina (no de Internet)."""
    try:
        direccion = ipaddress.ip_address((ip or "").split("%")[0])
    except ValueError:
        return False
    return direccion.is_loopback or direccion.is_link_local or (direccion.is_private and not direccion.is_global)


def ip_de_esta_red() -> str | None:
    """La dirección de este equipo en la red por la que sale a Internet (la del Wi-Fi). No envía ningún dato: solo pregunta por qué interfaz saldría."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except OSError:
            return None
    direccion = ipaddress.ip_address(ip)
    return ip if ip_privada(ip) and not (direccion.is_loopback or direccion.is_link_local) else None


def nombre_bonjour() -> str | None:
    """El nombre «mi-mac.local» que el iPhone también entiende, si este equipo tiene uno."""
    nombre = socket.gethostname().strip().lower()
    return nombre if re.fullmatch(r"[a-z0-9-]{1,63}\.local", nombre) else None


def normalizar(codigo: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(codigo).upper())


class Red:
    """El estado del modo Wi-Fi: el código vigente, el bloqueo por fallos y los aparatos ya emparejados."""

    def __init__(self, ip: str, puerto: int, nombre: str | None = None, reloj=time.monotonic) -> None:
        self.ip = ip
        self.puerto = puerto
        self.hosts = frozenset({ip} | ({nombre} if nombre else set()))
        self.nombre = nombre
        self._reloj = reloj
        self._cerrojo = threading.Lock()
        self._dispositivos: dict[str, float] = {}
        self._fallos = 0
        self._bloqueado_hasta = 0.0
        self.al_fallar = None  # función(ip_del_aparato) para avisar en la Terminal
        self._codigo = ""
        self._vence = 0.0
        self._usos = 0
        self.nuevo_codigo()

    # --------------------------------------------------------------------------------------------------- el código
    def nuevo_codigo(self) -> str:
        """Pulsar Enter en la Terminal: código nuevo, usos a cero y sin bloqueo. Los aparatos ya emparejados siguen valiendo."""
        with self._cerrojo:
            self._codigo = "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))
            self._vence = self._reloj() + VIDA_CODIGO
            self._usos = 0
            self._fallos = 0
            self._bloqueado_hasta = 0.0
            return self._codigo

    def codigo_para_mostrar(self) -> str:
        return f"{self._codigo[:4]}-{self._codigo[4:]}"

    def minutos_de_vida(self) -> int:
        return max(0, int((self._vence - self._reloj()) // 60) + 1)

    def direcciones(self) -> list[str]:
        base = [f"http://{ip}:{self.puerto}" for ip in sorted(self.hosts)]
        return sorted(base, key=lambda d: (".local" in d, d))

    # ---------------------------------------------------------------------------------------------- emparejar
    def probar(self, candidato: str, ip_cliente: str = "?") -> tuple[str | None, str, int]:
        """(token del aparato, mensaje, segundos de espera). El token solo viaja en la cookie."""
        with self._cerrojo:
            ahora = self._reloj()
            if ahora < self._bloqueado_hasta:
                return None, "Demasiados intentos. Pulsa Enter en la Terminal del Mac para recibir un código nuevo.", int(self._bloqueado_hasta - ahora) + 1
            if ahora > self._vence or self._usos >= USOS_CODIGO:
                return None, "Ese código ya no sirve. Pulsa Enter en la Terminal del Mac para ver uno nuevo.", 0
            if not hmac.compare_digest(normalizar(candidato).encode(), self._codigo.encode()):
                self._fallos += 1
                if self._fallos >= MAX_FALLOS:
                    self._bloqueado_hasta = ahora + BLOQUEO
                if self.al_fallar:
                    self.al_fallar(ip_cliente)
                return None, "El código no coincide. Míralo otra vez en la Terminal del Mac.", 0
            self._usos += 1
            self._fallos = 0
            self._dispositivos = {h: v for h, v in self._dispositivos.items() if v > ahora}
            if len(self._dispositivos) >= MAX_DISPOSITIVOS:
                del self._dispositivos[min(self._dispositivos, key=self._dispositivos.get)]
            token = secrets.token_urlsafe(32)
            self._dispositivos[hashlib.sha256(token.encode()).hexdigest()] = ahora + VIDA_DISPOSITIVO
            return token, "", 0

    def dispositivo_valido(self, token: str | None) -> bool:
        if not token:
            return False
        with self._cerrojo:
            vence = self._dispositivos.get(hashlib.sha256(token.encode()).hexdigest())
            return vence is not None and vence > self._reloj()

    def dispositivos_activos(self) -> int:
        with self._cerrojo:
            ahora = self._reloj()
            return sum(1 for v in self._dispositivos.values() if v > ahora)

    def es_remoto(self, ip_cliente: str | None) -> bool:
        return (ip_cliente or "?") not in BUCLE_LOCAL
