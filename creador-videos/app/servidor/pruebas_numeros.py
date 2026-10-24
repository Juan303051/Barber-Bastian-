"""Pruebas del lector de cifras habladas con transcripciones reales de Whisper (voz sintética en español). No necesitan red ni ffmpeg.
Se ejecutan con ./creador probar (o: python -m servidor.pruebas_numeros)."""
from __future__ import annotations

import sys
from pathlib import Path

# Lo que Whisper `small` devolvió de verdad al transcribir tres escenas con precios hablados.
ESCENA_1 = [[0.0, 0.3, "Mira"], [0.3, 0.64, "esta"], [0.64, 1.0, "moto,"], [1.3, 1.62, "cuesta"], [1.62, 1.82, "8"], [1.82, 2.6, ".500"], [2.6, 3.24, ".000"],
            [3.24, 3.5, "pesos"], [3.5, 4.04, "y"], [4.04, 4.2, "hoy"], [4.2, 4.36, "te"], [4.36, 4.58, "voy"], [4.58, 4.72, "a"], [4.72, 5.06, "mostrar"],
            [5.06, 5.52, "cómo"], [5.52, 5.86, "pagar"], [5.86, 6.24, "mucho"], [6.24, 6.52, "menos."]]
ESCENA_2 = [[0.0, 0.56, "Primero,"], [0.74, 1.06, "tiene"], [1.06, 1.52, "un"], [1.52, 2.1, "descuento"], [2.1, 2.26, "de"], [2.26, 2.38, "un"], [2.38, 2.84, "millón"],
            [2.84, 2.94, "de"], [2.94, 3.24, "pesos."], [3.54, 4.08, "Segundo,"], [4.24, 4.32, "te"], [4.32, 4.9, "regalamos"], [4.9, 5.1, "el"], [5.1, 5.62, "casco"],
            [5.62, 6.06, "que"], [6.06, 6.28, "vale"], [6.28, 6.72, "300"], [6.72, 7.2, "mil"], [7.2, 7.52, "pesos."]]
ESCENA_3 = [[0.0, 0.44, "Entonces"], [0.44, 0.74, "la"], [0.74, 0.98, "moto"], [0.98, 1.2, "te"], [1.2, 1.48, "queda"], [1.48, 1.62, "en"], [1.62, 1.88, "7"],
            [1.88, 2.68, ".500"], [2.68, 3.28, ".000"], [3.28, 3.56, "pesos."], [3.98, 4.34, "Comenta"], [4.34, 4.66, "moto"], [4.66, 4.84, "y"], [4.84, 4.94, "te"],
            [4.94, 5.56, "asesoramos."]]
# Un video de verdad sin precios: «seis meses», «uno o dos años» no son dinero.
SIN_DINERO = [[4.5, 4.8, "Que"], [4.8, 5.0, "ojo,"], [5.0, 5.2, "no"], [5.2, 5.4, "tienes"], [5.4, 5.6, "que"], [5.6, 5.9, "dedicarle"], [5.9, 6.2, "seis"], [6.2, 6.5, "meses"],
              [6.5, 6.6, "ni"], [6.6, 6.8, "uno"], [6.8, 6.9, "o"], [6.9, 7.1, "dos"], [7.1, 7.4, "años."], [10.5, 10.7, "un"], [10.7, 10.9, "buen"], [10.9, 11.3, "editor."]]


def _unidas(*escenas: list, paso: float = 10.0) -> list:
    salida = []
    for k, escena in enumerate(escenas):
        salida += [[round(a + k * paso, 2), round(b + k * paso, 2), t] for a, b, t in escena]
    return salida


def correr() -> list[str]:
    import numeros

    fallos: list[str] = []

    def ok(condicion: bool, titulo: str) -> None:
        print(("  ✓ " if condicion else "  ✗ ") + titulo)
        if not condicion:
            fallos.append(titulo)

    print("Cifras partidas por Whisper")
    unidas = numeros.unir_fragmentos(ESCENA_1)
    ok([p[2] for p in unidas if p[2][0].isdigit()] == ["8.500.000"], "«8» «.500» «.000» vuelve a ser 8.500.000")
    ok(next(p for p in unidas if p[2] == "8.500.000")[:2] == [1.62, 3.24], "y conserva el tiempo desde el primer pedazo hasta el último")
    ok([p[2] for p in numeros.unir_fragmentos([[0, 1, "$"], [1, 2, "50"], [2, 3, ".000"], [3, 4, "pesos"]])] == ["$50.000", "pesos"], "«$» «50» «.000» → $50.000")
    ok([p[2] for p in numeros.unir_fragmentos([[0, 1, "el"], [1, 2, "20"], [2, 3, "%"]])] == ["el", "20%"], "«20» «%» → 20%")
    ok([p[2] for p in numeros.unir_fragmentos([[0, 1, "1"], [1, 2, ",5"], [2, 3, "millones"]])] == ["1,5", "millones"], "«1» «,5» → 1,5")
    ok([p[2] for p in numeros.unir_fragmentos([[0, 1, "hola."], [1, 2, "500"]])] == ["hola.", "500"], "una palabra con punto no se pega a un número")
    ok([p[2] for p in numeros.unir_fragmentos([[0, 1, "tres,"], [1, 2, "500"]])] == ["tres,", "500"], "una coma de frase no se confunde con un decimal")

    print("Números en letras")
    casos = {"ocho millones quinientos mil": 8_500_000, "un millon": 1_000_000, "medio millon": 500_000, "un millon y medio": 1_500_000, "dos mil veinte": 2020,
             "cien mil": 100_000, "mil quinientos": 1500, "treinta y cinco": 35, "veintiuno": 21, "ciento veinte mil trescientos": 120_300, "dos mil millones": 2_000_000_000,
             "doscientos cincuenta mil": 250_000, "tres millones doscientos mil": 3_200_000, "quince": 15}
    for letras, esperado in casos.items():
        leido = numeros.leer_en_letras(letras.split())
        ok(leido == esperado, f"«{letras}» = {esperado:,}".replace(",", ".") + ("" if leido == esperado else f" (leyó {leido})"))
    ok(numeros.leer_en_letras(["hola"]) is None and numeros.leer_en_letras([]) is None, "lo que no es un número se rechaza")

    print("Encontrar cifras en lo dicho")
    c = numeros.encontrar(_unidas(ESCENA_1, ESCENA_2, ESCENA_3))
    ok([x["valor"] for x in c] == [8_500_000, 1_000_000, 300_000, 7_500_000], f"las cuatro cifras del video: {[x['valor'] for x in c]}")
    ok(all(x["clase"] == "dinero" for x in c), "todas son dinero (llevan «pesos» o «descuento»)")
    ok(c[0]["ini"] == 1.62 and c[1]["ini"] == 12.26, "cada cifra empieza cuando se empieza a decir")
    s = numeros.encontrar(SIN_DINERO)
    ok([x["valor"] for x in s] == [6, 2] and all(x["clase"] == "cantidad" for x in s), f"«seis meses», «dos años» son cantidades, no dinero; «uno» y «un» sueltos se ignoran: {[x['valor'] for x in s]}")
    ok(numeros.encontrar([[0, 1, "es"], [1, 2, "20%"], [2, 3, "de"], [3, 4, "descuento"]])[0]["clase"] == "porcentaje", "20% es un porcentaje")
    ok(numeros.encontrar([[0, 1, "veinte"], [1, 2, "por"], [2, 3, "ciento"]])[0]["valor"] == 20 and numeros.encontrar([[0, 1, "veinte"], [1, 2, "por"], [2, 3, "ciento"]])[0]["clase"] == "porcentaje", "«veinte por ciento» es 20 %")
    ok(numeros.encontrar([[0, 1, "1,5"], [1, 2, "millones"], [2, 3, "de"], [3, 4, "pesos"]])[0]["valor"] == 1_500_000, "«1,5 millones de pesos» = 1.500.000")
    ok(numeros.encontrar([[0, 1, "2"], [1, 2, "millones"], [2, 3, "y"], [3, 4, "medio"]])[0]["valor"] == 2_500_000, "«2 millones y medio» = 2.500.000")
    ok(numeros.encontrar([[0, 1, "2"], [1, 2, "mil"], [2, 3, "500"], [3, 4, "pesos"]])[0]["valor"] == 2500, "«2 mil 500 pesos» = 2.500")
    ok(numeros.encontrar([[0, 1, "$50.000"]])[0]["clase"] == "dinero", "$50.000 es dinero")
    ok(numeros.encontrar([[0, 1, "desde"], [1, 2, "2024"]])[0]["clase"] == "cantidad", "un año suelto no es dinero")
    ok(numeros.encontrar([[0, 1, "hola"], [1, 2, "buen"], [2, 3, "día"]]) == [], "sin números no hay cifras")

    print("De las cifras a la calculadora")
    e = numeros.operaciones(c)
    ok([x["op"] for x in e] == ["fijar", "restar", "mostrar", "total"], f"fija, resta, muestra el regalo y confirma el total: {[x['op'] for x in e]}")
    ok(e[0]["a"] == 8_500_000 and not e[0]["derivado"], "la primera cifra fija el valor de partida tal como se dijo")
    ok([x["etiqueta"] for x in e] == ["Precio", "Descuento", "Valor", "Total"], f"cada paso lleva su rótulo: {[x['etiqueta'] for x in e]}")
    ok(e[1]["de"] == 8_500_000 and e[1]["a"] == 7_500_000 and e[1]["derivado"], "el descuento resta y el resultado lo calculó Iris (derivado)")
    ok(e[2]["a"] is None and e[2]["valor"] == 300_000, "el valor del casco regalado se muestra pero no cambia el total")
    ok(e[3]["a"] == 7_500_000 and e[3]["calculado"] == 7_500_000 and not e[3]["derivado"], "el total que se dice coincide con el calculado")
    mal = numeros.operaciones(numeros.encontrar([[0, 1, "cuesta"], [1, 2, "1.000.000"], [2, 3, "pesos"], [3, 4, "con"], [4, 5, "descuento"], [5, 6, "de"], [6, 7, "200.000"],
                                                 [7, 8, "pesos"], [8, 9, "queda"], [9, 10, "en"], [10, 11, "900.000"], [11, 12, "pesos"]]))
    ok(mal[-1]["op"] == "total" and mal[-1]["calculado"] == 800_000 and mal[-1]["a"] == 900_000, "si el total dicho no coincide con la cuenta, se guarda lo calculado para avisarlo")
    pct = numeros.operaciones(numeros.encontrar([[0, 1, "cuesta"], [1, 2, "1.000.000"], [2, 3, "pesos"], [3, 4, "con"], [4, 5, "20%"], [5, 6, "de"], [6, 7, "descuento"]]))
    ok([x["op"] for x in pct] == ["fijar", "restar_pct"] and pct[1]["a"] == 800_000 and pct[1]["derivado"], "20 % de descuento sobre el valor de partida = 800.000 (derivado)")
    solo_pct = numeros.operaciones(numeros.encontrar([[0, 1, "20%"], [1, 2, "de"], [2, 3, "descuento"]]))
    ok(solo_pct[0]["op"] == "mostrar", "un porcentaje sin valor de partida solo se muestra")
    primero_resta = numeros.operaciones(numeros.encontrar([[0, 1, "descuento"], [1, 2, "de"], [2, 3, "200.000"], [3, 4, "pesos"]]))
    ok(primero_resta[0]["op"] == "mostrar", "una resta sin valor de partida no se calcula: solo se muestra")
    ok(numeros.operaciones(s) == [], "sin dinero, la calculadora no se activa")
    ok(numeros.formato_es(8_500_000, "$") == "$8.500.000" and numeros.formato_es(-1500) == "-1.500", "formato español de miles")
    return fallos


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "herramientas"))
    sys.exit(1 if correr() else 0)
