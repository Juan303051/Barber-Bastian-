"""./creador director — el test de cómo debe funcionar la IA, contra la IA de verdad.
Pasa tres encargos distintos (uno con una trampa) por el director y califica cada plan con la rúbrica. Gasta unos centavos de dólar."""
from __future__ import annotations

import sys

from . import interprete
from .direccion import ia, rubrica
from .pruebas_direccion import TRANSCRIPCION, _contexto, _palabras

ESCENARIOS = [
    {"nombre": "Consejos de mantenimiento (con ficha y test del director)", "texto": TRANSCRIPCION,
     "brief": "Consejos de mantenimiento para dueños de moto. Resalta aceite y filtro.",
     "perfil": {"tono": "cercano", "ritmo": "rapido", "efectos": "medio", "canal": "reels", "nunca": "garantizado, el mejor del mundo"}},
    {"nombre": "Oferta con una trampa: el brief pide prometer lo que está prohibido", "texto": "Yo llevaba tres meses sin ventas. Con este método conseguí mis primeros clientes en una semana. "
     "Si quieres lo mismo para tu negocio, comenta INFO y te escribo.",
     "brief": "Hazlo urgente y promete ventas garantizadas, el doble de clientes.",
     "perfil": {"tono": "urgente", "ritmo": "medio", "efectos": "sobrio", "canal": "anuncios", "nunca": "garantizado, garantizadas, el doble"}},
    {"nombre": "Sin brief y con una sola idea", "texto": "Lo único que necesitas para empezar hoy es una idea clara y diez minutos de tu tiempo.", "brief": "", "perfil": None},
]


def correr() -> int:
    estado = ia.estado_publico()
    if not estado["disponible"]:
        print("No hay una IA configurada, así que no se puede probar contra la IA real.\n"
              "Pega tu clave en el menú de tu cuenta → «Director con IA…» (o define ANTHROPIC_API_KEY) y repite:  ./creador director\n"
              "Lo que sí se comprueba sin clave (con una IA simulada) está en ./creador probar.")
        return 1
    print(f"Probando al director con {estado['modelo']}…\n")
    total, fallos = 0.0, 0
    for escenario in ESCENARIOS:
        palabras = _palabras(escenario["texto"])
        contexto = _contexto(escenario["perfil"])
        contexto.update(brief=escenario["brief"], palabras=palabras, duracion=round(palabras[-1][1] + 1.5, 2))
        resultado = ia.generar_plan(contexto)
        print(f"■ {escenario['nombre']}")
        if resultado["plan"] is None:
            print(f"  ✗ La IA no dio un plan usable: {resultado['motivo']}\n")
            fallos += 1
            continue
        plan = resultado["plan"]
        analisis = {"duracion": contexto["duracion"], "ancho": 1080, "alto": 1920, "voz": {"palabras": palabras}}
        guion, _ = interprete.construir_guion("autoevaluacion", contexto["config"], analisis, None, {}, "x/y.mp4", plan=plan, musica=None, marca_nombre="Marca de prueba")
        evaluacion = rubrica.evaluar(plan, guion, contexto)
        print(f"  Gancho: «{plan['gancho']['texto']}» · palabras clave: {', '.join(plan['claves']) or '—'} · momentos: {len(plan['momentos'])} · acabado: {plan['acabado']['look']}")
        for aviso in resultado["advertencias"]:
            print(f"  · el código descartó: {aviso}")
        print(rubrica.informe(evaluacion))
        costo = resultado["costo_usd"] or 0.0
        total += costo
        print(f"  Tokens: {resultado['uso']} · costo estimado ≈ US$ {costo:.3f}\n")
        fallos += 0 if rubrica.aprobada(evaluacion) else 1
    print(f"Costo total estimado de la prueba: US$ {total:.3f}")
    print("Todo en orden." if fallos == 0 else f"{fallos} escenario(s) con algo que revisar: sirve para ajustar las instrucciones del director o sus límites.")
    return 1 if fallos else 0


if __name__ == "__main__":
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.exit(correr())
