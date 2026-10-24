import type { EstiloPalabras, PalabraT, Zoom } from "./tipos.ts";

export type Token = { texto: string; ini: number; fin: number; clave: boolean; serif: boolean };
export type Pagina = { ini: number; fin: number; tokens: Token[] };

/** Minúsculas, sin acentos ni signos: así «Cómo», «como» y «¿cómo?» son la misma palabra. */
export const normalizar = (texto: string) =>
  texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\p{L}\p{N}]/gu, "");

/** Quita comillas y la puntuación final (se conservan ¿ ? ¡ !). */
export const limpiar = (texto: string) =>
  texto
    .trim()
    .replace(/^["“'«]+/, "")
    .replace(/(["”'»]|[.,;:…])+$/, "");

/** Agrupa palabras con tiempo en páginas cortas: se corta por cantidad, por pausa y al final de una frase. */
export function paginar(
  palabras: PalabraT[],
  estilo: EstiloPalabras = {},
  correcciones: Record<string, string> = {},
): Pagina[] {
  const maximo = estilo.maxPalabras ?? 3;
  const pausa = estilo.pausa ?? 0.35;
  const claves = new Set((estilo.claves ?? []).map(normalizar));
  const serif = new Set((estilo.serif ?? []).map(normalizar));
  const arreglos = new Map(Object.entries(correcciones).map(([k, v]) => [normalizar(k), v]));
  const paginas: Pagina[] = [];
  let actual: Pagina | null = null;
  let anterior: PalabraT | null = null;
  for (const [ini, fin, bruta] of palabras) {
    const texto = arreglos.get(normalizar(bruta)) ?? limpiar(bruta);
    if (!texto) continue;
    const finDeFrase = anterior !== null && /[.?!…]["”»]?$/.test(anterior[2].trim());
    const hayPausa = anterior !== null && ini - anterior[1] > pausa;
    if (actual === null || actual.tokens.length >= maximo || finDeFrase || hayPausa) {
      actual = { ini, fin, tokens: [] };
      paginas.push(actual);
    }
    const llave = normalizar(texto);
    actual.tokens.push({ texto, ini, fin, clave: claves.has(llave), serif: serif.has(llave) });
    actual.fin = fin;
    anterior = [ini, fin, bruta];
  }
  return paginas;
}

/** Segundos que una página permanece en pantalla: hasta que empieza la siguiente o, a lo sumo, 0.3 s tras su última palabra. */
export const duracionPagina = (pagina: Pagina, siguiente?: Pagina) =>
  Math.max(0.2, Math.min(siguiente ? siguiente.ini : Infinity, pagina.fin + 0.3) - pagina.ini);

export const formatearNumero = (valor: number, separador = ",") =>
  Math.round(valor).toString().replace(/\B(?=(\d{3})+(?!\d))/g, separador);

/** Valor de un contador en el segundo `t`: sube con suavidad durante el 70 % del tiempo y se queda en `hasta`. */
export function valorContador(t: number, ini: number, fin: number, desde: number, hasta: number) {
  const progreso = Math.min(1, Math.max(0, (t - ini) / Math.max(0.1, (fin - ini) * 0.7)));
  return desde + (hasta - desde) * (1 - Math.pow(1 - progreso, 3));
}

/** Acercamiento de la toma base en el segundo `t`: entra y sale con una rampa de 0.25 s. */
export function zoomEn(t: number, zooms: Zoom[] = []) {
  for (const z of zooms) {
    if (t >= z.ini && t <= z.fin) {
      const rampa = Math.min(0.25, (z.fin - z.ini) / 2);
      const k = Math.min(1, (t - z.ini) / rampa, (z.fin - t) / rampa);
      return { escala: 1 + (z.escala - 1) * k, x: z.x ?? 50, y: z.y ?? 40 };
    }
  }
  return { escala: 1, x: 50, y: 40 };
}

/** Trazados para el texto curvo en un lienzo de `ancho` × `alto`. */
export function trayecto(forma: "arco" | "onda", ancho: number, alto: number) {
  if (forma === "onda") {
    return `M 0 ${alto / 2} C ${ancho * 0.25} ${alto * 0.1}, ${ancho * 0.25} ${alto * 0.9}, ${ancho / 2} ${alto / 2} S ${ancho * 0.75} ${alto * 0.1}, ${ancho} ${alto / 2}`;
  }
  return `M ${ancho * 0.05} ${alto * 0.9} Q ${ancho / 2} ${-alto * 0.5}, ${ancho * 0.95} ${alto * 0.9}`;
}

/** Filtro CSS del acabado de color y fuerza de la viñeta (0–1). Efectos suaves: la intensidad los escala desde 0. */
export function filtroDeAcabado(acabado?: { look: string; intensidad?: number }) {
  if (!acabado) return { filtro: "none", vineta: 0 };
  const k = Math.min(1, Math.max(0, acabado.intensidad ?? 0.5));
  const r = (v: number) => Math.round(v * 1000) / 1000;
  switch (acabado.look) {
    case "calido":
      return { filtro: `contrast(${r(1 + 0.05 * k)}) saturate(${r(1 + 0.08 * k)}) sepia(${r(0.16 * k)}) brightness(${r(1 + 0.02 * k)})`, vineta: 0.1 * k };
    case "frio":
      return { filtro: `contrast(${r(1 + 0.06 * k)}) saturate(${r(1 - 0.05 * k)}) hue-rotate(${r(8 * k)}deg) brightness(${r(1 + 0.01 * k)})`, vineta: 0.1 * k };
    case "cine":
      return { filtro: `contrast(${r(1 + 0.14 * k)}) saturate(${r(1 - 0.1 * k)}) brightness(${r(1 - 0.04 * k)})`, vineta: 0.38 * k };
    case "vibrante":
      return { filtro: `contrast(${r(1 + 0.08 * k)}) saturate(${r(1 + 0.28 * k)})`, vineta: 0 };
    default:
      return { filtro: `contrast(${r(1 + 0.04 * k)}) saturate(${r(1 + 0.06 * k)})`, vineta: 0.08 * k };
  }
}

/** Escala del latido en el segundo `t`: sube de golpe en cada tiempo fuerte y se relaja en ~0.35 s. Máximo ≈ 2 %. */
export function escalaPorPulso(t: number, tiempos: number[] = [], intensidad = 0.5) {
  let previo = -1;
  for (const tiempo of tiempos) {
    if (tiempo <= t) previo = tiempo;
    else break;
  }
  if (previo < 0) return 1;
  const k = Math.min(1, Math.max(0, intensidad));
  return 1 + 0.02 * k * Math.exp(-(t - previo) / 0.12);
}
