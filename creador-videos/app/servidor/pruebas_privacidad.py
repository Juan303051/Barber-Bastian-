"""Pruebas de privacidad y cumplimiento: textos legales, consentimientos, exportar y borrar datos, nada de terceros en la página, transparencia de costos y señales de patrones oscuros.
Se ejecutan con ./creador probar (o: python -m servidor.pruebas_privacidad). Usan una carpeta de datos temporal: no tocan tus cuentas ni tus videos."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PUERTO = 8765
RAIZ_WEB = Path(__file__).resolve().parents[1] / "web"
PERMITIDAS = {"http://www.w3.org/2000/svg", "https://www.anthropic.com/legal/privacy", "https://www.remotion.dev/docs/license"}
URGENCIA = ("últimas horas", "solo hoy", "oferta limitada", "se agota", "quedan pocos", "no te lo pierdas", "última oportunidad", "ahora o nunca")


def correr() -> list[str]:
    from fastapi.testclient import TestClient

    from . import datos, produccion
    from .direccion import ia
    from .principal import crear_app

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    print("Textos legales")
    paginas = {n: (RAIZ_WEB / "legal" / f"{n}.html").read_text(encoding="utf-8") for n in ("privacidad", "terminos", "reembolsos", "cookies")}
    ok(all(p.count("<h1") == 1 and 'lang="es"' in p and "Borrador" in p and "no es asesoría legal" in p for p in paginas.values()), "las cuatro páginas existen, están en español y avisan de que son un borrador para revisar")
    ok(all(n in " ".join(re.findall(r'href="([^"]+)"', paginas["privacidad"])) for n in ("terminos.html", "cookies.html", "reembolsos.html")), "cada página enlaza a las otras")
    ok(all(f'href="{n}.html"' in p for p in paginas.values() for n in paginas), "y todas tienen el mismo menú de textos legales")
    ok("scrypt" in paginas["privacidad"] and "Anthropic" in paginas["privacidad"] and "Hugging Face" in paginas["privacidad"] and "Remotion" in paginas["privacidad"] and "Exportar mis datos" in paginas["privacidad"], "la política de privacidad cuenta qué se guarda, a quién llega y cómo exportar y borrar")
    ok("iris_sesion" in paginas["cookies"] and "iris_dispositivo" in paginas["cookies"] and "HttpOnly" in paginas["cookies"] and "iris-aviso-cookies" in paginas["cookies"] and "iris-invitacion-cerrada" in paginas["cookies"], "la política de cookies lista todo lo que guarda el navegador")
    ok("no hay nada que reembolsar" in paginas["reembolsos"] and "Anthropic" in paginas["reembolsos"] and "Sin cobros ocultos" in paginas["reembolsos"], "la política de reembolsos dice que Iris no cobra y quién cobra lo demás")
    ok("autorización" in paginas["terminos"] and "menores" in paginas["terminos"] and "reseñas" in paginas["terminos"] and "Remotion" in paginas["terminos"], "los términos piden derechos sobre lo que subes, autorización de padres, no inventar reseñas y avisan de la licencia de Remotion")
    ok(not any(re.search(r"ley \d|ley n[ºo]|decreto|gdpr|reglamento \(ue\)", p, re.I) for p in paginas.values()), "no se citan leyes concretas que nadie haya verificado para tu país")

    print("Nada de terceros en la página")
    urls: set[str] = set()
    for ruta in RAIZ_WEB.rglob("*"):
        if ruta.suffix in {".html", ".js", ".css", ".webmanifest", ".svg"}:
            urls |= set(re.findall(r"https?://[^\s\"'<>)]+", ruta.read_text(encoding="utf-8")))
    ok(urls <= PERMITIDAS, f"las únicas direcciones externas son el espacio de nombres SVG y dos enlaces de lectura en los textos legales ({sorted(urls - PERMITIDAS) or 'ninguna otra'})")
    ok(not re.search(r"<script[^>]+src=\"https?:|<link[^>]+href=\"https?:|@import|url\(\s*https?:|googletagmanager|google-analytics|facebook\.net|hotjar|segment\.", " ".join(p.read_text(encoding="utf-8") for p in RAIZ_WEB.rglob("*") if p.suffix in {".html", ".js", ".css"})),
       "sin scripts, estilos, tipografías ni analíticas de otros sitios")
    texto_visible = " ".join(p.read_text(encoding="utf-8").lower() for p in RAIZ_WEB.rglob("*.js"))
    ok(not any(u in texto_visible for u in URGENCIA), "sin lenguaje de urgencia o presión («solo hoy», «últimas horas»…)")
    acceso_js = (RAIZ_WEB / "acceso.js").read_text(encoding="utf-8")
    ok('id: "acepto"' in acceso_js and not re.search(r'id: "acepto"[^)]*checked', acceso_js), "la casilla de aceptar los términos nunca viene marcada de antemano")
    ui_js = (RAIZ_WEB / "ui.js").read_text(encoding="utf-8")
    ok('"Entendido" })' in ui_js and 'texto: "Ver la política"' in ui_js and "boton principal" not in ui_js.split("mostrarAvisoCookies")[1].split("pieLegal")[0], "en el aviso de cookies los dos botones pesan lo mismo (ninguno destacado)")

    c = TestClient(crear_app(PUERTO), base_url=f"http://127.0.0.1:{PUERTO}")
    cabeceras = c.get("/").headers["content-security-policy"]
    ok("connect-src 'self'" in cabeceras and "default-src 'self'" in cabeceras and "frame-ancestors 'none'" in cabeceras and "script-src 'self'" in cabeceras, "la página solo puede conectarse a este equipo (política de seguridad de contenido)")
    ok(c.get("/legal/privacidad.html").status_code == 200 and c.get("/legal/cookies.html").status_code == 200 and "private" not in c.get("/legal/privacidad.html").headers.get("cache-control", ""), "los textos legales se leen sin iniciar sesión")

    print("Consentimientos al crear la cuenta")
    base = {"correo": "ana@empresa.com", "nombre": "Ana", "contrasena": "una-clave-larga-1"}
    r = c.post("/api/registro", json=base)
    ok(r.status_code == 422 and "acepto" in r.json()["campos"] and c.get("/api/sesion").json()["primera_vez"], "sin aceptar los términos no se crea la cuenta")
    r = c.post("/api/registro", json={**base, "acepto": "si"})
    ok(r.status_code == 422, "«acepto» tiene que ser verdadero de verdad, no un texto")
    r = c.post("/api/registro", json={**base, "acepto": True})
    ok(r.status_code == 200 and r.json()["usuario"]["acepto"] is True and "contrasena" not in json.dumps(r.json()) and "sal" not in r.json()["usuario"], "al aceptar, la cuenta se crea y la respuesta no trae nada secreto")
    fila = datos.uno("SELECT acepto_version, acepto_en FROM usuarios WHERE correo = ?", ("ana@empresa.com",))
    ok(fila["acepto_version"] == "2026-10-24" and fila["acepto_en"] and time.time() - fila["acepto_en"] < 60, "queda constancia de qué versión aceptó y cuándo")
    ok(c.get("/api/sesion").json()["usuario"]["acepto"] is True, "la sesión sabe que ya aceptó")
    datos.ejecutar("UPDATE usuarios SET acepto_version = NULL, acepto_en = NULL WHERE correo = ?", ("ana@empresa.com",))
    ok(c.get("/api/sesion").json()["usuario"]["acepto"] is False, "una cuenta anterior a los textos aparece como «sin aceptar»")
    ok(c.post("/api/cuenta/aceptar", json={}).status_code == 422 and c.post("/api/cuenta/aceptar", json={"acepto": False}).status_code == 422, "aceptar exige un «sí» explícito")
    ok(c.post("/api/cuenta/aceptar", json={"acepto": True}).status_code == 200 and c.get("/api/sesion").json()["usuario"]["acepto"] is True, "y al aceptar queda registrado")
    r = c.post("/api/registro", json={"correo": "luis@empresa.com", "nombre": "Luis", "contrasena": "otra-clave-larga-2"})
    ok(r.status_code == 422 and "acepto" in r.json()["campos"], "al añadir a otra persona también hace falta su aceptación")
    c.post("/api/registro", json={"correo": "luis@empresa.com", "nombre": "Luis", "contrasena": "otra-clave-larga-2", "acepto": True})

    print("La IA no recibe nada sin confirmación, y el dinero no es una sorpresa")
    entorno_previo = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        ia._fabrica = lambda: object()
        e = c.get("/api/ia").json()
        ok(e["disponible"] and not e["consentida"] and not e["activa"], "con una clave disponible pero sin confirmación, la IA queda apagada")
        r = c.put("/api/ia", json={"consentimiento": True}).json()
        ok(r["consentida"] and r["consentida_en"] == time.strftime("%Y-%m-%d") and r["activa"], "al confirmar, se activa y queda la fecha")
        ok(r["costo_estimado_usd"] and r["costo_estimado_usd"] > 0 and r["gastado_mes_usd"] == 0, f"se informa el costo estimado por video (≈ US$ {r['costo_estimado_usd']}) y que este mes no se ha gastado nada")
        datos.insertar("trabajos", {"id": "a" * 12, "usuario_id": None, "titulo": "Prueba", "estado": "listo", "ia_info": {"usada": True, "costo_usd": 0.12}, "creado": time.time(), "actualizado": time.time()})
        datos.insertar("trabajos", {"id": "b" * 12, "usuario_id": None, "titulo": "Viejo", "estado": "listo", "ia_info": {"usada": True, "costo_usd": 5.0}, "creado": 1.0, "actualizado": 1.0})
        ok(c.get("/api/ia").json()["gastado_mes_usd"] == 0.12, "el gasto del mes suma solo los videos de este mes")
        datos.ejecutar("DELETE FROM trabajos")
        r = c.put("/api/ia", json={"consentimiento": False}).json()
        ok(not r["consentida"] and not r["activa"], "retirar la confirmación apaga la IA al instante")
        ia.guardar_ajustes({"consentimiento": True})
    finally:
        ia._fabrica = None
        if entorno_previo:
            os.environ["ANTHROPIC_API_KEY"] = entorno_previo

    print("Exportar y borrar los datos")
    ia.guardar_ajustes({"clave": "k" * 30})
    jid = c.post("/api/trabajos", json={"marca": "al-volante", "titulo": "Mi video"}).json()["id"]
    c.patch(f"/api/trabajos/{jid}", json={"prompt": "Cierra con el logo", "opciones": {"logo": True}})
    toma = Path(tempfile.mkdtemp(prefix="iris-priv-")) / "toma.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc2=s=180x320:d=2:r=24", "-f", "lavfi", "-i", "sine=duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(toma)], check=True)
    c.put(f"/api/trabajos/{jid}/escenas?nombre=toma.mp4", content=toma.read_bytes())
    from .pruebas_escenas import _png
    logo = toma.parent / "logo.png"
    _png(logo, 64, 64, True)
    c.put("/api/marcas/al-volante/logo?nombre=logo.png&derechos=1", content=logo.read_bytes())
    c.put("/api/perfil", json={"marca": "al-volante", "respuestas": {"tono": "experto"}})
    r = c.get("/api/cuenta/exportar")
    exportado = r.json()
    ok(r.status_code == 200 and "attachment" in r.headers["content-disposition"] and r.headers["cache-control"] == "no-store", "exportar descarga un archivo y no se guarda en la caché del navegador")
    ok(exportado["cuenta"]["correo"] == "ana@empresa.com" and exportado["trabajos"][0]["instrucciones"] == "Cierra con el logo" and exportado["trabajos"][0]["escenas"] == [{"nombre": "toma.mp4", "duracion": exportado["trabajos"][0]["escenas"][0]["duracion"]}]
       and exportado["test_del_director"]["al-volante"]["tono"] == "experto", "el archivo trae la cuenta, los videos con sus instrucciones y escenas, y el test del director")
    texto = json.dumps(exportado, ensure_ascii=False)
    ok("k" * 30 not in texto and "scrypt" not in texto and "sal" not in exportado["cuenta"] and exportado["ajustes_de_ia"]["hay_clave_guardada"] is True, "y nunca incluye la clave de la IA ni la contraseña (solo dice que hay una clave guardada)")
    ok("luis@empresa.com" not in texto, "solo exporta los datos de quien lo pide, no los de otras personas")
    carpeta_trabajo = produccion.carpeta_de_trabajo(jid)
    ok(carpeta_trabajo.exists() and (datos.DATOS / "marcas" / "al-volante").exists(), "antes de borrar: existen los archivos del video y el logo")
    ok(c.request("DELETE", "/api/cuenta", json={"contrasena": "incorrecta-1"}).status_code == 403, "borrar la cuenta exige la contraseña")
    r = c.request("DELETE", "/api/cuenta", json={"contrasena": "una-clave-larga-1", "borrar_todo": True})
    ok(r.status_code == 200 and not carpeta_trabajo.exists() and not datos.uno("SELECT id FROM trabajos WHERE id = ?", (jid,)) and not datos.uno("SELECT id FROM usuarios WHERE correo = ?", ("ana@empresa.com",)),
       "«borrar todo» elimina la cuenta, el video y sus archivos")
    ok((datos.DATOS / "marcas" / "al-volante").exists() and (datos.DATOS / "ia.json").exists(), "mientras queda otra cuenta, los logos y los ajustes de la IA no se tocan")
    c.post("/api/entrar", json={"correo": "luis@empresa.com", "contrasena": "otra-clave-larga-2"})
    ok(c.request("DELETE", "/api/cuenta", json={"contrasena": "otra-clave-larga-2", "borrar_todo": True}).status_code == 200, "la última persona también puede borrar todo")
    ok(not (datos.DATOS / "marcas").exists() and not (datos.DATOS / "ia.json").exists() and datos.uno("SELECT COUNT(*) AS n FROM perfiles")["n"] == 0, "al irse la última cuenta se borran también los logos, el test del director y la clave de la IA")
    ok(datos.uno("SELECT COUNT(*) AS n FROM usuarios")["n"] == 0 and datos.uno("SELECT COUNT(*) AS n FROM sesiones")["n"] == 0, "no queda ninguna cuenta ni sesión abierta")
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="iris-datos-privacidad-") as carpeta:
        os.environ["IRIS_DATOS"] = carpeta
        for marca in ("maquetas-estilo", "al-volante"):
            for sub in ("videos/referencias", "videos/propios", "salidas", "analisis"):
                (Path(carpeta) / "empresas" / marca / sub).mkdir(parents=True)
        os.environ["CREADOR_EMPRESAS"] = str(Path(carpeta) / "empresas")
        from servidor.pruebas_privacidad import correr as _correr
        malos = _correr()
    sys.exit(1 if malos else 0)
