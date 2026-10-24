// Utilidades pequeñas: crear elementos de forma segura (nunca se inserta HTML de texto escrito por personas).
const NS = "http://www.w3.org/2000/svg";

export function el(etiqueta, propiedades = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(propiedades)) {
    if (valor === undefined || valor === null || valor === false) continue;
    if (clave === "clase") nodo.className = valor;
    else if (clave === "texto") nodo.textContent = valor;
    else if (clave.startsWith("en") && typeof valor === "function") nodo.addEventListener(clave.slice(2).toLowerCase(), valor);
    else if (clave === "datos") Object.assign(nodo.dataset, valor);
    else if (valor === true) nodo.setAttribute(clave, "");
    else nodo.setAttribute(clave, valor);
  }
  anadir(nodo, hijos);
  return nodo;
}

export function anadir(nodo, hijos) {
  for (const hijo of hijos.flat()) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
  }
}

export function icono(nombre, clase = "") {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", `icono ${clase}`.trim());
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const uso = document.createElementNS(NS, "use");
  uso.setAttribute("href", `#i-${nombre}`);
  svg.append(uso);
  return svg;
}

export function logo() {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 64 36");
  svg.setAttribute("aria-hidden", "true");
  const radios = [[28, "rojo"], [23, "naranja"], [18, "verde"], [13, "azul"], [8, "morado"]];
  radios.forEach(([r, color]) => {
    const camino = document.createElementNS(NS, "path");
    camino.setAttribute("d", `M${32 - r} 33a${r} ${r} 0 0 1 ${r * 2} 0`);
    camino.setAttribute("class", `arco ${color}`);
    svg.append(camino);
  });
  return svg;
}

export function formatoTiempo(segundos) {
  const total = Math.max(0, Math.round(segundos));
  return total >= 60 ? `${Math.floor(total / 60)} min ${String(total % 60).padStart(2, "0")} s` : `${total} s`;
}

export function aproximado(segundos) {
  if (segundos === null || segundos === undefined || !isFinite(segundos)) return null;
  if (segundos < 8) return "unos segundos";
  if (segundos < 55) return `unos ${Math.round(segundos / 5) * 5} s`;
  const minutos = Math.round(segundos / 60);
  return minutos <= 1 ? "cerca de 1 min" : `cerca de ${minutos} min`;
}

export function debounce(funcion, espera) {
  let temporizador;
  const envuelta = (...argumentos) => {
    clearTimeout(temporizador);
    temporizador = setTimeout(() => funcion(...argumentos), espera);
  };
  envuelta.ahora = (...argumentos) => { clearTimeout(temporizador); return funcion(...argumentos); };
  return envuelta;
}

export function esVideo(archivo) {
  return /\.(mp4|mov|m4v|webm|mkv)$/i.test(archivo.name);
}

export function iniciales(nombre) {
  return (nombre || "?").trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("") || "?";
}

export function poner(nodo, ...hijos) {
  nodo.replaceChildren();
  anadir(nodo, hijos);
  return nodo;
}

export function establecerProgreso(pista, fraccion) {
  pista.querySelector("i").style.setProperty("--p", `${Math.round(Math.min(1, Math.max(0, fraccion)) * 1000) / 10}%`);
}
