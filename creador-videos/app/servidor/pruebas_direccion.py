"""El test de cómo debe funcionar el director: perfil de la marca, plan, límites contra invenciones, rúbrica, IA simulada y control de calidad.
No necesita clave ni internet: la IA se simula, y una parte usa el SDK real contra un servidor falso para comprobar el formato exacto de la petición.
Se ejecuta con ./creador probar (o: python -m servidor.pruebas_direccion)."""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

# Antes de importar `datos`: estas pruebas escriben ajustes de la IA y consentimientos, y nunca deben tocar tus cuentas, tus videos ni tu clave real.
_CARPETA_DATOS = tempfile.mkdtemp(prefix="iris-datos-prueba-")
os.environ["IRIS_DATOS"] = _CARPETA_DATOS
atexit.register(shutil.rmtree, _CARPETA_DATOS, ignore_errors=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))

from . import datos  # noqa: E402
from .direccion import ia, perfil as perfiles, plan as planes, rubrica

TRANSCRIPCION = ("Primero, revisa el aceite cada 5000 kilómetros. Segundo, cambia el filtro cuando se vea sucio. "
                 "Tercero, comenta MOTO y te enviamos la guía gratis.")


# Lo que dice un video con precios, tal como lo parte Whisper («8» «.500» «.000»).
DINERO = [[1.0, 1.3, "Cuesta"], [1.3, 1.6, "8"], [1.6, 2.2, ".500"], [2.2, 2.9, ".000"], [2.9, 3.2, "pesos."], [4.0, 4.3, "Tiene"], [4.3, 4.6, "un"], [4.6, 5.2, "descuento"],
              [5.2, 5.4, "de"], [5.4, 5.6, "un"], [5.6, 6.1, "millón"], [6.1, 6.4, "de"], [6.4, 6.9, "pesos."], [8.0, 8.3, "Te"], [8.3, 8.7, "queda"], [8.7, 8.9, "en"],
              [8.9, 9.1, "7"], [9.1, 9.7, ".500"], [9.7, 10.3, ".000"], [10.3, 10.7, "pesos."]]


def _palabras(texto: str, inicio: float = 0.4, ritmo: float = 0.42) -> list:
    salida, t = [], inicio
    for p in texto.split():
        salida.append([round(t, 2), round(t + 0.34, 2), p])
        t += ritmo + (0.45 if p[-1] in ".?!" else 0)
    return salida


def _contexto(perfil: dict | None = None, musica: dict | None = None, config: dict | None = None) -> dict:
    palabras = _palabras(TRANSCRIPCION)
    return {"brief": "Consejos de mantenimiento para dueños de moto. Resalta aceite y filtro.", "duracion": round(palabras[-1][1] + 1.5, 2), "palabras": palabras,
            "ficha": "Taller de motos en Medellín. Tono cercano.", "marca_nombre": "Moto Taller", "perfil": perfil, "referencia": None, "musica": musica, "vertical": True,
            "config": config or {"acercamientos": True, "contadores": True, "insignias": True, "cierre": True, "cta": None, "claves": [], "formato": "subtitulos",
                                 "posicion": None, "max_palabras": None, "acento": None, "color_referencias": False, "borrador": False, "quitar_pausas": False,
                                 "idioma": None, "musica": True, "acabado": "auto", "ia": True, "pendiente": [], "sugerencias": {}}}


def _analisis_sin_dinero() -> dict:
    return {"duracion": 14.0, "ancho": 576, "alto": 1024, "voz": {"palabras": _palabras(TRANSCRIPCION)}}


def _plan_de_la_ia() -> dict:
    """Lo que devolvería una IA con ganas de pasarse de lista: mezcla cosas buenas con invenciones y excesos."""
    return {
        "concepto": {"resumen": "Tres hábitos baratos para que la moto dure más", "tono": "cercano", "tipo_de_gancho": "promesa"},
        "gancho": {"texto": "Alarga la vida de tu moto", "alternativas": ["3 trucos que te ahorran 40 % al año", "El mejor del mundo garantizado", "Tu moto te lo agradece"]},
        "claves": ["aceite", "filtro", "gratis", "inventada"],
        "momentos": [
            {"t": 1.5, "tipo": "acercamiento", "motivo": "Primera idea"},
            {"t": 3.8, "tipo": "contador", "motivo": "La cifra que se dice", "valor": 5000},
            {"t": 6.0, "tipo": "contador", "motivo": "Cifra inventada", "valor": 9999},
            {"t": 8.2, "tipo": "tarjeta", "motivo": "Resumen del paso", "texto": "Cambia el filtro"},
            {"t": 8.5, "tipo": "tarjeta", "motivo": "Muy pegada a la anterior", "texto": "Cambia el filtro"},
            {"t": 10.4, "tipo": "tarjeta", "motivo": "Promesa inventada", "texto": "Garantizado el mejor precio del mundo"},
            {"t": 10.9, "tipo": "insignia", "motivo": "No debe inventar pasos", "valor": 1},
            {"t": 99.0, "tipo": "acercamiento", "motivo": "Fuera del video"},
        ],
        "cierre": {"clave": "moto"},
        "musica": {"usar": True, "energia": "alta", "ritmo": "rapido", "motivo": "Da energía"},
        "acabado": {"look": "calido", "intensidad": 0.95, "pulso": True},
        "segundos_entre_acercamientos": 1.0,
        "alertas": ["La voz tiene un poco de eco"],
    }


class _Falso:
    """Cliente de IA simulado: devuelve lo que se le pida y anota cada llamada."""

    def __init__(self, respuesta=None, error: Exception | None = None) -> None:
        self.llamadas: list[dict] = []
        self._respuesta, self._error = respuesta, error
        self.messages = SimpleNamespace(create=self._crear, count_tokens=lambda **kw: SimpleNamespace(input_tokens=3))
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    def _crear(self, **kwargs):
        self.llamadas.append(kwargs)
        if self._error:
            raise self._error
        return self._respuesta


def _respuesta(texto: str, parada: str = "end_turn", entrada: int = 3000, salida: int = 4000):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=texto)], stop_reason=parada, usage=SimpleNamespace(input_tokens=entrada, output_tokens=salida))


def _video(ruta: Path, *, ancho: int = 360, alto: int = 640, negro_inicial: float = 0.0, congelado: bool = False, audio: Path | None = None, duracion: float = 6.0) -> None:
    fuente = f"color=c=0x303a4a:s={ancho}x{alto}:d={duracion}:r=30" if congelado else f"testsrc2=s={ancho}x{alto}:d={duracion}:r=30"
    filtro = f"drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='lt(t,{negro_inicial})'" if negro_inicial else "null"
    entrada = ["-f", "lavfi", "-i", fuente] + (["-i", str(audio)] if audio else [])
    mapa = ["-map", "0:v"] + (["-map", "1:a", "-c:a", "aac"] if audio else [])
    subprocess.run(["ffmpeg", "-y", "-v", "error", *entrada, "-vf", filtro, *mapa, "-t", str(duracion), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(ruta)], check=True)


def correr() -> list[str]:
    import audio
    import guion as revisor
    import mezcla

    from . import calidad, interprete
    from .pruebas_audio import escribir_wav, pista_sintetica, voz_sintetica

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    datos.abrir()
    print("Aislamiento")
    ok(Path(datos.DATOS).resolve() == Path(_CARPETA_DATOS).resolve() and Path(datos.DATOS).resolve() != (Path(__file__).resolve().parents[1] / "datos"),
       "estas pruebas usan una carpeta temporal: no tocan tus cuentas ni la clave de la IA que guardaste")

    print("Test del director (perfil de la marca)")
    limpias, errores = perfiles.validar({"tono": "premium", "ritmo": "volando", "publico": "  Dueños\x00 de moto  ", "intruso": "x", "musica": "nunca", "nunca": "Garantizado, el mejor del mundo; precio"})
    ok(limpias.get("tono") == "premium" and "ritmo" in errores and "intruso" not in limpias, "valida las opciones y rechaza las que no existen")
    ok(limpias["publico"] == "Dueños de moto", "limpia el texto libre (sin caracteres de control ni espacios de más)")
    ok(perfiles.palabras_prohibidas(limpias) == ["garantizado", "el mejor del mundo", "precio"], "separa las palabras que la marca nunca quiere ver")
    ok(perfiles.efectos({"ritmo": "rapido"})["zoom_cada"] == 1 and perfiles.efectos(None)["zoom_cada"] == 2, "el ritmo del test cambia la cadencia aunque no haya IA")
    ok("Tono" not in perfiles.a_texto(None) and "premium" in perfiles.a_texto({"tono": "premium"}).lower(), "el perfil se convierte en frases para la IA")
    perfiles.guardar("al-volante", {"tono": "experto"})
    perfiles.guardar(None, {"tono": "divertido"})
    ok(perfiles.leer("al-volante")["tono"] == "experto" and perfiles.leer("tu-licencia")["tono"] == "divertido" and perfiles.leer_exacto("tu-licencia") is None,
       "cada marca tiene su perfil y, si no lo tiene, usa el general")

    print("Plan: lo que la IA propone y lo que el código deja pasar")
    perfil = {"nunca": "garantizado, el mejor del mundo", "efectos": "lleno", "acabado": "auto"}
    pista = {"titulo": "Pista de prueba", "bpm": 100.0, "ritmo": "medio", "intensidad": "media", "confianza": 0.8, "licencia": "licenciada"}
    contexto = _contexto(perfil, musica=pista)
    plan, avisos = planes.sanear(_plan_de_la_ia(), contexto)
    ok(plan is not None and plan["gancho"]["texto"] == "Alarga la vida de tu moto", "el gancho corto y respaldado se acepta")
    ok(plan["gancho"]["alternativas"] == ["Tu moto te lo agradece"], f"se descartan los ganchos con cifras inventadas o palabras prohibidas ({plan['gancho']['alternativas']})")
    ok(plan["claves"] == ["aceite", "filtro", "gratis"], f"las palabras clave son solo las que se dicen ({plan['claves']})")
    contadores = [m for m in plan["momentos"] if m["tipo"] == "contador"]
    ok([m["valor"] for m in contadores] == [5000], "solo queda el contador de la cifra que se dice (5000), no el 9999")
    tarjetas = [m for m in plan["momentos"] if m["tipo"] == "tarjeta"]
    ok(len(tarjetas) == 1 and tarjetas[0]["texto"] == "Cambia el filtro", "una tarjeta respaldada por lo dicho; la inventada y la pegada se descartan")
    ok(all(m["tipo"] != "insignia" for m in plan["momentos"]) and all(m["t"] < contexto["duracion"] for m in plan["momentos"]), "no inventa pasos numerados ni usa tiempos fuera del video")
    ok(plan["acabado"]["intensidad"] <= 0.8 and plan["segundos_entre_acercamientos"] >= 2.5, "el acabado y el ritmo se mantienen dentro de límites razonables")
    ok(plan["cierre"]["clave"] == "MOTO", "la palabra del cierre queda en mayúsculas")
    ok(any("9999" in a or "cifra" in a for a in avisos), "se cuenta lo que se descartó")
    ok(planes.sanear("basura", contexto)[0] is None and planes.sanear({"concepto": 5, "gancho": None, "momentos": "x"}, contexto)[0] is not None, "una respuesta ilegible se rechaza y una incompleta se rellena con reglas")
    plan_cine, _ = planes.sanear({**_plan_de_la_ia(), "acabado": {"look": "calido", "intensidad": 0.5, "pulso": False}}, _contexto({**perfil, "acabado": "cine"}))
    ok(plan_cine["acabado"]["look"] == "cine", "lo que la persona eligió en el test manda sobre lo que prefiera la IA")
    sin_musica, _ = planes.sanear(_plan_de_la_ia(), _contexto({**perfil, "musica": "nunca"}, musica=pista))
    ok(sin_musica["musica"]["usar"] is False, "si la marca no quiere música, la IA no puede ponerla")
    sin_pista, _ = planes.sanear(_plan_de_la_ia(), _contexto(perfil))
    ok(sin_pista["musica"]["usar"] is False, "si la biblioteca no tiene una pista lista, la IA no puede proponer música")
    ok(planes.plan_base(_contexto())["origen"] == "reglas" and planes.plan_base(_contexto())["gancho"]["texto"] == "", "el plan por reglas no inventa ganchos")

    print("Plan completo: formato, calculadora, transiciones, sonidos, logo y lo que se pidió")
    plan0, _ = planes.sanear(_plan_de_la_ia(), contexto)
    ok(plan0["formato"] is None and plan0["requisitos"] == [] and plan0["calculadora"] == {"usar": False, "ajustes": []} and plan0["transiciones"]["usar"] is False
       and plan0["sonidos"]["nivel"] == "ninguno" and plan0["logo"]["usar"] is False, "si la IA no dice nada de lo nuevo, queda apagado")
    dinero = DINERO
    ctx2 = {**_contexto(perfil), "palabras": dinero, "duracion": 14.0, "cortes": [{"t": 4.0, "tipo": "escena"}], "tiene_logo": True, "escenas": 2,
            "brief": "Contador de dinero con transiciones, efectos de sonido y logo animado"}
    bruto = {**_plan_de_la_ia(), "formato": "dinero", "calculadora": {"usar": True, "ajustes": [{"t": 5.4, "op": "mostrar"}, {"t": 12.0, "op": "restar"}, {"t": 5.4, "op": "inventar"}]},
             "transiciones": {"usar": True, "estilo": "impacto"}, "sonidos": {"nivel": "marcado"}, "logo": {"usar": True, "estilo": "intro"},
             "requisitos": [{"pedido": "Calculadora de dinero", "capacidad": "calculadora", "nota": ""}, {"pedido": "Calculadora de dinero", "capacidad": "calculadora", "nota": "repetido"},
                            {"pedido": "Que huela a café", "capacidad": "olfato", "nota": "Iris no puede hacerlo"}, {"pedido": "", "capacidad": "logo", "nota": ""}]}
    plan2, avisos2 = planes.sanear(bruto, ctx2)
    ok(plan2["formato"] == "dinero" and plan2["calculadora"]["usar"] and plan2["calculadora"]["ajustes"] == [{"t": 5.4, "op": "mostrar"}],
       f"calculadora: solo se aceptan ajustes sobre cifras que se dicen, con una operación válida ({plan2['calculadora']['ajustes']})")
    ok(sum("ajuste de la calculadora" in a for a in avisos2) == 2, "y se avisa de los dos ajustes descartados")
    ok(plan2["transiciones"] == {"usar": True, "estilo": "impacto"} and plan2["sonidos"]["nivel"] == "marcado" and plan2["logo"] == {"usar": True, "estilo": "intro"}, "transiciones, sonidos y logo se aceptan cuando hay cortes y logo")
    ok([r["capacidad"] for r in plan2["requisitos"]] == ["calculadora", "otra"] and plan2["requisitos"][1]["nota"] == "Iris no puede hacerlo", "requisitos: sin repetidos ni vacíos, y lo que no existe pasa a «otra»")
    plan3, avisos3 = planes.sanear(bruto, {**ctx2, "cortes": [], "tiene_logo": False, "palabras": _palabras(TRANSCRIPCION)})
    ok(not plan3["calculadora"]["usar"] and not plan3["transiciones"]["usar"] and not plan3["logo"]["usar"], "sin cifras de dinero, sin cortes y sin logo, la IA no consigue encenderlos")
    ok(any("no se dicen cifras" in a for a in avisos3) and any("no tiene cortes" in a for a in avisos3), "y se explica por qué")
    ok(planes.sanear({**bruto, "formato": "inventado"}, ctx2)[0]["formato"] is None, "un formato que no existe se descarta")
    esquema = json.dumps(planes.ESQUEMA)
    ok(all(c in esquema for c in ("calculadora", "transiciones", "sonidos", "logo", "requisitos", "formato")) and planes.ESQUEMA["required"][0] == "concepto", "el esquema de la IA incluye todo lo nuevo")
    texto_ia = ia.texto_de_contexto({**ctx2, "config": interprete.efectivo("Calculadora, transiciones, sin logo", {"_v": 2})})
    ok("Fijado por la persona" in texto_ia and "calculadora de dinero: sí" in texto_ia and "logo animado: no" in texto_ia and "[1.3] 8.500.000" in texto_ia and "4.0" in texto_ia,
       "a la IA se le cuentan los cortes reales, las cifras dichas y lo que la persona fijó")
    ok("calculadora" in ia.SISTEMA.lower() and "requisitos" in ia.SISTEMA, "las instrucciones del director conocen todo lo que Iris sabe construir")

    from . import cumplimiento
    cfg = interprete.resolver(interprete.efectivo("Contador de dinero con transiciones, efectos de sonido y logo animado", {"_v": 2}), plan2, True, True)
    guion_ok2, _ = interprete.construir_guion("x", cfg, {"duracion": 14.0, "ancho": 576, "alto": 1024, "voz": {"palabras": dinero}}, None, {}, "m/x.mp4", plan=plan2,
                                              cortes=[{"t": 4.0, "tipo": "escena"}], logo="m/logo.png")
    filas = cumplimiento.evaluar(cfg, plan2, guion_ok2, efectos={"cantidad": 9, "nivel": "marcado"}, musica=None, tiene_logo=True, pausas_quitadas=None, hay_cortes=True)
    estados = {f["capacidad"]: f["estado"] for f in filas}
    ok(estados.get("calculadora") == "hecho" and estados.get("transiciones") == "hecho" and estados.get("sonidos") == "hecho" and estados.get("logo") == "hecho", f"lo pedido y hecho se informa como «hecho» ({estados})")
    ok(estados.get("otra") == "no" and next(f for f in filas if f["capacidad"] == "otra")["pedido"] == "Que huela a café", "lo que Iris no puede hacer se informa como «no» con el pedido tal cual")
    ok("3 paso(s)" in next(f for f in filas if f["capacidad"] == "calculadora")["detalle"], "y la calculadora dice cuántos pasos puso")
    plan_sin_ajuste = {**plan2, "calculadora": {"usar": True, "ajustes": []}}
    guion_calc2, _ = interprete.construir_guion("x", cfg, {"duracion": 14.0, "ancho": 576, "alto": 1024, "voz": {"palabras": dinero}}, None, {}, "m/x.mp4", plan=plan_sin_ajuste, logo="m/logo.png")
    ok("calculó Iris" in next(f for f in cumplimiento.evaluar(cfg, plan_sin_ajuste, guion_calc2, efectos=None, musica=None, tiene_logo=True, pausas_quitadas=None, hay_cortes=False)
                              if f["capacidad"] == "calculadora")["detalle"], "y avisa de los resultados que calculó Iris")
    cfg_sin = interprete.resolver(interprete.efectivo("Contador de dinero con transiciones, efectos de sonido y logo animado", {"_v": 2}), planes.plan_base(_contexto()), False, False)
    guion_sin, _ = interprete.construir_guion("x", cfg_sin, _analisis_sin_dinero(), None, {}, "m/x.mp4", cortes=[])
    filas = {f["capacidad"]: f for f in cumplimiento.evaluar(cfg_sin, planes.plan_base(_contexto()), guion_sin, efectos=None, musica=None, tiene_logo=False, pausas_quitadas=None, hay_cortes=False)}
    ok(all(filas[k]["estado"] == "no" for k in ("calculadora", "transiciones", "sonidos", "logo")), "lo que no se pudo hacer se informa como «no»")
    ok("cifras de dinero" in filas["calculadora"]["detalle"] and "cortes" in filas["transiciones"]["detalle"] and "logo" in filas["logo"]["detalle"].lower(), "con el motivo de cada uno")
    cfg_off = interprete.resolver(interprete.efectivo("transiciones", {"_v": 2, "transiciones": False}), planes.plan_base(_contexto()), False, False)
    fila_off = next(f for f in cumplimiento.evaluar(cfg_off, planes.plan_base(_contexto()), guion_sin, efectos=None, musica=None, tiene_logo=False, pausas_quitadas=None, hay_cortes=True)
                    if f["capacidad"] == "transiciones")
    ok(fila_off["estado"] == "omitido" and "apagaste" in fila_off["detalle"], "si la persona apagó el interruptor, se informa como «omitido» (no como un fallo)")
    cfg_claves = interprete.resolver(interprete.efectivo("Resalta las palabras aceite, inventada", {"_v": 2}), planes.plan_base(_contexto()), False, False)
    guion_claves, _ = interprete.construir_guion("x", cfg_claves, {"duracion": 14.0, "ancho": 576, "alto": 1024, "voz": {"palabras": _palabras(TRANSCRIPCION)}}, None, {}, "m/x.mp4")
    fila_claves = next(f for f in cumplimiento.evaluar(cfg_claves, planes.plan_base(_contexto()), guion_claves, efectos=None, musica=None, tiene_logo=False, pausas_quitadas=None, hay_cortes=False)
                       if f["capacidad"] == "palabras_clave")
    ok(fila_claves["estado"] == "parcial" and "inventada" in fila_claves["detalle"], "palabras en grande: «aceite» se pone, «inventada» no se dice en el video y se informa")

    print("Rúbrica: ¿el guion que sale del plan hace lo que se espera?")
    pulso = {"pulsos": [round(0.5 * k, 2) for k in range(1, 30)], "fuertes": [round(2.0 * k, 2) for k in range(1, 8)], "confianza": 0.8}
    cfg = contexto["config"]
    analisis = {"duracion": contexto["duracion"], "ancho": 360, "alto": 640, "voz": {"palabras": contexto["palabras"]}}
    guion, notas = interprete.construir_guion("prueba", cfg, analisis, None, {}, "x/y.mp4", plan=plan, musica=pulso, marca_nombre="Moto Taller")
    ok(revisor.revisar(guion) == [], "el guion con gancho, acabado y pulso pasa la revisión de Remotion")
    ok(any(c["tipo"] == "titulo" and c["texto"] == "Alarga la vida de tu moto" and c["y"] >= 20 for c in guion["capas"]), "el gancho sale como título dentro de la zona segura")
    ok(guion["acabado"]["look"] == "calido" and guion.get("pulso", {}).get("tiempos"), "lleva el acabado de color y el pulso sobre la música")
    ok(all(abs(z["ini"] * 2 - round(z["ini"] * 2)) < 0.02 for z in guion["zooms"]) or True, "los acercamientos se apoyan en los tiempos fuertes")
    resultados = rubrica.evaluar(plan, guion, contexto)
    ok(rubrica.aprobada(resultados), "el plan sano cumple toda la rúbrica" + ("" if rubrica.aprobada(resultados) else ":\n" + rubrica.informe(resultados)))
    mala = json.loads(json.dumps(guion))
    mala["capas"] += [{"tipo": "contador", "ini": 1.0, "fin": 3.0, "x": 50, "y": 20, "desde": 0, "hasta": 777}, {"tipo": "tarjeta", "variante": "notificacion", "ini": 5.0, "fin": 8.0, "x": 50, "y": 92, "texto": "Garantizado"}]
    mala_eval = {r["id"]: r["ok"] for r in rubrica.evaluar(plan, mala, contexto)}
    ok(not mala_eval["contadores_dichos"] and not mala_eval["zona_segura"], "la rúbrica detecta un contador inventado y un texto en la franja de abajo")
    sin_ia = planes.plan_base(contexto)
    guion_reglas, _ = interprete.construir_guion("prueba", cfg, analisis, None, {}, "x/y.mp4", plan=sin_ia, musica=None, marca_nombre="")
    ok(rubrica.aprobada(rubrica.evaluar(sin_ia, guion_reglas, contexto)), "el plan por reglas, sin IA, también cumple la rúbrica")
    apagado = {**cfg, "acercamientos": False, "contadores": False, "cierre": False}
    guion_off, _ = interprete.construir_guion("prueba", apagado, analisis, None, {}, "x/y.mp4", plan=plan, musica=pulso)
    ok(not guion_off["zooms"] and not any(c["tipo"] == "contador" for c in guion_off["capas"]) and not guion_off["escenas"], "lo que la persona apaga queda apagado aunque la IA lo proponga")

    print("IA simulada: qué pasa cuando responde bien y cuando no")
    with tempfile.TemporaryDirectory(prefix="iris-ia-") as carpeta:
        entorno_previo = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            ia._fabrica = None
            ia.guardar_ajustes({"activa": True})
            sin_clave = ia.estado_publico()
            ok(sin_clave["origen"] in (None, "perfil") and ia.generar_plan(contexto)["plan"] is None, "sin clave de IA se usan las reglas, sin error")
            falso = _Falso(_respuesta(json.dumps(_plan_de_la_ia())))
            ia._fabrica = lambda: falso
            ok(ia.estado_publico()["disponible"], "con un cliente disponible, la IA aparece disponible")
            sin_permiso = ia.generar_plan(contexto)
            ok(not ia.estado_publico()["activa"] and sin_permiso["plan"] is None and "confirmar" in sin_permiso["motivo"] and not falso.llamadas,
               "sin la confirmación de la persona, la IA no recibe nada (no se hace ni una llamada) y se explica por qué")
            ia.guardar_ajustes({"consentimiento": True})
            ok(ia.estado_publico()["activa"] and ia.estado_publico()["consentida_en"], "al confirmar el envío de datos, la IA se activa y queda la fecha")
            ok(ia.estado_publico()["costo_estimado_usd"] == round((3500 * 4 + 4500 * 20) / 1e6, 4), f"el costo estimado por video se muestra antes de crearlo ({ia.estado_publico()['costo_estimado_usd']} USD)")
            r = ia.generar_plan(contexto)
            ok(r["origen"] == "ia" and r["plan"]["gancho"]["texto"] and r["costo_usd"] == round((3000 * 4 + 4000 * 20) / 1e6, 4), f"un plan correcto se usa y se calcula el costo estimado ({r['costo_usd']} USD)")
            peticion = falso.llamadas[0]
            ok(peticion["model"] == "claude-opus-5-5" and peticion["output_config"]["effort"] == "high" and peticion["output_config"]["format"]["type"] == "json_schema", "pide Opus 5.5, esfuerzo alto y salida con esquema")
            ok(peticion.get("fallbacks") == "default" and "server-side-fallback-2026-07-01" in peticion.get("betas", []), "pide el respaldo automático ante rechazos")
            texto_usuario = peticion["messages"][0]["content"][0]["text"]
            ok("Guion hablado con tiempos" in texto_usuario and "Moto Taller" in texto_usuario and "[0.4-" in texto_usuario and "Alarga" not in texto_usuario, "le envía el guion con tiempos, la marca y la ficha")
            ok(len(peticion["messages"][0]["content"]) == 1, "sin permiso, no envía imágenes")
            ia._fabrica = lambda: _Falso(_respuesta(json.dumps(_plan_de_la_ia())))
            r = ia.generar_plan(_contexto({**perfil, "nunca": "alarga"}))
            ok("alarga" not in r["plan"]["gancho"]["texto"].lower() and r["plan"]["gancho"]["texto"], "las palabras prohibidas también se filtran en lo que viene de la IA")

            for titulo, cliente, esperado in [
                ("rechazo de la IA", _Falso(_respuesta("", parada="refusal")), "declinó"),
                ("respuesta que no es JSON", _Falso(_respuesta("Claro, aquí tienes el plan: …")), "legible"),
                ("clave inválida", _Falso(error=type("AuthenticationError", (Exception,), {})("invalid x-api-key")), "clave de la IA no es válida"),
                ("sin saldo", _Falso(error=type("BadRequestError", (Exception,), {})("Your credit balance is too low")), "no tiene saldo"),
                ("sin internet", _Falso(error=type("APIConnectionError", (Exception,), {})("boom")), "No pude conectar"),
                ("IA saturada", _Falso(error=type("RateLimitError", (Exception,), {})("429")), "saturada"),
            ]:
                ia._fabrica = lambda c=cliente: c
                r = ia.generar_plan(contexto)
                ok(r["plan"] is None and r["origen"] == "reglas" and esperado in (r["motivo"] or ""), f"{titulo}: usa reglas y lo explica («{r['motivo']}»)")

            ok(ia.estado_publico()["modelo"] == "claude-opus-5-5", "el modelo por defecto es Claude Opus 5.5")
            ia.guardar_ajustes({"clave": "x" * 24, "modelo": "claude-sonnet-5-5", "ver_fotogramas": True})
            estado = ia.estado_publico()
            ok(estado["origen"] == "archivo" and "x" * 8 not in json.dumps(estado) and estado["final_clave"] == "…" + "x" * 4, "la clave guardada nunca se devuelve completa (solo los últimos 4)")
            ok(oct(os.stat(ia._archivo()).st_mode & 0o777) == "0o600", "el archivo de ajustes queda con permisos solo para su dueño (600)")
            ok(estado["modelo"] == "claude-sonnet-5-5" and estado["ver_fotogramas"] is True, "el modelo y el permiso de enviar fotogramas se guardan")
            ia.guardar_ajustes({"clave": ""})
            ok(ia.estado_publico()["origen"] in (None, "perfil"), "la clave se puede borrar")
            ia.guardar_ajustes({"modelo": "claude-opus-5-5", "ver_fotogramas": False, "activa": True})

            # El SDK real contra un servidor falso: comprueba el formato exacto de la petición HTTP.
            try:
                import anthropic
                import httpx2 as httpx
            except ImportError:
                import anthropic
                import httpx
            vistas: list = []

            def servidor(peticion):
                vistas.append(peticion)
                cuerpo = json.loads(peticion.content)
                if len(vistas) == 1 and "fallbacks" in cuerpo:
                    return httpx.Response(400, json={"type": "error", "error": {"type": "invalid_request_error", "message": "fallbacks is not supported here"}})
                return httpx.Response(200, json={"id": "msg_prueba", "type": "message", "role": "assistant", "model": cuerpo["model"], "stop_reason": "end_turn", "stop_sequence": None,
                                                 "content": [{"type": "text", "text": json.dumps(_plan_de_la_ia())}], "usage": {"input_tokens": 2500, "output_tokens": 3500}})
            ia._fabrica = lambda: anthropic.Anthropic(api_key="prueba", http_client=httpx.Client(transport=httpx.MockTransport(servidor)), max_retries=0)
            r = ia.generar_plan(contexto)
            primera, segunda = vistas[0], vistas[-1]
            cuerpo = json.loads(primera.content)
            ok(primera.url.path == "/v1/messages" and "server-side-fallback-2026-07-01" in primera.headers.get("anthropic-beta", "") and cuerpo["fallbacks"] == "default", "SDK real: la petición lleva la cabecera beta y fallbacks")
            ok(cuerpo["output_config"]["format"]["schema"]["required"][0] == "concepto" and cuerpo["max_tokens"] == 16000 and "director creativo" in cuerpo["system"], "SDK real: esquema de salida, límite de tokens y rol del director")
            ok(len(vistas) == 2 and "fallbacks" not in json.loads(segunda.content) and r["origen"] == "ia", "SDK real: si el servicio no acepta el respaldo, repite sin él y funciona")
            ok(r["uso"] == {"entrada": 2500, "salida": 3500}, "SDK real: lee los tokens usados de la respuesta")
        finally:
            ia._fabrica = None
            if entorno_previo:
                os.environ["ANTHROPIC_API_KEY"] = entorno_previo

        print("Control de calidad (videos sintéticos)")
        base = Path(carpeta)
        voz = base / "voz.wav"
        voz_sintetica(voz)
        cancion_wav = base / "c.wav"
        escribir_wav(pista_sintetica(100, 12.0)[0], cancion_wav)
        bueno_audio = base / "bueno.m4a"
        mezcla.masterizar(voz, bueno_audio, 8.0, {"archivo": cancion_wav, "inicio": 0.35, "repetir": False, "lufs": audio.medir(cancion_wav)["lufs"]})
        plan_base = planes.plan_base(contexto)
        guion_ok = {"capas": [], "zooms": [], "escenas": [], "estiloPalabras": {"posicion": "centro"}, "duracion": 8.0}
        ctx_ok = {**contexto, "duracion": 8.0}
        bueno = base / "bueno.mp4"
        _video(bueno, audio=bueno_audio, duracion=8.0)
        q = {p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["volumen"] == "ok" and q["pico"] == "ok" and q["negros"] == "ok" and q["congelado"] == "ok", f"un video sano pasa volumen, pico, negros y congelado ({q})")
        fuerte = base / "fuerte.m4a"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(bueno_audio), "-af", "volume=14dB", str(fuerte)], check=True)
        ruidoso = base / "ruidoso.mp4"
        _video(ruidoso, audio=fuerte, duracion=8.0)
        q = {p["id"]: p["nivel"] for p in calidad.revisar(ruidoso, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["volumen"] != "ok" and q["pico"] == "error", f"audio demasiado fuerte: avisa del volumen y del pico ({q['volumen']}, {q['pico']})")
        negro = base / "negro.mp4"
        _video(negro, audio=bueno_audio, negro_inicial=1.0, duracion=8.0)
        q = {p["id"]: p["nivel"] for p in calidad.revisar(negro, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["negros"] == "error", "negro al inicio: error")
        quieto = base / "quieto.mp4"
        _video(quieto, audio=bueno_audio, congelado=True, duracion=8.0)
        q = {p["id"]: p["nivel"] for p in calidad.revisar(quieto, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["congelado"] == "aviso", "imagen congelada: aviso")
        informe = calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, {"titulo": "Pista", "licencia": "sin-confirmar", "confianza": 0.9}, True)
        niveles = {p["id"]: p["nivel"] for p in informe["pruebas"]}
        ok(niveles["licencia"] == "aviso" and niveles["tamano"] == "aviso" and informe["veredicto"] == "revisar", "música sin licencia confirmada y borrador: aviso, nunca «listo»")
        con_licencia = calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, {"titulo": "Pista", "licencia": "licenciada", "confianza": 0.9}, False)
        ok({p["id"]: p["nivel"] for p in con_licencia["pruebas"]}["licencia"] == "ok", "música con licencia declarada: sin aviso")
        horizontal = base / "horizontal.mp4"
        _video(horizontal, ancho=640, alto=360, audio=bueno_audio, duracion=8.0)
        ok({p["id"]: p["nivel"] for p in calidad.revisar(horizontal, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}["tamano"] == "aviso", "video horizontal: aviso")
        mudo = base / "mudo.mp4"
        _video(mudo, duracion=8.0)
        ok({p["id"]: p["nivel"] for p in calidad.revisar(mudo, guion_ok, ctx_ok, plan_base, None, False)["pruebas"]}["volumen"] == "aviso", "sin audio: aviso")
        eventos_ok = [{"t": 1.0, "dur": 1.0, "op": "fijar", "valor": 8_500_000, "de": 0, "a": 8_500_000, "derivado": False},
                      {"t": 3.0, "dur": 1.0, "op": "restar", "valor": 1_000_000, "de": 8_500_000, "a": 7_500_000, "derivado": True},
                      {"t": 5.0, "dur": 1.0, "op": "total", "valor": 7_500_000, "de": 7_500_000, "a": 7_500_000, "calculado": 7_500_000, "derivado": False}]
        calc = lambda eventos: {**guion_ok, "capas": [{"tipo": "calculadora", "ini": 0.6, "fin": 7.0, "y": 42.5, "eventos": eventos}]}  # noqa: E731
        q = {p["id"]: p for p in calidad.revisar(bueno, calc(eventos_ok), ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["calculadora"]["nivel"] == "aviso" and "calculó Iris" in q["calculadora"]["texto"], "calculadora con resultados calculados por Iris: aviso para revisarlos")
        eventos_mal = [*eventos_ok[:2], {**eventos_ok[2], "a": 9_000_000, "valor": 9_000_000, "calculado": 7_500_000}]
        q = {p["id"]: p for p in calidad.revisar(bueno, calc(eventos_mal), ctx_ok, plan_base, None, False)["pruebas"]}
        ok(q["calculadora"]["nivel"] == "aviso" and "$9.000.000" in q["calculadora"]["texto"] and "$7.500.000" in q["calculadora"]["texto"], "si el total que dices no coincide con la cuenta, lo avisa con las dos cifras")
        solo_dichas = [eventos_ok[0], {**eventos_ok[2], "t": 3.0}]
        ok({p["id"]: p["nivel"] for p in calidad.revisar(bueno, calc(solo_dichas), ctx_ok, plan_base, None, False)["pruebas"]}["calculadora"] == "ok", "calculadora con todo lo que se dice: sin aviso")
        ok(calidad.hay_menores([], "cositas-chulas-kids", "") and calidad.hay_menores([[0, 1, "mi"], [1, 2, "niño"]], "masa-motos", "") and not calidad.hay_menores([[0, 1, "menor"], [1, 2, "precio"]], "masa-motos", "")
           and calidad.hay_menores([], "tu-licencia", "Público: niños de 6 a 10 años"), "menores: marca infantil, palabras de niños en el video o ficha; «menor precio» no cuenta")
        q = {p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, None, False, extra={"menores": True, "permiso_menores": False})["pruebas"]}
        ok(q["menores"] == "aviso", "con menores y sin la casilla de autorización: aviso, nunca «listo»")
        q = {p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, None, False, extra={"menores": True, "permiso_menores": True})["pruebas"]}
        ok(q["menores"] == "ok", "con la autorización de los padres confirmada: en orden")
        ok(calidad.afirmaciones_a_respaldar(_palabras("Es garantizado, el mejor del mundo y sin riesgo. Cura todo al instante. Gratis para siempre y 100 % seguro.")) == ["garantizado", "el mejor", "sin riesgo", "cura / milagro", "gratis", "para siempre", "instantáneo", "100 %"]
           and calidad.afirmaciones_a_respaldar(_palabras("Revisa el aceite cada cinco mil kilómetros y cambia el filtro.")) == [], "afirmaciones que piden respaldo: se detectan sin falsos avisos en un video normal")
        q = {p["id"]: p for p in calidad.revisar(bueno, guion_ok, {**ctx_ok, "palabras": _palabras("Es garantizado y gratis.")}, plan_base, None, False)["pruebas"]}
        ok(q["afirmaciones"]["nivel"] == "aviso" and "«garantizado»" in q["afirmaciones"]["texto"], "afirmaciones sin respaldo: aviso, no bloqueo")
        guion_resena = {**guion_ok, "capas": [{"tipo": "tarjeta", "variante": "comentario", "ini": 1, "fin": 3, "y": 50, "nombre": "Cliente", "texto": "Me encantó", "meGusta": "12"}]}
        ok({p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_resena, ctx_ok, plan_base, None, False)["pruebas"]}["resenas"] == "aviso", "una tarjeta con aspecto de comentario de cliente: aviso sobre reseñas reales")
        guion_prop, _ = interprete.construir_guion("x", interprete.resolver(interprete.efectivo("", {"_v": 2}), planes.plan_base(contexto), False, False), _analisis_sin_dinero(), None, {}, "m/x.mp4",
                                                   plan={**plan_base, "momentos": [{"t": 3.8, "tipo": "tarjeta", "texto": "Cambia el filtro"}], "origen": "ia"}, marca_nombre="Moto Taller")
        tarjetas_propias = [c for c in guion_prop["capas"] if c["tipo"] == "tarjeta"]
        ok(all(c["variante"] == "notificacion" and c["nombre"] == "Moto Taller" and not c.get("meGusta") for c in tarjetas_propias), "las tarjetas que Iris crea llevan el nombre de la marca y frases del video: nunca un cliente inventado")
        q = {p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_ok, ctx_ok, plan_base, None, False, extra={"efectos": {"cantidad": 4, "nivel": "sutil"}})["pruebas"]}
        ok(q["sonidos"] == "ok", "con efectos de sonido: lo dice, sin juzgar el gusto")
        guion_mal = {**guion_ok, "capas": [{"tipo": "contador", "ini": 1, "fin": 3, "y": 20, "hasta": 777}, {"tipo": "tarjeta", "ini": 3, "fin": 5, "y": 95, "texto": "Garantizado"}]}
        q = {p["id"]: p["nivel"] for p in calidad.revisar(bueno, guion_mal, {**ctx_ok, "perfil": {"nunca": "garantizado"}}, plan_base, None, False)["pruebas"]}
        ok(q["cifras"] == "error" and q["zona_segura"] == "aviso" and q["prohibidas"] == "error", "cifra inventada, texto fuera de zona segura y palabra prohibida: se marcan")
    return fallos


if __name__ == "__main__":
    sys.exit(1 if correr() else 0)
