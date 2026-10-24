"""Pruebas del modo opcional «iPhone por Wi-Fi»: el código de emparejamiento, sus límites, las defensas del servidor y un servidor real en dos direcciones.
Se ejecutan con ./creador probar (o: python -m servidor.pruebas_red). Usan una carpeta de datos temporal: no tocan tus cuentas ni tu clave de la IA."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PUERTO = 8766
IP_REMOTA = "192.168.1.50"
IP_DEL_MAC = "192.168.1.23"


class _Reloj:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def correr() -> list[str]:
    from fastapi.testclient import TestClient

    from . import arranque, datos, red, seguridad
    from .principal import crear_app

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    datos.abrir()
    print("Aislamiento")
    ok(Path(datos.DATOS).resolve() != (Path(__file__).resolve().parents[1] / "datos"), "estas pruebas usan una carpeta temporal: no tocan tus cuentas ni la clave de la IA")

    print("Direcciones de red")
    ok(all(red.ip_privada(ip) for ip in ("192.168.1.5", "10.0.0.2", "172.16.4.4", "172.31.255.1", "127.0.0.1", "::1", "169.254.1.1")), "las redes de casa y este mismo equipo cuentan como locales")
    ok(not any(red.ip_privada(ip) for ip in ("8.8.8.8", "172.32.0.1", "100.64.0.1", "2001:4860::1", "testclient", "", None)), "las direcciones de Internet, de operadores o inventadas no cuentan")
    ok(seguridad.host_permitido("127.0.0.1:8765", 8765) and seguridad.host_permitido("localhost", 8765) and not seguridad.host_permitido("192.168.1.23:8765", 8765),
       "sin el modo Wi-Fi, solo se atiende a localhost (como antes)")
    ok(seguridad.host_permitido("192.168.1.23:8765", 8765, {"192.168.1.23"}) and not seguridad.host_permitido("192.168.1.23:9999", 8765, {"192.168.1.23"})
       and not seguridad.host_permitido("evil.com:8765", 8765, {"192.168.1.23"}) and not seguridad.host_permitido("192.168.1.23.evil.com", 8765, {"192.168.1.23"}),
       "con el modo Wi-Fi, solo el nombre exacto de este equipo y su puerto")
    ok(seguridad.origen_permitido("http://192.168.1.23:8765", None, 8765, {"192.168.1.23"}) and not seguridad.origen_permitido("http://192.168.1.23:8765", None, 8765)
       and not seguridad.origen_permitido("http://evil.com:8765", None, 8765, {"192.168.1.23"}) and not seguridad.origen_permitido("https://192.168.1.23:8765", None, 8765, {"192.168.1.23"}),
       "las peticiones que modifican datos solo valen si vienen de esta misma página")

    print("Código de emparejamiento")
    reloj = _Reloj()
    conexion = red.Red(IP_DEL_MAC, PUERTO, "mi-mac.local", reloj=reloj)
    codigo = conexion._codigo
    ok(len(codigo) == red.LARGO_CODIGO and all(c in red.ALFABETO for c in codigo), "el código tiene 8 caracteres sin letras que se confunden (I, O, 0, 1)")
    ok(conexion.codigo_para_mostrar() == f"{codigo[:4]}-{codigo[4:]}" and red.normalizar("ab-cd 12") == "ABCD12", "se muestra como XXXX-XXXX y se acepta en minúsculas, con guion o con espacios")
    ok(conexion.direcciones() == [f"http://{IP_DEL_MAC}:{PUERTO}", f"http://mi-mac.local:{PUERTO}"], "la Terminal muestra la dirección por número y por nombre")
    avisos: list[str] = []
    conexion.al_fallar = avisos.append
    token, mensaje, espera = conexion.probar("AAAAAAAA", "192.168.1.99")
    ok(token is None and "no coincide" in mensaje and avisos == ["192.168.1.99"], "un código equivocado no entra y avisa en la Terminal desde qué aparato")
    token, _, _ = conexion.probar(codigo.lower(), IP_REMOTA)
    ok(token is not None and conexion.dispositivo_valido(token) and not conexion.dispositivo_valido(token + "x") and not conexion.dispositivo_valido(None) and not conexion.dispositivo_valido(""), "el código correcto da un aparato emparejado; un token inventado no vale")
    ok(token not in json.dumps(list(conexion._dispositivos)), "en memoria solo queda un resumen del token, no el token")
    conexion.probar(codigo, IP_REMOTA)
    conexion.probar(codigo, IP_REMOTA)
    cuarto, mensaje, _ = conexion.probar(codigo, IP_REMOTA)
    ok(cuarto is None and "ya no sirve" in mensaje and conexion.dispositivos_activos() == red.USOS_CODIGO, f"un código sirve para {red.USOS_CODIGO} aparatos y no más")
    codigo2 = conexion.nuevo_codigo()
    ok(codigo2 != codigo and conexion.probar(codigo, IP_REMOTA)[0] is None and conexion.probar(codigo2, IP_REMOTA)[0] is not None and conexion.dispositivo_valido(token),
       "Enter en la Terminal da un código nuevo, el anterior deja de valer y los aparatos ya emparejados siguen")
    conexion.nuevo_codigo()
    reloj.t += red.VIDA_CODIGO + 1
    ok(conexion.probar(conexion._codigo, IP_REMOTA)[0] is None, "el código vence a los 10 minutos")
    conexion.nuevo_codigo()
    for _ in range(red.MAX_FALLOS):
        conexion.probar("ZZZZZZZZ", IP_REMOTA)
    token, mensaje, espera = conexion.probar(conexion._codigo, IP_REMOTA)
    ok(token is None and espera > 0 and "Demasiados" in mensaje, "tras 5 fallos se bloquea aunque después llegue el código bueno")
    conexion.nuevo_codigo()
    ok(conexion.probar(conexion._codigo, IP_REMOTA)[0] is not None, "pulsar Enter en la Terminal (presencia física) quita el bloqueo")
    viejo = conexion.nuevo_codigo()
    antes = conexion.probar(viejo, IP_REMOTA)[0]
    reloj.t += red.VIDA_DISPOSITIVO + 1
    ok(not conexion.dispositivo_valido(antes), "un aparato emparejado deja de valer a las 12 horas")
    for _ in range(red.MAX_DISPOSITIVOS + 2):
        conexion.probar(conexion.nuevo_codigo(), IP_REMOTA)
    ok(conexion.dispositivos_activos() <= red.MAX_DISPOSITIVOS, f"nunca hay más de {red.MAX_DISPOSITIVOS} aparatos emparejados a la vez")

    print("Defensas del servidor")
    sin_modo = TestClient(crear_app(PUERTO), base_url=f"http://{IP_DEL_MAC}:{PUERTO}", client=(IP_REMOTA, 50000))
    ok(sin_modo.get("/api/sesion").status_code == 421 and sin_modo.post("/api/emparejar", json={"codigo": "AAAAAAAA"}).status_code == 421, "sin el modo Wi-Fi, un aparato de la red no entra ni siquiera con la dirección del Mac")
    local_sin_modo = TestClient(crear_app(PUERTO), base_url=f"http://127.0.0.1:{PUERTO}")
    r = local_sin_modo.post("/api/emparejar", json={"codigo": "AAAAAAAA"})
    ok(r.status_code == 404 and local_sin_modo.get("/api/sesion").json()["por_red"] is False, "sin el modo Wi-Fi, no existe el emparejamiento y el uso normal no cambia")

    conexion = red.Red(IP_DEL_MAC, PUERTO, "mi-mac.local")
    app = crear_app(PUERTO, conexion)
    nuevo = lambda ip=IP_REMOTA, host=IP_DEL_MAC: TestClient(app, base_url=f"http://{host}:{PUERTO}", client=(ip, 50000), follow_redirects=False)  # noqa: E731
    c = nuevo()
    r = c.get("/")
    ok(r.status_code == 302 and r.headers["location"] == "/emparejar.html", "un aparato sin emparejar que abre Iris va a la página del código")
    ok(all(c.get(ruta).status_code == 302 for ruta in ("/app.js", "/panel.js", "/trabajo.js", "/legal/privacidad.html", "/manifest.webmanifest")), "no puede leer ni el código de la pantalla ni los textos")
    r = c.get("/api/sesion")
    ok(r.status_code == 401 and r.json().get("emparejar") is True, "la API le responde «empareja este aparato», nunca datos")
    ok(all(c.request(m, ruta, json={} if m != "GET" else None).status_code == 401 for m, ruta in (("GET", "/api/estado"), ("POST", "/api/registro"), ("POST", "/api/entrar"), ("GET", "/api/cuenta/exportar"), ("DELETE", "/api/cuenta"))),
       "ni crear una cuenta, ni entrar, ni exportar, ni borrar sin emparejar")
    pagina = c.get("/emparejar.html")
    ok(pagina.status_code == 200 and "emparejar.js" in pagina.text and c.get("/emparejar.js").status_code == 200 and c.get("/estilos.css").status_code == 200 and c.get("/util.js").status_code == 200,
       "sí ve la página del código y lo justo para dibujarla")
    ok("script-src 'self'" in pagina.headers.get("content-security-policy", "") and pagina.headers.get("cache-control") == "no-store", "con la política de contenido estricta y sin guardarse en caché")
    ok(nuevo(host="evil.com").get("/api/sesion").status_code == 421 and nuevo(host=f"{IP_DEL_MAC}.evil.com").get("/api/sesion").status_code == 421, "un nombre de host ajeno (DNS rebinding) se rechaza antes de nada")
    ok(nuevo(ip="8.8.8.8").get("/emparejar.html").status_code == 403, "una dirección de Internet se rechaza aunque conozca el código")
    r = c.post("/api/emparejar", json={"codigo": "AAAAAAAA"}, headers={"Origin": "http://evil.com"})
    ok(r.status_code == 403, "emparejar desde otra página web se rechaza")
    r = c.post("/api/emparejar", json={"codigo": "AAAAAAAA"}, headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}"})
    ok(r.status_code == 401 and "no coincide" in r.json()["mensaje"], "un código equivocado da un mensaje claro y 401")
    r = c.post("/api/emparejar", json={"codigo": conexion._codigo.lower()}, headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}"})
    galleta = r.headers.get("set-cookie", "")
    ok(r.status_code == 200 and "iris_dispositivo=" in galleta and "httponly" in galleta.lower() and "samesite=strict" in galleta.lower(), "el código bueno da la cookie del aparato (HttpOnly, SameSite=Strict)")
    r = c.get("/api/sesion")
    ok(r.status_code == 200 and r.json()["por_red"] is True and r.json()["autenticado"] is False, "ya emparejado ve la pantalla de entrada, y la app sabe que va por Wi-Fi")
    ok(c.get("/").status_code == 200 and c.get("/app.js").status_code == 200, "ya emparejado abre Iris")
    ok(c.get("/api/estado").status_code == 401 and c.get("/api/estado").json().get("emparejar") is None, "emparejado no es lo mismo que iniciar sesión: sigue haciendo falta la cuenta")
    r = c.post("/api/registro", json={"correo": "ana@casa.co", "nombre": "Ana", "contrasena": "una-clave-larga-1", "acepto": True},
               headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}"})
    ok(r.status_code == 200 and "iris_sesion=" in r.headers.get("set-cookie", ""), "desde el aparato emparejado se puede crear la cuenta y entrar (con el Origin de esta misma página)")
    otro = nuevo(ip="192.168.1.77")
    ok(otro.get("/api/estado").status_code == 401 and otro.get("/api/estado").json().get("emparejar") is True, "otro aparato de la red no hereda nada: sigue sin emparejar")
    ok(otro.get("/api/estado", cookies={"iris_dispositivo": "inventado", "iris_sesion": c.cookies.get("iris_sesion") or "x"}).status_code == 401, "ni con una cookie de aparato inventada ni con la sesión de otro")
    cerrado = nuevo(ip="192.168.1.88")
    for _ in range(red.MAX_FALLOS):
        cerrado.post("/api/emparejar", json={"codigo": "ZZZZZZZZ"}, headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}"})
    r = cerrado.post("/api/emparejar", json={"codigo": conexion._codigo}, headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}"})
    ok(r.status_code == 429 and r.json()["espera"] > 0 and "Retry-After" in r.headers, "tras 5 fallos responde 429 con el tiempo de espera")
    cuerpo = nuevo(ip="192.168.1.89").post("/api/emparejar", content=b"no es json", headers={"Origin": f"http://{IP_DEL_MAC}:{PUERTO}", "Content-Type": "application/json"})
    ok(cuerpo.status_code in (400, 429), "un cuerpo que no es JSON no tumba el servidor")
    local = TestClient(app, base_url=f"http://127.0.0.1:{PUERTO}", client=("127.0.0.1", 50000))
    ok(local.get("/").status_code == 200 and local.get("/api/sesion").json()["por_red"] is False, "este Mac sigue entrando sin código, como siempre")

    print("Servidor real en dos direcciones")
    ip = red.ip_de_esta_red()
    if ip is None:
        print("  · (este equipo no tiene una dirección de red local: se omite la prueba con sockets reales)")
        return fallos
    puerto = PUERTO + 1
    conexion = red.Red(ip, puerto, None)
    servidor, conectores = arranque.servidor_en_red(crear_app(puerto, conexion), puerto, ip)
    hilo = threading.Thread(target=lambda: servidor.run(sockets=conectores), daemon=True)
    hilo.start()
    try:
        for _ in range(100):
            if getattr(servidor, "started", False):
                break
            time.sleep(0.1)
        ok(servidor.started, "el servidor arranca escuchando en 127.0.0.1 y en la dirección de la red")

        class _SinRedireccion(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                return None

        def pedir(url, metodo="GET", cuerpo=None, cabeceras=None):
            peticion = urllib.request.Request(url, data=cuerpo, method=metodo, headers=cabeceras or {})
            try:
                with urllib.request.build_opener(_SinRedireccion).open(peticion, timeout=3) as r:
                    return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read()
            except urllib.error.HTTPError as e:
                return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read()
            except urllib.error.URLError:
                return 0, {}, b""

        estado, cabeceras, _ = pedir(f"http://127.0.0.1:{puerto}/api/sesion")
        ok(estado == 200, "por 127.0.0.1 se entra sin código")
        estado, cabeceras, _ = pedir(f"http://{ip}:{puerto}/")
        ok(estado == 302 and cabeceras.get("location") == "/emparejar.html", "por la dirección de la red, un aparato sin emparejar va a la página del código")
        estado, _, _ = pedir(f"http://{ip}:{puerto}/api/estado")
        ok(estado == 401, "y la API no le da nada")
        origen = {"Origin": f"http://{ip}:{puerto}", "Content-Type": "application/json"}
        estado, cabeceras, _ = pedir(f"http://{ip}:{puerto}/api/emparejar", "POST", json.dumps({"codigo": conexion._codigo}).encode(), origen)
        galleta = (cabeceras.get("set-cookie") or "").split(";")[0]
        ok(estado == 200 and galleta.startswith("iris_dispositivo="), "con el código bueno por la red, recibe su cookie")
        estado, _, cuerpo = pedir(f"http://{ip}:{puerto}/api/sesion", cabeceras={"Cookie": galleta})
        ok(estado == 200 and json.loads(cuerpo)["por_red"] is True, "con la cookie, entra a Iris por la red y se sabe que va por Wi-Fi")
        estado, _, _ = pedir(f"http://127.0.0.2:{puerto}/api/sesion")
        ok(estado == 0 or estado >= 400, "otra dirección de este equipo (no la de la red) no está abierta o se rechaza")
    finally:
        servidor.should_exit = True
        hilo.join(timeout=10)
        for conector in conectores:
            conector.close()
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="iris-datos-prueba-") as carpeta:
        os.environ["IRIS_DATOS"] = carpeta
        sys.exit(1 if correr() else 0)
