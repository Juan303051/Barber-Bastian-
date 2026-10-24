import assert from "node:assert/strict";
import { duracionPagina, formatearNumero, limpiar, normalizar, paginar, trayecto, valorContador, zoomEn } from "./logica.ts";
import type { PalabraT } from "./tipos.ts";

const casi = (a: number, b: number) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`);

const palabras: PalabraT[] = [
  [0.0, 0.3, "Esto"], [0.3, 0.6, "te"], [0.6, 0.9, "ahorra"], [0.9, 1.3, "horas."],
  [1.4, 1.7, "Invideo"], [1.7, 2.0, "ya"], [3.0, 3.3, "cloud"],
];

// Se agrupa de 3 en 3, se corta al final de una frase y por pausa larga.
const paginas = paginar(palabras);
assert.deepEqual(paginas.map((p) => p.tokens.map((t) => t.texto)), [["Esto", "te", "ahorra"], ["horas"], ["Invideo", "ya"], ["cloud"]]);
assert.equal(paginas[0].ini, 0);
assert.equal(paginas[0].fin, 0.9);

// Una sola palabra por página.
assert.equal(paginar(palabras, { maxPalabras: 1 }).length, 7);

// Palabras clave y serif ignoran mayúsculas, acentos y signos.
const marcadas = paginar([[0, 1, "¿Cómo"], [1, 2, "Currency."]], { claves: ["como"], serif: ["CURRENCY"] });
assert.equal(marcadas[0].tokens[0].clave, true);
assert.equal(marcadas[0].tokens[1].serif, true);
assert.equal(marcadas[0].tokens[1].clave, false);

// Correcciones de la transcripción.
assert.equal(paginar(palabras, {}, { Cloud: "Claude" })[3].tokens[0].texto, "Claude");

// Una palabra con solo signos no crea una página vacía.
assert.equal(paginar([[0, 1, "..."], [1, 2, "hola"]]).length, 1);
assert.deepEqual(paginar([]), []);

// Limpieza y normalización.
assert.equal(limpiar("«dinero»,"), "dinero");
assert.equal(normalizar("Cómo estás?"), "comoestas");

// Una página dura hasta la siguiente, o 0.3 s tras su última palabra.
casi(duracionPagina(paginas[0], paginas[1]), 0.9);
casi(duracionPagina(paginas[1], paginas[2]), 0.5);
casi(duracionPagina(paginas[2], paginas[3]), 0.9);
casi(duracionPagina(paginas[3]), 0.6);
casi(duracionPagina({ ini: 1, fin: 1, tokens: [] }, { ini: 1, fin: 2, tokens: [] }), 0.2);

// Números.
assert.equal(formatearNumero(1450), "1,450");
assert.equal(formatearNumero(3000.4), "3,000");
assert.equal(formatearNumero(999), "999");
assert.equal(formatearNumero(1234567, "."), "1.234.567");

// Contador: arranca en `desde`, termina en `hasta` y no se pasa.
assert.equal(valorContador(0, 0, 2, 100, 3000), 100);
assert.equal(valorContador(2, 0, 2, 100, 3000), 3000);
assert.equal(valorContador(99, 0, 2, 100, 3000), 3000);
assert.equal(valorContador(-5, 0, 2, 100, 3000), 100);
assert.ok(valorContador(0.5, 0, 2, 0, 1000) > 0 && valorContador(0.5, 0, 2, 0, 1000) < 1000);

// Zoom: sin zoom activo no cambia nada; en el centro del tramo llega a la escala pedida.
assert.deepEqual(zoomEn(0, []), { escala: 1, x: 50, y: 40 });
assert.equal(zoomEn(5, [{ ini: 1, fin: 3, escala: 1.4 }]).escala, 1);
assert.equal(zoomEn(2, [{ ini: 1, fin: 3, escala: 1.4 }]).escala, 1.4);
assert.ok(zoomEn(1.1, [{ ini: 1, fin: 3, escala: 1.4 }]).escala < 1.4);

// Trazados SVG.
assert.match(trayecto("arco", 1000, 400), /^M /);
assert.match(trayecto("onda", 1000, 400), /^M /);

console.log("logica.test.mts: todo en orden");
