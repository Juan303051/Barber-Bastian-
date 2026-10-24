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
    ok(leido["sugerencias"] == {"quitar_pausas": True}, "«quita las pausas» se ofrece como sugerencia, no se aplica solo")
    ok(interprete.leer_prompt("Hazlo antes y después con música")["sugerencias"] == {"formato": "antes-despues", "musica": True}, "antes y después, y música pedida")
    ok(interprete.leer_prompt("quiero el video sin música")["sugerencias"] == {"musica": False}, "«sin música» se entiende como quitarla")
    ok(len(interprete.leer_prompt("pon música y transiciones y texto detrás de la persona")["pendiente"]) == 2, "avisa de lo que todavía no hace (la música ya sí se hace)")
    ok(interprete.leer_prompt("edítalo rápido")["claves"] == [], "un texto sin órdenes no inventa nada")
    ok(interprete.leer_prompt("Comenta la palabra Masterclass en este reel")["cta"] == "MASTERCLASS", "palabra a comentar sin mayúsculas")

    print("Detección en lo que dice el video")
    pasos = interprete._pasos(_palabras("Primero abre la app. Segundo elige tu video. Tercero comparte."))
    ok([n for n, _ in pasos] == [1, 2, 3], "pasos numerados «primero, segundo, tercero»")
    ok(interprete._pasos(_palabras("Espera un segundo y vas a ver esto")) == [], "«un segundo» no es un paso")
    ok(interprete._pasos(_palabras("Primero abre la app y listo")) == [], "un solo paso no se numera")
    ok([n for n, _ in interprete._pasos(_palabras("Paso uno abre. Paso dos cierra."))] == [1, 2], "«paso uno, paso dos»")
    for texto, esperado in (("$3,000", (3000.0, "$", "")), ("3.000", (3000.0, "", "")), ("35%", (35.0, "", "%")), ("$50", (50.0, "$", "")),
                            ("2024", None), ("3.5", None), ("50", None), ("hola", None), ("10.000.000.000", None)):
        ok(interprete._valor(texto) == esperado, f"cifra {texto!r}")
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
            "acento": None, "pendiente": [], "sugerencias": {}}
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

    print("Referencias y pausas")
    perfil = estilo.perfil_de({"ritmo": {"cortes_por_10s": 4.2}, "voz": {"palabras_por_min": 200, "gancho_texto": "hola"}, "duracion": 40, "vertical": True}, "#FF2D55")
    ok(perfil["maxPalabras"] == 2 and perfil["zoom_cada"] == 1 and "Ritmo rápido" in perfil["etiquetas"], "perfil: voz ágil y ritmo rápido")
    ok(estilo.agregar([]) is None and estilo.agregar([perfil, perfil])["cantidad"] == 2, "agregar perfiles")
    ok(pausas.tramos_a_conservar(10.0, [(2.0, 4.0)]) == [(0.0, 2.15), (3.85, 10.0)], "pausas: se acorta el silencio dejando margen")
    ok(pausas.tramos_a_conservar(10.0, [(2.0, 2.3)]) == [(0.0, 10.0)], "pausas: un silencio corto no se toca")

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
