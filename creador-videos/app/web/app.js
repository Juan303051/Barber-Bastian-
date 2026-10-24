// Arranque: decide si mostrar el acceso o el panel y reacciona cuando la sesión termina.
import { api } from "./api.js";
import { montarAcceso } from "./acceso.js";
import { montarPanel } from "./panel.js";
import { el, logo, poner } from "./util.js";

const raiz = document.getElementById("raiz");
let panel = null;

function mostrarAcceso(primeraVez) {
  panel?.detener();
  panel = null;
  document.title = "Iris · Entrar";
  montarAcceso(raiz, { primeraVez, alEntrar: mostrarPanel });
}

function mostrarPanel(usuario) {
  panel?.detener();
  document.title = "Iris · Videos de marketing en automático";
  panel = montarPanel(raiz, usuario, { alSalir: () => mostrarAcceso(false) });
}

async function arrancar() {
  poner(raiz, el("div", { clase: "cargando-pagina", role: "status" }, logo(), el("span", { clase: "solo-lector", texto: "Cargando Iris…" })));
  try {
    const sesion = await api.sesion();
    if (sesion.usuario) mostrarPanel(sesion.usuario);
    else mostrarAcceso(sesion.primera_vez);
  } catch (error) {
    poner(raiz, el("main", { id: "contenido", clase: "acceso" }, el("section", { clase: "acceso-tarjeta vidrio" },
      el("div", { clase: "marca" }, logo(), el("h1", { clase: "titulo-grande", texto: "Iris no responde" }), el("p", { clase: "subtitulo", texto: error.message })),
      el("button", { type: "button", clase: "boton principal", texto: "Intentar de nuevo", enClick: arrancar }))));
  }
}

document.addEventListener("sesion-caducada", () => { if (panel) mostrarAcceso(false); });
arrancar();
