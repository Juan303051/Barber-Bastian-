"""Prueba de la app de punta a punta, sin navegador: cuentas, seguridad, subida y (con --completo) un video creado de verdad.
Se ejecuta con ./creador probar. Usa una carpeta de datos temporal: no toca tus cuentas ni tus videos."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PUERTO = 8765
# Contraseñas de prueba: solo existen en la base temporal de esta ejecución.
CLAVE_ANA = "una-clave-larga-1"
CLAVE_LUIS = "otra-clave-larga-2"


def _video_de_prueba(destino: Path) -> Path:
    ruta = destino / "toma.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=360x640:d=3:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=330:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(ruta)],
                   check=True)
    return ruta


def correr(completo: bool) -> list[str]:
    from fastapi.testclient import TestClient

    from .principal import crear_app

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    c = TestClient(crear_app(PUERTO), base_url=f"http://127.0.0.1:{PUERTO}")
    temporal = Path(tempfile.mkdtemp(prefix="iris-video-"))
    toma = _video_de_prueba(temporal)

    print("Cuentas")
    r = c.get("/api/sesion").json()
    ok(r["primera_vez"] and not r["autenticado"], "primera vez, sin sesión")
    r = c.post("/api/registro", json={"correo": "mala", "nombre": "", "contrasena": "123"})
    ok(r.status_code == 422 and set(r.json()["campos"]) == {"correo", "nombre", "contrasena"}, "registro inválido marca los tres campos")
    r = c.post("/api/registro", json={"correo": "ana@empresa.com", "nombre": "Ana", "contrasena": "password"})
    ok(r.status_code == 422 and "común" in r.json()["campos"]["contrasena"], "contraseña común rechazada")
    r = c.post("/api/registro", json={"correo": "Ana@Empresa.com", "nombre": "Ana", "contrasena": CLAVE_ANA, "recordar": True})
    ok(r.status_code == 200 and "iris_sesion" in c.cookies, "el registro correcto inicia sesión")
    cookie = r.headers["set-cookie"].lower()
    ok("httponly" in cookie and "samesite=strict" in cookie, "cookie HttpOnly y SameSite=Strict")
    ok(c.get("/api/sesion").json()["usuario"]["correo"] == "ana@empresa.com", "el correo se guarda en minúsculas")
    r = c.post("/api/registro", json={"correo": "luis@empresa.com", "nombre": "Luis", "contrasena": CLAVE_LUIS})
    ok(r.status_code == 200 and not r.json()["entro"], "con sesión se añade a otra persona sin cambiar de sesión")
    c.post("/api/salir")
    ok(c.get("/api/sesion").json()["autenticado"] is False, "salir cierra la sesión")
    r = c.post("/api/registro", json={"correo": "x@y.com", "nombre": "X", "contrasena": "una-clave-larga-3"})
    ok(r.status_code == 403, "sin sesión no se pueden crear cuentas")
    for i in range(5):
        r = c.post("/api/entrar", json={"correo": "ana@empresa.com", "contrasena": f"equivocada{i}"})
        ok(r.status_code == 401 and "no coinciden" in r.json()["mensaje"], f"intento fallido {i + 1}: el mensaje no dice cuál dato falló")
    r = c.post("/api/entrar", json={"correo": "ana@empresa.com", "contrasena": CLAVE_ANA})
    ok(r.status_code == 429 and "Retry-After" in r.headers, "tras 5 fallos se bloquea aunque la clave sea buena")
    r = c.post("/api/entrar", json={"correo": "luis@empresa.com", "contrasena": CLAVE_LUIS})
    ok(r.status_code == 200, "otra cuenta no queda bloqueada")

    print("Seguridad")
    ok(c.get("/api/estado").status_code == 200, "con sesión se ve el panel")
    ok(TestClient(c.app, base_url=f"http://127.0.0.1:{PUERTO}").get("/api/estado").status_code == 401, "sin cookie: 401")
    ok(c.get("/api/estado", headers={"host": "evil.com"}).status_code == 421, "Host ajeno: 421 (DNS rebinding)")
    ok(c.post("/api/trabajos", json={}, headers={"origin": "http://evil.com"}).status_code == 403, "Origin ajeno: 403 (CSRF)")
    ok(c.post("/api/trabajos", json={}, headers={"sec-fetch-site": "cross-site"}).status_code == 403, "Sec-Fetch-Site cross-site: 403")
    cabeceras = c.get("/").headers
    ok("default-src 'self'" in cabeceras["content-security-policy"] and cabeceras["x-content-type-options"] == "nosniff", "cabeceras de seguridad")
    ok(c.get("/api/trabajos/../../etc/passwd/fotograma").status_code in (404, 405), "una ruta con .. no sale de la carpeta")
    ok(c.get("/api/trabajos/zzzz/miniatura").status_code == 404, "identificadores inválidos: 404")

    print("Trabajos y subida")
    jid = c.post("/api/trabajos", json={"marca": "al-volante"}).json()["id"]
    r = c.put(f"/api/trabajos/{jid}/video?nombre=notas.txt", content=b"hola")
    ok(r.status_code == 415, "extensión no permitida: 415")
    r = c.put(f"/api/trabajos/{jid}/video?nombre=falso.mp4", content=b"esto no es un video")
    ok(r.status_code == 422 and "no es un video" in r.json()["mensaje"], "archivo falso con extensión mp4: 422")
    ok(c.put(f"/api/trabajos/{jid}/video?nombre=vacio.mp4", content=b"").status_code == 422, "archivo vacío: 422")
    ok(c.post(f"/api/trabajos/{jid}/crear").status_code == 422, "crear sin video: 422 con mensaje")
    r = c.put(f"/api/trabajos/{jid}/video?nombre=toma.mp4", content=toma.read_bytes())
    ok(r.status_code == 200 and 2.5 < r.json()["duracion"] < 3.5, f"video válido: dura {r.json().get('duracion')} s")
    ok(c.get(f"/api/trabajos/{jid}/miniatura").status_code == 200, "se genera la miniatura")
    r = c.post("/api/interpretar", json={"prompt": "Resalta las palabras dinero y semanas. Quita las pausas. Comenta EDITOR. Con transiciones", "opciones": {}}).json()
    ok(any("dinero" in f["texto"] for f in r["entendido"]) and r["sugerencias"][0]["clave"] == "quitar_pausas" and r["pendiente"],
       "interpretar: entiende, sugiere y avisa de lo que no hace")
    c.patch(f"/api/trabajos/{jid}", json={"prompt": "Resalta las palabras dinero y semanas. Comenta EDITOR", "titulo": "Prueba", "opciones": {"calidad": "borrador", "intruso": 1}})
    t = next(x for x in c.get("/api/estado").json()["trabajos"] if x["id"] == jid)
    ok(t["opciones"] == {"calidad": "borrador"} and t["titulo"] == "Prueba", "solo se guardan las opciones permitidas")
    r = c.post("/api/referencias/enlace", json={"url": "hola"})
    ok(r.status_code == 422, "un enlace que no es enlace se rechaza")

    print("Música, IA y test del director")
    from . import pruebas_audio
    from .direccion import ia
    cancion = temporal / "cancion.wav"
    pruebas_audio.escribir_wav(pruebas_audio.pista_sintetica(100, 30.0)[0], cancion)
    r = c.put("/api/musica/archivo?nombre=falso.mp3", content=b"esto no es musica")
    id_falso = r.json()["id"]
    r = c.put("/api/musica/archivo?nombre=notas.txt", content=b"hola")
    ok(r.status_code == 415, "música: una extensión que no es de audio se rechaza (415)")
    r = c.put("/api/musica/archivo?nombre=Mi%20Cancion.wav", content=cancion.read_bytes())
    id_cancion = r.json()["id"]
    ok(r.status_code == 200, "música: se sube una canción")

    def esperar_musica(id_: str) -> dict:
        for _ in range(240):
            m = next(x for x in c.get("/api/estado").json()["musica"] if x["id"] == id_)
            if m["estado"] in {"lista", "error"}:
                return m
            time.sleep(0.5)
        return m
    m = esperar_musica(id_cancion)
    ok(m["estado"] == "lista" and abs(m["bpm"] - 100) < 1.5 and m["licencia"] == "sin-confirmar", f"música: se analiza sola ({m['bpm']} BPM, licencia «{m['licencia']}»)")
    m_falso = esperar_musica(id_falso)
    ok(m_falso["estado"] == "error" and "audio" in m_falso["error"], f"música: un archivo falso termina en un error claro («{m_falso['error']}»)")
    ok(c.patch(f"/api/musica/{id_cancion}", json={"licencia": "inventada"}).status_code == 422, "música: una licencia que no existe se rechaza")
    ok(c.patch(f"/api/musica/{id_cancion}", json={"licencia": "licenciada"}).status_code == 200, "música: se declara la licencia")
    ok(c.get(f"/api/musica/{id_cancion}/audio").status_code == 200, "música: se puede escuchar desde la página")
    ok(c.delete(f"/api/musica/{id_falso}").status_code == 200 and len(c.get("/api/estado").json()["musica"]) == 1, "música: se puede quitar")
    estado_ia = c.get("/api/ia").json()
    ok("clave" not in estado_ia and estado_ia["modelo"] == "claude-opus-5-5", "IA: el estado no incluye la clave y el modelo por defecto es Opus 5.5")
    ok(c.put("/api/ia", json={"clave": "tiene espacios dentro"}).status_code == 422, "IA: una clave con espacios se rechaza")
    ok(c.put("/api/ia", json={"activa": False}).json()["activa"] is False, "IA: se puede apagar")
    c.put("/api/ia", json={"activa": True})
    pregunta = c.get("/api/perfil").json()
    ok(len(pregunta["preguntas"]) == 10 and pregunta["respuestas"] == {}, "test del director: 10 preguntas y sin respuestas todavía")
    r = c.put("/api/perfil", json={"marca": "al-volante", "respuestas": {"tono": "volando"}})
    ok(r.status_code == 422 and "tono" in r.json()["campos"], "test del director: una opción inválida se rechaza")
    c.put("/api/perfil", json={"marca": "al-volante", "respuestas": {"tono": "experto", "ritmo": "rapido", "nunca": "garantizado"}})
    ok(c.get("/api/perfil?marca=al-volante").json()["respuestas"]["tono"] == "experto" and c.get("/api/perfil").json()["respuestas"] == {}, "test del director: se guarda por marca sin tocar el general")

    if completo:
        print("Un video de verdad (sin voz: debe crearse igual)")
        ok(c.post(f"/api/trabajos/{jid}/crear").status_code == 200, "se pone en la cola")
        inicio, visto, foto = time.time(), set(), False
        while time.time() - inicio < 900:
            t = next(x for x in c.get("/api/estado").json()["trabajos"] if x["id"] == jid)
            visto.add(t["etapa"])
            if t["estado"] == "trabajando" and t["fotogramas_listos"] > 5 and not foto:
                r = c.get(f"/api/trabajos/{jid}/fotograma?n={t['fotogramas_listos'] - 2}")
                foto = r.status_code == 200 and r.content[:2] == b"\xff\xd8"
            if t["estado"] in {"listo", "error", "cancelado"}:
                break
            time.sleep(0.7)
        ok(t["estado"] == "listo", f"termina bien ({t['estado']}{': ' + str(t['error']) if t['error'] else ''}, {round(time.time() - inicio)} s)")
        ok(foto, "mientras se construye, ya se puede ver un fotograma")
        ok(len(visto - {None}) >= 2, f"informa de varias etapas: {len(visto - {None})}")
        if t["estado"] == "listo":
            r = c.get(f"/api/trabajos/{jid}/resultado")
            archivo = temporal / "resultado.mp4"
            archivo.write_bytes(r.content)
            sonda = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "csv=p=0", str(archivo)], capture_output=True, text=True).stdout
            ok(r.status_code == 200 and "video,540,960" in sonda and "audio" in sonda, f"el resultado es un mp4 de 540×960 con audio ({sonda.strip().replace(chr(10), ' ')})")
            ok("attachment" in c.get(f"/api/trabajos/{jid}/resultado?descargar=1").headers.get("content-disposition", ""), "se puede descargar con nombre")
        c.post(f"/api/trabajos/{jid}/crear")
        c.post(f"/api/trabajos/{jid}/cancelar")
        time.sleep(1.5)
        t = next(x for x in c.get("/api/estado").json()["trabajos"] if x["id"] == jid)
        ok(t["estado"] in {"cancelado", "listo"}, f"cancelar a mitad deja un estado limpio ({t['estado']})")

        print("Un video con voz simulada, IA simulada y música")
        import analizar
        import audio as medidas
        from .pruebas_direccion import TRANSCRIPCION, _Falso, _palabras, _plan_de_la_ia, _respuesta
        voz = temporal / "voz.wav"
        pruebas_audio.voz_sintetica(voz, 14.0)
        toma_voz = temporal / "toma-voz.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=360x640:d=14:r=30", "-i", str(voz), "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(toma_voz)], check=True)
        palabras = _palabras(TRANSCRIPCION)
        original_voz = analizar._voz
        analizar._voz = lambda ruta, dur, modelo, avance=None, idioma=None: {"idioma": "es", "palabras_por_min": 150, "gancho_texto": "Primero revisa el aceite", "palabras": palabras,
                                                                           "segmentos": [{"ini": palabras[0][0], "fin": palabras[-1][1], "texto": TRANSCRIPCION}]}
        plan = _plan_de_la_ia()
        plan["momentos"] = [{"t": 1.5, "tipo": "acercamiento", "motivo": ""}, {"t": 3.8, "tipo": "contador", "motivo": "", "valor": 5000}]
        falso = _Falso(_respuesta(json.dumps(plan)))
        ia._fabrica = lambda: falso
        try:
            jid2 = c.post("/api/trabajos", json={"marca": "al-volante", "titulo": "Con IA"}).json()["id"]
            c.put(f"/api/trabajos/{jid2}/video?nombre=toma-voz.mp4", content=toma_voz.read_bytes())
            c.patch(f"/api/trabajos/{jid2}", json={"prompt": "Resalta aceite y filtro.", "opciones": {"calidad": "borrador", "musica": True}})
            c.post(f"/api/trabajos/{jid2}/crear")
            inicio = time.time()
            while time.time() - inicio < 900:
                t2 = next(x for x in c.get("/api/estado").json()["trabajos"] if x["id"] == jid2)
                if t2["estado"] in {"listo", "error", "cancelado"}:
                    break
                time.sleep(0.7)
        finally:
            analizar._voz = original_voz
            ia._fabrica = None
        ok(t2["estado"] == "listo", f"termina bien ({t2['estado']}{': ' + str(t2['error']) if t2['error'] else ''}, {round(time.time() - inicio)} s)")
        ok(t2["ia"] and t2["ia"]["usada"] and t2["ia"]["costo_usd"] and len(falso.llamadas) == 1, f"la IA dirigió el video y se registró el costo estimado ({t2['ia']})")
        ok(t2["direccion"] and t2["direccion"]["gancho"] == "Alarga la vida de tu moto" and t2["direccion"]["look"] == "calido", "el plan del director queda guardado y se muestra")
        ok(t2["musica"] and t2["musica"]["licencia"] == "licenciada" and abs(t2["musica"]["bpm"] - 100) < 1.5, f"usó la canción de la biblioteca ({t2['musica']})")
        ok(any("pulso" in n or "Música" in n for n in t2["notas"]), "las notas cuentan que se usó música")
        ok(t2["calidad"] is not None and t2["calidad"]["veredicto"] in {"listo", "revisar"}, f"el control de calidad dejó su informe ({t2['calidad']['veredicto']}: {t2['calidad']['resumen']})")
        niveles = {p["id"]: p["nivel"] for p in t2["calidad"]["pruebas"]}
        ok(niveles["volumen"] == "ok" and niveles["pico"] == "ok" and niveles["negros"] == "ok", f"volumen, pico y negros en orden ({niveles['volumen']}, {niveles['pico']}, {niveles['negros']})")
        final = temporal / "resultado-ia.mp4"
        final.write_bytes(c.get(f"/api/trabajos/{jid2}/resultado").content)
        medida = medidas.medir(final)
        ok(medida is not None and abs(medida["lufs"] + 14) <= 1.0, f"el audio final quedó a {medida['lufs'] if medida else '?'} LUFS (objetivo −14)")
    return fallos


if __name__ == "__main__":
    # Se ejecuta en su propio proceso para que IRIS_DATOS (carpeta temporal) valga desde el primer import.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="iris-datos-prueba-") as carpeta:
        os.environ["IRIS_DATOS"] = carpeta
        # Empresas de mentira: la prueba no deja videos en tus carpetas reales.
        for marca in ("maquetas-estilo", "al-volante"):
            for sub in ("videos/referencias", "videos/propios", "salidas", "analisis"):
                (Path(carpeta) / "empresas" / marca / sub).mkdir(parents=True)
        os.environ["CREADOR_EMPRESAS"] = str(Path(carpeta) / "empresas")
        os.environ.setdefault("IRIS_MODELO_VOZ", "tiny")
        from servidor.pruebas_api import correr as _correr
        malos = _correr("--completo" in sys.argv)
    print(json.dumps({"fallos": malos}, ensure_ascii=False) if "--json" in sys.argv else "")
    sys.exit(1 if malos else 0)
