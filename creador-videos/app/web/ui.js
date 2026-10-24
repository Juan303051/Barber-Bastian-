// Avisos emergentes, cuadros de diálogo y anuncios para lectores de pantalla.
import { el, icono, poner } from "./util.js";

const contenedorAvisos = () => document.getElementById("avisos");

/** Aviso breve abajo. Con `accion` ofrece un botón (por ejemplo «Deshacer»). Devuelve una función para cerrarlo. */
export function aviso(texto, { tipo = "info", accion = null, duracion = 5000 } = {}) {
  const botonAccion = accion ? el("button", { clase: "boton suave pequeno", texto: accion.texto }) : null;
  const cerrar = () => { nodo.remove(); clearTimeout(temporizador); };
  const nodo = el("div", { clase: `aviso vidrio ${tipo === "error" ? "error" : ""}` },
    el("span", { clase: "estado-texto" }, tipo === "error" ? icono("aviso") : null, texto), botonAccion);
  botonAccion?.addEventListener("click", () => { accion.alHacer(); cerrar(); });
  contenedorAvisos().append(nodo);
  const temporizador = setTimeout(cerrar, duracion);
  return cerrar;
}

/** Texto solo para lectores de pantalla (cambios de etapa, videos listos). */
export function anunciar(texto) {
  let nodo = document.getElementById("anuncios");
  if (!nodo) {
    nodo = el("div", { id: "anuncios", clase: "solo-lector", "aria-live": "polite", role: "status" });
    document.body.append(nodo);
  }
  nodo.textContent = "";
  setTimeout(() => { nodo.textContent = texto; }, 60);
}

/**
 * Cuadro de diálogo modal. `acciones`: [{ texto, valor, clase }]. Devuelve el `valor` de la acción elegida (undefined si se cierra con Esc).
 * `alValidar(valor)` puede devolver un texto de error para no cerrar todavía.
 */
export function dialogo({ titulo, texto, cuerpo = null, acciones, alValidar = null }) {
  return new Promise((resolver) => {
    const error = el("div", { clase: "aviso-formulario", role: "alert" });
    const botones = acciones.map((a) => el("button", { type: "button", clase: `boton ${a.clase || ""}`, texto: a.texto, datos: { valor: String(a.valor) } }));
    const nodo = el("dialog", { "aria-labelledby": "dialogo-titulo" },
      el("form", { clase: "hoja", method: "dialog" }, el("h2", { id: "dialogo-titulo", texto: titulo }), texto ? el("p", { texto }) : null, cuerpo, error, el("div", { clase: "acciones" }, botones)));
    document.body.append(nodo);
    const terminar = (valor) => { nodo.close(); nodo.remove(); resolver(valor); };
    acciones.forEach((a, i) => botones[i].addEventListener("click", async () => {
      if (alValidar && a.valor !== false && a.valor !== undefined) {
        botones[i].disabled = true;
        const mensaje = await alValidar(a.valor);
        botones[i].disabled = false;
        if (mensaje) { poner(error, icono("aviso"), el("span", { texto: mensaje })); return; }
      }
      terminar(a.valor);
    }));
    nodo.addEventListener("cancel", (e) => { e.preventDefault(); terminar(undefined); });
    nodo.addEventListener("click", (e) => { if (e.target === nodo) terminar(undefined); });
    nodo.showModal();
    (cuerpo?.querySelector("input, select, textarea") ?? botones[botones.length - 1]).focus();
  });
}

/** Campo con etiqueta fija para usar dentro de un diálogo. */
export function campoSimple({ id, etiqueta, tipo = "text", ejemplo = "", autocompletar = "off" }) {
  const entrada = el("input", { id, type: tipo, placeholder: ejemplo, autocomplete: autocompletar, spellcheck: "false", autocapitalize: "off" });
  return { nodo: el("div", { clase: "campo" }, el("label", { for: id, texto: etiqueta }), el("div", { clase: "entrada" }, entrada)), entrada };
}
