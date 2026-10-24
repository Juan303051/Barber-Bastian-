"""Pruebas sin red ni navegador de las piezas de la app. Se ejecutan con ./creador probar (o: python -m servidor.pruebas)."""
from __future__ import annotations

import sys
from pathlib import Path

from . import estilo, interprete, pausas, seguridad


def _palabras(texto: str, inicio: float = 1.0, ritmo: float = 0.4) -> list:
    salida, t = [], inicio
    for p in texto.split():
        salida.append([round(t, 2), round(t + 0.3, 2), p])
        t += ritmo + (0.5 if p[-1] in ".?!" else 0)
    return salida


def _analisis(texto: str, ancho: int = 576, alto: int = 1024, voz: bool = True) -> dict:
    palabras = _palabras(texto)
    fin = palabras[-1][1] + 0.5 if palabras else 5.0
    return {"duracion": round(fin + 2.0, 2), "ancho": ancho, "alto": alto, "fps": 30, "vertical": alto > ancho,
            "ritmo": {"cortes_por_10s": 1.0}, "audio": {"lufs": -14}, "voz": {"palabras": palabras, "palabras_por_min": 150, "gancho_texto": ""} if voz else None}


def correr() -> list[str]:
    """Devuelve la lista de fallos (vacía si todo va bien) e imprime cada comprobación."""
    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    print("Intérprete del texto")
    leido = interprete.leer_prompt('Resalta las palabras dinero, años y "gratis". Quita las pausas y cierra con Comenta EDITOR. Subtítulos abajo, color azul')
    ok(leido["claves"] == ["dinero", "años", "gratis"], "palabras en grande")
    ok(leido["cta"] == "EDITOR" and leido["posicion"] == "abajo" and leido["acento"] == "#0A84FF", "cierre, posición y color")
    ok("quitar_pausas" in leido["pide"], "«quita las pausas» lo pide el texto")
    pedido = interprete.leer_prompt("Hazlo antes y después con música")
    ok(pedido["formato"] == "antes-despues" and "musica" in pedido["pide"], "antes y después, y música pedida")
    ok("musica" in interprete.leer_prompt("quiero el video sin música")["niega"], "«sin música» se entiende como quitarla")
    avisos = interprete.leer_prompt("pon música y transiciones y texto detrás de la persona")
    ok(len(avisos["pendiente"]) == 1 and "transiciones" in avisos["pide"], "avisa solo de lo que todavía no hace: transiciones y música ya sí se hacen")
    ok(interprete.leer_prompt("edítalo rápido")["claves"] == [], "un texto sin órdenes no inventa nada")
    ok(interprete.leer_prompt("Comenta la palabra Masterclass en este reel")["cta"] == "MASTERCLASS", "palabra a comentar sin mayúsculas")

    print("Lo que se pide en el texto y lo que Iris hará")
    larga = ("CONTADOR DE DINERO: Cada vez que se anuncie una cifra o un valor, muestra una calculadora o contador digital de dinero en pantalla. Los números deben aparecer y "
             "actualizarse en sincronía con la voz. Cuando se anuncie un descuento, gasto o resta, anima el valor disminuyendo. Utiliza cifras grandes. "
             "Agrega transiciones con efecto, efectos de sonido y un logo animado al final.")
    leido = interprete.leer_prompt(larga)
    ok(leido["pide"] == {"calculadora", "transiciones", "sonidos", "logo"} and leido["formato"] == "dinero", f"el texto largo pide calculadora, transiciones, sonidos y logo: {sorted(leido['pide'])}")
    ok(leido["claves"] == [] and leido["pendiente"] == [], "y no inventa «palabras en grande» ni avisos de lo que ya se puede hacer")
    ef = interprete.efectivo(larga, {"_v": 2})
    ok(ef["formato"] == "dinero" and ef["formato_origen"] == "texto" and ef["calculadora"] and ef["transiciones"] and ef["sonidos"] and ef["logo"], "sin tocar nada, lo que pide el texto se aplica")
    ok(ef["origenes"]["calculadora"] == "texto" and ef["origenes"]["acercamientos"] == "defecto", "y se sabe de dónde sale cada valor")
    ef = interprete.efectivo(larga, {"_v": 2, "transiciones": False, "formato": "subtitulos"})
    ok(ef["transiciones"] is False and ef["origenes"]["transiciones"] == "manual" and ef["formato"] == "subtitulos", "lo que la persona tocó a mano manda sobre el texto")
    ef = interprete.efectivo("sin transiciones ni efectos de sonido, sin logo", {"_v": 2})
    ok(ef["transiciones"] is False and ef["sonidos"] is False and ef["logo"] is False, "«sin transiciones, sin efectos de sonido, sin logo» las apaga")
    ef = interprete.efectivo("hazlo rápido", {"_v": 2})
    ok(ef["calculadora"] is None and ef["transiciones"] is None and ef["sonidos"] is None and ef["logo"] is None and ef["formato"] == "subtitulos", "sin pedirlo, esas cuatro las decide el director")
    ef = interprete.efectivo(larga, {"formato": "subtitulos", "quitar_pausas": False, "acercamientos": True, "insignias": True, "contadores": True, "cierre": True,
                                     "color_referencias": False, "musica": True, "ia": True})
    ok(ef["formato"] == "dinero" and ef["calculadora"], "una tarjeta guardada por la versión anterior no bloquea lo que pide el texto")
    ef = interprete.efectivo("", {"quitar_pausas": True, "formato": "antes-despues"})
    ok(ef["quitar_pausas"] and ef["formato"] == "antes-despues", "y lo que sí se apartaba de los valores de entonces se respeta")
    ok(interprete.efectivo("antes y después", {"_v": 2})["formato"] == "antes-despues" and interprete.efectivo("paso a paso", {"_v": 2})["formato"] == "pasos", "el formato se deduce del texto")
    ok(interprete.efectivo("antes y después", {"_v": 2, "formato": "dinero"})["formato"] == "dinero", "un formato elegido a mano gana al texto")
    ok(interprete.efectivo("", {"_v": 2, "formato": "dinero"})["calculadora"] is True, "elegir «Contador de dinero» enciende la calculadora")
    fin = interprete.resolver(interprete.efectivo("hazlo", {"_v": 2}), {"calculadora": {"usar": True}, "transiciones": {"usar": True}, "sonidos": {"nivel": "sutil"}, "logo": {"usar": True}}, True, True)
    ok(fin["calculadora"] and fin["transiciones"] and fin["sonidos"] and fin["logo"], "lo que queda en «decide el director» lo completa el plan")
    fin = interprete.resolver(interprete.efectivo("sin transiciones", {"_v": 2}), {"transiciones": {"usar": True}, "logo": {"usar": True}}, False, False)
    ok(fin["transiciones"] is False and fin["logo"] is False and fin["calculadora"] is False, "el plan no pasa por encima de lo que la persona apagó, ni pone logo si no hay, ni calculadora sin cifras")
    resumen = " | ".join(f["texto"] for f in interprete.resumen(interprete.efectivo(larga, {"_v": 2}), tiene_logo=False))
    ok("falta subir el logo" in resumen and "Calculadora" in resumen and "todavía no" not in resumen, "el panel «Esto entendí» cuenta lo que haré y avisa si falta el logo")

    print("Detección en lo que dice el video")
    pasos = interprete._pasos(_palabras("Primero abre la app. Segundo elige tu video. Tercero comparte."))
    ok([n for n, _ in pasos] == [1, 2, 3], "pasos numerados «primero, segundo, tercero»")
    ok(interprete._pasos(_palabras("Espera un segundo y vas a ver esto")) == [], "«un segundo» no es un paso")
    ok(interprete._pasos(_palabras("Primero abre la app y listo")) == [], "un solo paso no se numera")
    ok([n for n, _ in interprete._pasos(_palabras("Paso uno abre. Paso dos cierra."))] == [1, 2], "«paso uno, paso dos»")
    for texto, esperado in (("$3,000", (3000.0, "$", "")), ("3.000", (3000.0, "", "")), ("35%", (35.0, "", "%")), ("$50", (50.0, "$", "")),
                            ("2024", None), ("3.5", None), ("50", None), ("hola", None), ("10.000.000.000", None)):
        ok(interprete._valor(texto) == esperado, f"cifra {texto!r}")
    cd = interprete._contadores([[2.0, 2.4, "cuesta"], [2.4, 2.8, "8"], [2.8, 3.4, ".500"], [3.4, 4.0, ".000"], [4.0, 4.4, "pesos"], [9.0, 9.4, "300"], [9.4, 9.8, "mil"], [9.8, 10.2, "pesos"]], 20.0)
    ok([c["hasta"] for c in cd] == [8_500_000, 300_000] and cd[0]["prefijo"] == "$", "contadores: entiende «8 .500 .000 pesos» y «300 mil pesos»")
    ok(interprete._contadores([[2.0, 2.4, "seis"], [2.4, 2.8, "meses"], [6.0, 6.4, "dos"], [6.4, 6.8, "años"]], 20.0) == [], "contadores: «seis meses» y «dos años» no son cifras para mostrar")
    contadores = interprete._contadores(_palabras("Gané 3000 dólares. Luego 5000 más. Después 7000 y 9000 y 11000"), 40.0)
    ok(1 <= len(contadores) <= 3 and contadores[0]["prefijo"] == "$" and contadores[0]["hasta"] == 3000, "contadores: máximo 3, con $ si dice dólares")
    ok(all(b["ini"] - a["ini"] >= 4 for a, b in zip(contadores, contadores[1:])), "contadores separados al menos 4 s")
    ok(interprete._cierre(_palabras("Comenta la palabra Masterclass en este reel"), 30.0, None)[0] == "MASTERCLASS", "palabra de cierre dicha en el video")
    ok(interprete._cierre(_palabras("Comentame EDITOR y te lo envío"), 30.0, None)[0] == "EDITOR", "«comentame EDITOR»")
    ok(interprete._cierre(_palabras("Comenta aquí abajo"), 30.0, None)[0] is None, "«comenta aquí abajo» sin palabra clave no inventa una")
    ok(interprete._cierre(_palabras("Hola a todos"), 30.0, "PRECIO") == ("PRECIO", 26.5), "palabra pedida en el texto: cierre en los últimos 3.5 s")

    print("Guion final")
    base = {"formato": "subtitulos", "quitar_pausas": False, "acercamientos": True, "insignias": True, "contadores": True, "cierre": True,
            "color_referencias": False, "idioma": None, "borrador": False, "claves": [], "cta": None, "posicion": None, "max_palabras": None,
            "acento": None, "pendiente": [], "calculadora": False, "transiciones": False, "sonidos": False, "logo": False, "origenes": {}}
    texto = "Hola amigos. Primero abre la app. Segundo elige tu video con 3000 dólares. Tercero comparte. Comenta EDITOR y te lo envío."
    from importlib import import_module
    revisor = import_module("guion")
    guion, notas = interprete.construir_guion("x", base, _analisis(texto), None, {}, "marca/videos/propios/x.mp4")
    ok(revisor.revisar(guion) == [], "el guion pasa la revisión de Remotion")
    ok(guion["diseno"] == "pleno" and "ancho" not in guion, "vertical y a tamaño completo por defecto")
    ok([c["numero"] for c in guion["capas"] if c["tipo"] == "insignia"] == [1, 2, 3], "tres insignias")
    ok(any(c["tipo"] == "contador" and c["hasta"] == 3000 for c in guion["capas"]), "un contador para 3000")
    cierre = [e for e in guion["escenas"] if e["tipo"] == "cta"]
    ok(len(cierre) == 1 and cierre[0]["clave"] == "EDITOR" and cierre[0]["ini"] is not None, "cierre con la palabra que se dice")
    ok(all(p[0] < cierre[0]["ini"] for p in guion["palabras"]), "los subtítulos paran cuando empieza el cierre")
    ok(abs(cierre[0]["ini"] + cierre[0]["duracion"] - guion["duracion"]) < 0.02, "el cierre llega hasta el final del video")
    ok(len(guion["zooms"]) >= 1 and all(z["fin"] > z["ini"] for z in guion["zooms"]), "acercamientos con tiempos válidos")
    guion, _ = interprete.construir_guion("x", {**base, "formato": "antes-despues", "borrador": True, "acento": "#FF2D55", "cierre": False}, _analisis(texto), None,
                                          {"fondo": "#101010"}, "m/x.mp4")
    ok(guion["diseno"] == "antes-despues" and (guion["ancho"], guion["alto"]) == (540, 960), "antes y después en borrador rápido (540×960)")
    ok(guion["marca"]["colores"] == {"fondo": "#101010", "acento": "#FF2D55"} and not guion["escenas"], "el color pedido se suma a los de la marca; sin cierre si se apaga")
    guion, _ = interprete.construir_guion("x", base, _analisis(texto, 1920, 1080), None, {}, "m/x.mp4")
    ok((guion["ancho"], guion["alto"]) == (1920, 1080), "un video horizontal se queda horizontal")
    guion, notas = interprete.construir_guion("x", base, _analisis("", voz=False), None, {}, "m/x.mp4")
    ok("palabras" not in guion and any("No encontré voz" in n for n in notas) and revisor.revisar(guion) == [], "video sin voz: solo lo visual y un aviso")
    guion, _ = interprete.construir_guion("x", {**base, "claves": ["amigos"], "max_palabras": 1, "posicion": "arriba", "insignias": False, "contadores": False, "acercamientos": False},
                                          _analisis(texto), None, {}, "m/x.mp4")
    ok(guion["estiloPalabras"]["maxPalabras"] == 1 and guion["estiloPalabras"]["posicion"] == "arriba" and "amigos" in guion["estiloPalabras"]["claves"], "claves, palabras por vez y posición del texto")
    ok(not [c for c in guion["capas"]] and not guion["zooms"], "apagar insignias, contadores y acercamientos los quita")
    guion, _ = interprete.construir_guion("x", {**base, "color_referencias": True}, _analisis(texto), {"acento": "#34C759", "maxPalabras": 2, "zoom_cada": 1}, {}, "m/x.mp4")
    ok(guion["marca"]["colores"]["acento"] == "#34C759" and guion["estiloPalabras"]["maxPalabras"] == 2, "lo aprendido de las referencias se aplica")

    print("Calculadora, transiciones y logo en el guion")
    dinero = [[1.0, 1.3, "Cuesta"], [1.3, 1.6, "8"], [1.6, 2.2, ".500"], [2.2, 2.9, ".000"], [2.9, 3.2, "pesos."], [4.0, 4.3, "Tiene"], [4.3, 4.6, "un"], [4.6, 5.2, "descuento"],
              [5.2, 5.4, "de"], [5.4, 5.6, "un"], [5.6, 6.1, "millón"], [6.1, 6.4, "de"], [6.4, 6.9, "pesos."], [8.0, 8.3, "Te"], [8.3, 8.7, "queda"], [8.7, 8.9, "en"],
              [8.9, 9.1, "7"], [9.1, 9.7, ".500"], [9.7, 10.3, ".000"], [10.3, 10.7, "pesos."]]
    analisis_d = {"duracion": 14.0, "ancho": 576, "alto": 1024, "fps": 30, "vertical": True, "voz": {"palabras": dinero}}
    cfg = {**base, "calculadora": True, "transiciones": True, "logo": True, "contadores": False, "cierre": False}
    guion, notas = interprete.construir_guion("x", cfg, analisis_d, None, {}, "m/x.mp4", plan={"transiciones": {"estilo": "barrido"}}, cortes=[{"t": 4.0, "tipo": "escena"}, {"t": 4.5, "tipo": "pausa"}, {"t": 9.0, "tipo": "escena"}],
                                              logo="m/logo.png")
    calc = [c for c in guion["capas"] if c["tipo"] == "calculadora"]
    ok(revisor.revisar(guion) == [], "el guion con calculadora, transiciones y logo pasa la revisión")
    ok(len(calc) == 1 and [e["op"] for e in calc[0]["eventos"]] == ["fijar", "restar", "total"] and calc[0]["eventos"][1]["a"] == 7_500_000, "calculadora: fija 8,5 M, resta 1 M y confirma 7,5 M")
    ok(not any(c["tipo"] == "contador" for c in guion["capas"]), "con calculadora no se duplican los contadores")
    transiciones = [c for c in guion["capas"] if c["tipo"] == "transicion"]
    ok(len(transiciones) == 2 and all(abs((c["ini"] + c["fin"]) / 2 - t) < 0.01 for c, t in zip(transiciones, (4.0, 9.0))), "transiciones solo sobre cortes, separadas (el corte de 4,5 s queda muy pegado y se omite)")
    logos = [c for c in guion["capas"] if c["tipo"] == "logo"]
    ok(len(logos) == 1 and logos[0]["archivo"] == "m/logo.png" and logos[0]["fin"] <= 14.0 and "m/logo.png" in revisor.recursos(guion), "logo animado al final y listado entre los recursos")
    guion, notas = interprete.construir_guion("x", {**cfg, "cierre": True, "cta": "MOTO"}, analisis_d, None, {}, "m/x.mp4", logo="m/logo.png")
    ok(guion["marca"]["logo"] == "m/logo.png" and not [c for c in guion["capas"] if c["tipo"] == "logo"], "con cierre, el logo se anima dentro del cierre")
    ok(max(c["fin"] for c in guion["capas"] if c["tipo"] == "calculadora") <= [e for e in guion["escenas"] if e["tipo"] == "cta"][0]["ini"] + 0.01, "la calculadora termina cuando empieza el cierre")
    guion, notas = interprete.construir_guion("x", cfg, analisis_d, None, {}, "m/x.mp4", cortes=[])
    ok(any("no tiene cortes" in n for n in notas) and any("no tiene logo" in n for n in notas), "sin cortes ni logo, lo dice en vez de ignorarlo")
    guion, notas = interprete.construir_guion("x", {**cfg, "transiciones": False}, _analisis("Hola amigos. Esto no tiene precios."), None, {}, "m/x.mp4")
    ok(any("no oí cifras de dinero" in n for n in notas) and not any(c["tipo"] == "calculadora" for c in guion["capas"]), "sin cifras de dinero no hay calculadora y se dice")
    guion, _ = interprete.construir_guion("x", {**cfg, "transiciones": False, "logo": False}, analisis_d, None, {}, "m/x.mp4",
                                          plan={"calculadora": {"usar": True, "ajustes": [{"t": 5.4, "op": "mostrar"}]}})
    ok([e["op"] for e in [c for c in guion["capas"] if c["tipo"] == "calculadora"][0]["eventos"]][:2] == ["fijar", "mostrar"], "el director puede corregir qué hace una cifra; el valor lo sigue leyendo el código")
    ok(revisor.revisar({**guion, "capas": [{"tipo": "calculadora", "ini": 1, "fin": 3, "eventos": [{"t": 1, "dur": 1, "op": "restar", "valor": 5}]}]}) != [], "la revisión rechaza una calculadora sin los valores de partida y llegada")

    print("Referencias y pausas")
    perfil = estilo.perfil_de({"ritmo": {"cortes_por_10s": 4.2}, "voz": {"palabras_por_min": 200, "gancho_texto": "hola"}, "duracion": 40, "vertical": True}, "#FF2D55")
    ok(perfil["maxPalabras"] == 2 and perfil["zoom_cada"] == 1 and "Ritmo rápido" in perfil["etiquetas"], "perfil: voz ágil y ritmo rápido")
    ok(estilo.agregar([]) is None and estilo.agregar([perfil, perfil])["cantidad"] == 2, "agregar perfiles")
    ok(pausas.tramos_a_conservar(10.0, [(2.0, 4.0)]) == [(0.0, 2.15), (3.85, 10.0)], "pausas: se acorta el silencio dejando margen")
    ok(pausas.tramos_a_conservar(10.0, [(2.0, 2.3)]) == [(0.0, 10.0)], "pausas: un silencio corto no se toca")
    tramos = [(0.0, 2.15), (3.85, 10.0)]
    ok(pausas.remapear(1.0, tramos) == 1.0 and abs(pausas.remapear(5.0, tramos) - 3.3) < 1e-9 and pausas.remapear(3.0, tramos) == 2.15, "pausas: un instante de la toma original se lleva a la toma sin pausas")
    ok(pausas.cortes_de(tramos) == [2.15] and pausas.cortes_de([(0.0, 5.0)]) == [], "pausas: los cortes quedan donde se unieron los tramos")

    print("Seguridad")
    sal, clave = seguridad.crear_clave("una-clave-larga-1")
    ok(seguridad.verificar_clave("una-clave-larga-1", sal, clave) and not seguridad.verificar_clave("otra", sal, clave) and not seguridad.verificar_clave("x", None, None), "contraseñas con scrypt")
    ok(seguridad.validar_registro("a@b.co", "Ana", "buena-clave-9") == {} and set(seguridad.validar_registro("mal", "", "1")) == {"correo", "nombre", "contrasena"}, "validación del registro")
    ok(seguridad.host_permitido("localhost:8765", 8765) and not seguridad.host_permitido("evil.com", 8765) and not seguridad.host_permitido(None, 8765), "solo se atiende a localhost")
    ok(seguridad.origen_permitido("http://127.0.0.1:8765", None, 8765) and not seguridad.origen_permitido("http://127.0.0.1:9999", None, 8765)
       and not seguridad.origen_permitido("https://evil.com", None, 8765) and not seguridad.origen_permitido(None, "cross-site", 8765), "origen de las peticiones")

    print("Celular por cable (con un adb de mentira)")
    import contextlib
    import io
    import os
    import stat
    import tempfile
    from . import arranque
    with tempfile.TemporaryDirectory(prefix="iris-adb-") as carpeta:
        registro = Path(carpeta) / "llamadas.txt"
        falso = Path(carpeta) / "adb"
        falso.write_text('#!/bin/sh\necho "$@" >> "' + str(registro) + '"\ncase "$*" in\n  *devices*) printf "List of devices attached\\n$FAKE_ADB_DISPOSITIVOS\\n" ;;\nesac\nexit 0\n')
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        original = arranque._buscar_adb
        try:
            arranque._buscar_adb = lambda: str(falso)
            os.environ["FAKE_ADB_DISPOSITIVOS"] = "ABC123\\tdevice"
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = arranque.celular(abrir_servidor=False)
            llamadas = registro.read_text().splitlines()
            ok(codigo == 0 and any(l.startswith("-s ABC123 reverse tcp:") for l in llamadas), "con un celular listo, conecta el puerto por el cable (adb reverse)")
            ok(any("shell am start" in l and "http://127.0.0.1:" in l for l in llamadas), "y le abre Iris en su navegador")
            ok("Mantén esta ventana" not in salida.getvalue() and "127.0.0.1" in salida.getvalue(), "dice en claro qué hizo")
            os.environ["FAKE_ADB_DISPOSITIVOS"] = "XYZ\\tunauthorized"
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = arranque.celular(abrir_servidor=False)
            ok(codigo == 1 and "Permitir" in salida.getvalue(), "si el celular no autorizó, explica qué pulsar en la pantalla")
            os.environ["FAKE_ADB_DISPOSITIVOS"] = ""
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = arranque.celular(abrir_servidor=False)
            ok(codigo == 1 and "Depuración por USB" in salida.getvalue(), "si no hay celular, explica cómo conectarlo")
            os.environ["FAKE_ADB_DISPOSITIVOS"] = "A1\\tdevice\\nB2\\tdevice"
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = arranque.celular(abrir_servidor=False)
            ok(codigo == 1 and "varios celulares" in salida.getvalue(), "con dos celulares no adivina cuál usar")
            arranque._buscar_adb = lambda: None
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = arranque.celular(abrir_servidor=False)
            ok(codigo == 1 and "brew install" in salida.getvalue() and "iPhone" in salida.getvalue(), "sin adb, explica cómo instalarlo y avisa de que el iPhone es otra vía")
        finally:
            arranque._buscar_adb = original
            os.environ.pop("FAKE_ADB_DISPOSITIVOS", None)
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.exit(1 if correr() else 0)
