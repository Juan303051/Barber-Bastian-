// Avisos emergentes, cuadros de diálogo y anuncios para lectores de pantalla.
import { el, icono, poner } from "./util.js";

const contenedorAvisos = () => document.getElementById("avisos");

/** Aviso breve abajo. Con `accion` ofrece un botón (por ejemplo «Deshacer»). Devuelve una función para cerrarlo. */
export function aviso(texto, { tipo = "info", accion = null, duracion = 5000 } = {}) {
  const botonAccion = accion ? el("button", { clase: "boton suave pequeno", texto: accion.texto }) : null;
  const cerrar = () => { nodo.remove(); clearTimeout(temporizador); };
  const nodo = el("div", { clase: `emergente vidrio ${tipo === "error" ? "error" : ""}` },
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

/** Aviso informativo de cookies. Iris solo usa lo imprescindible, así que no bloquea nada ni pide permiso; los dos botones pesan lo mismo. */
export function mostrarAvisoCookies() {
  let visto = false;
  try { visto = localStorage.getItem("iris-aviso-cookies") === "1"; } catch { /* sin almacenamiento */ }
  if (visto || document.getElementById("aviso-cookies")) return;
  const cerrar = () => { try { localStorage.setItem("iris-aviso-cookies", "1"); } catch { /* sin almacenamiento */ } nodo.remove(); document.body.classList.remove("con-aviso-cookies"); };
  const entendido = el("button", { type: "button", clase: "boton", texto: "Entendido" });
  const ver = el("a", { clase: "boton", href: "/legal/cookies.html", target: "_blank", rel: "noopener", texto: "Ver la política" });
  const nodo = el("div", { id: "aviso-cookies", clase: "aviso-cookies vidrio", role: "region", "aria-label": "Aviso de cookies" },
    el("p", {}, el("strong", { texto: "Solo cookies imprescindibles " }), "para mantener tu sesión. Sin publicidad ni terceros: no hace falta tu permiso."),
    el("div", { clase: "acciones" }, entendido, ver));
  entendido.addEventListener("click", cerrar);
  ver.addEventListener("click", cerrar);
  document.body.append(nodo);
  document.body.classList.add("con-aviso-cookies"); // deja espacio al final de la página para que el aviso no tape nada
}

/** Enlaces a los textos legales para el pie de cada pantalla. */
export function pieLegal() {
  const enlace = (texto, ruta) => el("li", {}, el("a", { href: `/legal/${ruta}.html`, target: "_blank", rel: "noopener", texto }));
  return el("ul", { clase: "pie-legal", "aria-label": "Textos legales" }, enlace("Privacidad", "privacidad"), enlace("Términos", "terminos"), enlace("Reembolsos", "reembolsos"), enlace("Cookies", "cookies"));
}
