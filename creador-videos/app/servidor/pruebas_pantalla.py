"""Prueba de la pantalla en un navegador de verdad: escenas, formato, extras que siguen lo que se escribe, logo, privacidad, teclado y celular.
Es opcional: necesita Playwright (`pip install playwright` y `playwright install chromium`) o un navegador indicado en CREADOR_NAVEGADOR.
Sin eso se omite con un aviso. Se ejecuta con ./creador probar (o: python -m servidor.pruebas_pantalla). Usa una carpeta de datos temporal.
Para añadir la revisión de accesibilidad con axe-core, apunta CREADOR_AXE al archivo axe.min.js."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

PUERTO = 8765
CLAVE = "una-clave-larga-1"


def _toma(ruta: Path, segundos: int, color: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={color}:s=180x320:d={segundos}:r=24", "-f", "lavfi", "-i", f"sine=duration={segundos}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(ruta)], check=True)


def correr() -> list[str] | None:
    """Devuelve la lista de fallos, o None si no hay navegador para probar."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  · se omite: falta Playwright (pip install playwright && playwright install chromium)")
        return None
    import uvicorn

    from .direccion import ia
    from .principal import crear_app
    from .pruebas_escenas import _png

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    ia._fabrica = lambda: object()  # una IA simulada «disponible»: aquí solo se prueba la pantalla
    servidor = uvicorn.Server(uvicorn.Config(crear_app(PUERTO), host="127.0.0.1", port=PUERTO, log_level="error"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/api/sesion", timeout=1).read()
            break
        except OSError:
            time.sleep(0.1)
    base = Path(tempfile.mkdtemp(prefix="iris-pantalla-"))
    tomas = [base / f"escena{n}.mp4" for n in (3, 1, 2)]
    for ruta, color in zip(tomas, ("0x1b6b3a", "0x1b3a6b", "0x6b1b3a")):
        _toma(ruta, 2, color)
    logo = base / "logo.png"
    _png(logo, 64, 64, True)
    axe = Path(os.environ["CREADOR_AXE"]).read_text(encoding="utf-8") if os.environ.get("CREADOR_AXE") and Path(os.environ["CREADOR_AXE"]).is_file() else None

    with sync_playwright() as p:
        try:
            navegador = p.chromium.launch(executable_path=os.environ.get("CREADOR_NAVEGADOR") or None)
        except Exception as error:  # noqa: BLE001
            print(f"  · se omite: no pude abrir un navegador ({str(error).splitlines()[0][:100]})")
            servidor.should_exit = True
            return None
        errores: list[tuple[str, str]] = []
        contexto = navegador.new_context(viewport={"width": 1280, "height": 900}, color_scheme="light", accept_downloads=True, bypass_csp=axe is not None)
        pg = contexto.new_page()
        pg.on("console", lambda m: errores.append((m.type, m.text)) if m.type in ("error", "warning") and "404" not in m.text else None)
        pg.on("pageerror", lambda e: errores.append(("pageerror", str(e))))

        def revisar_axe(etiqueta: str, pagina=None) -> None:
            if axe is None:
                return
            destino = pagina or pg
            destino.wait_for_timeout(900)  # que terminen las animaciones de entrada: a mitad de una, el contraste medido no es el real
            destino.add_script_tag(content=axe)
            r = destino.evaluate("axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']})")
            detalle = "" if not r["violations"] else " → " + "; ".join(
                f"{v['id']} en {', '.join(str(n['target'][0])[:60] for n in v['nodes'][:2])}: {(v['nodes'][0].get('any') or [{}])[0].get('message', '')[:90]}" for v in r["violations"])
            ok(not r["violations"], f"accesibilidad (axe) sin violaciones: {etiqueta}{detalle}")

        print("Privacidad en pantalla")
        pg.goto(f"http://127.0.0.1:{PUERTO}/")
        pg.wait_for_selector(".acceso-tarjeta")
        pg.wait_for_selector("#aviso-cookies")
        botones = pg.locator("#aviso-cookies .boton")
        ok(botones.count() == 2 and pg.locator("#aviso-cookies .boton.principal").count() == 0 and abs(botones.nth(0).bounding_box()["height"] - botones.nth(1).bounding_box()["height"]) < 1,
           "el aviso de cookies tiene dos botones del mismo peso")
        revisar_axe("acceso con aviso de cookies")
        pg.locator("#aviso-cookies button", has_text="Entendido").click()
        pg.reload()
        pg.wait_for_selector(".acceso-tarjeta")
        ok(pg.locator("#aviso-cookies").count() == 0, "«Entendido» lo cierra y no vuelve a salir")
        ok(not pg.locator("#acepto").is_checked() and pg.locator(".pie-legal a").all_inner_texts() == ["Privacidad", "Términos", "Reembolsos", "Cookies"], "la casilla de aceptar no viene marcada y el pie enlaza a los cuatro textos")
        pg.fill("#nombre", "Ana Pérez")
        pg.fill("#correo", "ana@empresa.com")
        pg.fill("#contrasena", CLAVE)
        pg.click("button[type=submit]")
        pg.wait_for_timeout(400)
        ok("acepta los términos" in pg.locator("#acepto-msg").inner_text() and pg.locator(".barra").count() == 0 and pg.evaluate("document.activeElement.id") == "acepto",
           "sin marcar la casilla no se crea la cuenta, se explica y el foco va a la casilla")
        pg.keyboard.press("Space")
        pg.click("button[type=submit]")
        pg.wait_for_selector(".barra", timeout=10000)
        aviso_ia = pg.locator(".emergente", has_text="confirma qué datos se envían")
        try:
            aviso_ia.wait_for(timeout=8000)  # el aviso llega tras una consulta al servidor: esperar a que aparezca, no un tiempo fijo
        except Exception:  # noqa: BLE001
            pass
        ok(aviso_ia.count() == 1, "con la IA sin confirmar, el panel avisa en vez de enviar datos")

        print("Escenas")
        t = pg.locator(".trabajo").first
        nombres = lambda: t.locator(".escenas .escena:not(.subiendo) .escena-nombre").all_inner_texts()  # noqa: E731
        t.locator("select[id^=marca]").select_option("al-volante")
        t.locator("input[type=file]").set_input_files([str(r) for r in tomas])
        t.locator(".escenas .escena:not(.subiendo)").nth(2).wait_for(timeout=40000)
        ok(nombres() == ["escena1.mp4", "escena2.mp4", "escena3.mp4"] and "3 escenas" in t.locator(".escenas-total").inner_text(), f"tres escenas a la vez, ordenadas por nombre ({nombres()})")
        t.locator("button[aria-label='Subir la escena 3']").click()
        pg.wait_for_timeout(600)
        ok(nombres() == ["escena1.mp4", "escena3.mp4", "escena2.mp4"] and t.locator("button[aria-label='Subir la escena 1']").is_disabled() and t.locator("button[aria-label='Bajar la escena 3']").is_disabled(),
           "se reordenan con los botones (la primera no sube, la última no baja)")
        pg.reload()
        t = pg.locator(".trabajo").first
        t.locator(".escenas .escena").nth(2).wait_for()
        ok(nombres() == ["escena1.mp4", "escena3.mp4", "escena2.mp4"], "el orden se conserva al recargar")
        t.locator("button[aria-label='Quitar la escena 2']").click()
        pg.wait_for_timeout(800)
        ok(nombres() == ["escena1.mp4", "escena2.mp4"], "se quita una escena")

        print("Lo que se escribe enciende lo que corresponde")
        area = t.locator("textarea")
        t.locator(".sugerencias button", has_text="Palabras en grande").click()
        ok(area.evaluate("e => e.value.slice(e.selectionStart, e.selectionEnd)") == "precio, descuento" and "Resalta las palabras: precio, descuento." in area.input_value(), "un atajo escribe una frase completa y deja seleccionado lo que hay que cambiar")
        area.fill("Contador de dinero: muestra una calculadora que sume y reste cada cifra. Agrega transiciones con efecto, efectos de sonido y un logo animado al final.")
        pg.wait_for_timeout(1300)
        activo = lambda k: t.locator(f"input[id^=extra-{k}-]").is_checked()  # noqa: E731
        ok(all(activo(k) for k in ("calculadora", "transiciones", "sonidos", "logo")) and "Lo pediste en tu texto" in t.locator(".extra[data-clave=calculadora]").inner_text(), "calculadora, transiciones, sonidos y logo se encienden solos y dicen por qué")
        ok("Contador de dinero" in t.locator(".formato-ayuda").inner_text() and "todavía no" not in t.locator(".entendido").inner_text(), "el formato automático explica qué eligió y «Esto haré» no dice «todavía no»")
        area.fill(area.input_value() + " Sin transiciones.")
        pg.wait_for_timeout(1300)
        ok(not activo("transiciones") and activo("calculadora"), "«Sin transiciones» las apaga")
        t.locator(".extra[data-clave=calculadora] label.extra-texto").click()
        pg.wait_for_timeout(900)
        pg.reload()
        t = pg.locator(".trabajo").first
        t.locator(".escenas .escena").first.wait_for()
        pg.wait_for_timeout(1200)
        ok(not t.locator("input[id^=extra-calculadora-]").is_checked(), "lo que se toca a mano manda sobre el texto y se conserva al recargar")
        t.locator(".formato", has_text="Antes y después").click()
        pg.wait_for_timeout(900)
        ok(t.locator(".formato", has_text="Antes y después").locator("input").is_checked(), "elegir un formato lo marca")

        print("Logo y menores")
        t.locator(".extra[data-clave=logo] button").click()
        pg.wait_for_selector("dialog[open]")
        pg.locator("dialog button", has_text="Subir logo").click()
        ok("Elige primero" in pg.locator("dialog").inner_text(), "sin imagen, el cuadro del logo la pide")
        pg.set_input_files("dialog #logo-archivo", str(logo))
        pg.locator("dialog button", has_text="Subir logo").click()
        ok("Marca la casilla" in pg.locator("dialog").inner_text(), "sin confirmar los derechos, no se sube")
        pg.locator("dialog label[for=logo-derechos]").click()
        pg.locator("dialog button", has_text="Subir logo").click()
        pg.wait_for_selector("dialog", state="detached", timeout=10000)
        pg.wait_for_timeout(1500)
        ok("Cambiar logo" in t.locator(".extra[data-clave=logo]").inner_text(), "con imagen y derechos el logo se guarda")
        ok(t.locator(".extra-aviso").is_hidden(), "una marca de adultos no pide la autorización de los padres")
        t.locator("select[id^=marca]").select_option("cositas-chulas-kids")
        t.locator(".extra-aviso").wait_for(state="visible", timeout=8000)
        t.locator(".extra-aviso label").click()
        pg.wait_for_timeout(900)
        pg.reload()
        t = pg.locator(".trabajo").first
        t.locator(".escenas .escena").first.wait_for()
        pg.wait_for_timeout(1200)
        ok(t.locator(".extra-aviso").is_visible() and t.locator("input[id^=menores-]").is_checked(), "la marca infantil pide la autorización de los padres y la casilla se conserva")
        t.locator("select[id^=marca]").select_option("al-volante")
        pg.wait_for_timeout(900)

        print("La IA, el costo y los datos")
        pg.click(".avatar")
        pg.locator(".menu-usuario button", has_text="Director con IA").click()
        pg.wait_for_selector("dialog[open] #ia-activa")
        ok("Este mes llevas" in pg.locator("dialog").inner_text() and "≈ US$" in pg.locator("dialog").inner_text() and not pg.locator("#ia-consiente").is_checked(), "el diálogo de IA muestra el costo y la casilla de confirmación sin marcar")
        pg.wait_for_timeout(800)  # la animación de entrada del cuadro termina antes de medir el contraste
        revisar_axe("diálogo de IA")
        if not pg.locator("#ia-activa").is_checked():
            pg.locator("label[for=ia-activa]").click()
        pg.locator("dialog button", has_text="Guardar").click()
        pg.wait_for_timeout(600)
        ok("marca la casilla" in pg.locator("dialog").inner_text().lower(), "activar la IA sin confirmar el envío de datos no se deja")
        pg.locator("label[for=ia-consiente]").click()
        pg.locator("dialog button", has_text="Guardar").click()
        pg.wait_for_selector("dialog", state="detached", timeout=8000)
        pg.wait_for_timeout(1200)
        ok("Con IA: ≈ US$" in t.locator(".trabajo-pie").inner_text(), "ya confirmada, la tarjeta muestra el costo por video junto a «Listo para crear»")
        pg.click(".avatar")
        with pg.expect_download() as descarga:
            pg.locator(".menu-usuario button", has_text="Exportar mis datos").click()
        exportado = json.load(open(descarga.value.path()))
        ok(descarga.value.suggested_filename == "mis-datos-iris.json" and exportado["cuenta"]["correo"] == "ana@empresa.com" and "clave" not in json.dumps(exportado["cuenta"]), "exportar descarga un JSON con la cuenta y sin secretos")
        pg.click(".avatar")
        with contexto.expect_page() as nueva:
            pg.locator(".menu-usuario button", has_text="Privacidad y términos").click()
        ok(nueva.value.url.endswith("/legal/privacidad.html"), "«Privacidad y términos» abre la política")
        nueva.value.wait_for_load_state()
        revisar_axe("política de privacidad", nueva.value)
        nueva.value.close()

        print("Teclado y accesibilidad")
        t.locator("summary", has_text="Más opciones").click()
        revisar_axe("panel con escenas y extras")
        sin_nombre = pg.evaluate("""() => [...document.querySelectorAll('button, a[href], input, select, textarea, [role=button]')].filter((e) => e.offsetParent !== null || e.type === 'file')
          .filter((e) => { const n = (e.getAttribute('aria-label') || e.textContent || e.getAttribute('title') || '').trim(); const l = e.id && document.querySelector(`label[for="${e.id}"]`); const p = e.closest('label'); return !n && !l && !p && e.type !== 'hidden'; })
          .map((e) => e.outerHTML.slice(0, 80))""")
        ok(sin_nombre == [], f"todo lo que se puede pulsar o escribir tiene nombre para un lector de pantalla ({sin_nombre[:2]})")
        sin_alt = pg.evaluate("[...document.querySelectorAll('img')].filter((i) => !i.hasAttribute('alt')).length")
        ok(sin_alt == 0, "todas las imágenes tienen texto alternativo")
        visitados: list[str] = []
        pg.evaluate("window.scrollTo(0, 0)")
        pg.locator("body").click(position={"x": 5, "y": 5})
        for _ in range(90):
            pg.keyboard.press("Tab")
            visitados.append(pg.evaluate("(() => { const e = document.activeElement; const r = e.getBoundingClientRect(); return (e.id || e.getAttribute('aria-label') || e.textContent.trim().slice(0, 30)) + (r.width > 0 ? '' : ' [invisible]'); })()"))
        ok(any("Subir la escena" in v for v in visitados) and any("extra-calculadora" in v for v in visitados) and any("Crear este video" in v for v in visitados) and any("Privacidad" in v for v in visitados),
           "con Tab se llega a las escenas, los extras, el botón de crear y el pie legal")
        ok(not any("[invisible]" in v for v in visitados), "todo lo que recibe el foco se ve")
        pg.click(".avatar")
        pg.keyboard.press("Escape")
        ok(pg.locator(".menu-usuario").is_hidden() and "avatar" in pg.evaluate("document.activeElement.className"), "Esc cierra el menú y devuelve el foco al avatar")

        print("Celular y modo oscuro")
        estado_sesion = contexto.storage_state()
        contexto.close()
        for nombre, cfg in (("oscuro", {"viewport": {"width": 1280, "height": 900}, "color_scheme": "dark"}), ("celular", {"viewport": {"width": 390, "height": 844}, "color_scheme": "light"})):
            c2 = navegador.new_context(storage_state=estado_sesion, bypass_csp=axe is not None, **cfg)
            q = c2.new_page()
            q.goto(f"http://127.0.0.1:{PUERTO}/")
            q.wait_for_selector(".barra")
            q.wait_for_timeout(1500)
            ok(not q.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"), f"sin desplazamiento horizontal ({nombre})")
            revisar_axe(f"panel ({nombre})", q)
            c2.close()
        ok(not errores, f"sin errores en la consola del navegador ({errores[:2]})")

        print("iPhone por Wi-Fi (aparato sin emparejar, pantalla de iPhone)")
        from . import arranque, red
        ip = red.ip_de_esta_red()
        if ip is None:
            print("  · (este equipo no tiene una dirección de red local: se omite)")
        else:
            puerto_red = PUERTO + 2
            conexion = red.Red(ip, puerto_red, None)
            servidor_red, conectores = arranque.servidor_en_red(crear_app(puerto_red, conexion), puerto_red, ip)
            hilo_red = threading.Thread(target=lambda: servidor_red.run(sockets=conectores), daemon=True)
            hilo_red.start()
            for _ in range(100):
                if getattr(servidor_red, "started", False):
                    break
                time.sleep(0.1)
            movil = navegador.new_context(viewport={"width": 390, "height": 844}, color_scheme="light", bypass_csp=axe is not None, is_mobile=True, has_touch=True)
            q = movil.new_page()
            errores_red: list[str] = []
            q.on("pageerror", lambda e: errores_red.append(str(e)))
            q.goto(f"http://{ip}:{puerto_red}/")
            q.wait_for_selector("#codigo")
            ok(q.url.endswith("/emparejar.html"), "sin emparejar, abrir Iris por la red lleva a la página del código")
            ok(q.locator("h1").inner_text() == "Empareja este aparato" and q.locator("label[for=codigo]").count() == 1 and q.evaluate("document.activeElement.id") == "codigo",
               "la página tiene título, campo con etiqueta y el foco ya está en el código")
            ok(q.get_attribute("#codigo", "autocapitalize") == "characters" and q.get_attribute("#codigo", "autocomplete") == "off", "el teclado del iPhone sale en mayúsculas y sin autocompletar")
            ok(not q.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"), "sin desplazamiento horizontal a 390 px")
            revisar_axe("página de emparejamiento", q)
            q.fill("#codigo", "abc")
            q.keyboard.press("Enter")
            ok("8 letras y números" in q.locator("#codigo-msg").inner_text(), "un código incompleto se explica sin enviarse")
            q.fill("#codigo", "ZZZZ-ZZZZ")
            q.keyboard.press("Enter")
            q.locator("#codigo-msg", has_text="no coincide").wait_for(timeout=8000)
            ok("no coincide" in q.locator("#codigo-msg").inner_text() and q.get_attribute("#codigo", "aria-invalid") == "true", "un código equivocado se dice con claridad")
            q.fill("#codigo", conexion.codigo_para_mostrar().lower())
            q.keyboard.press("Enter")
            q.wait_for_selector(".acceso-tarjeta #nombre, .acceso-tarjeta #correo", timeout=10000)
            ok(q.locator(".aviso-red").count() == 1 and "por Wi-Fi" in q.locator(".aviso-red").inner_text(), "emparejado, ve la pantalla de entrada con el aviso de que la conexión no va cifrada")
            revisar_axe("entrada por Wi-Fi con aviso", q)
            ok(not errores_red, f"sin errores de JavaScript en el aparato ({errores_red[:2]})")
            movil.close()
            servidor_red.should_exit = True
            hilo_red.join(timeout=10)
            for conector in conectores:
                conector.close()
        navegador.close()
    servidor.should_exit = True
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    with tempfile.TemporaryDirectory(prefix="iris-datos-pantalla-") as carpeta:
        os.environ["IRIS_DATOS"] = carpeta
        for marca in ("maquetas-estilo", "al-volante", "cositas-chulas-kids"):
            for sub in ("videos/referencias", "videos/propios", "salidas", "analisis"):
                (Path(carpeta) / "empresas" / marca / sub).mkdir(parents=True)
        os.environ["CREADOR_EMPRESAS"] = str(Path(carpeta) / "empresas")
        from servidor.pruebas_pantalla import correr as _correr
        malos = _correr()
    sys.exit(0 if malos is None else 1 if malos else 0)
