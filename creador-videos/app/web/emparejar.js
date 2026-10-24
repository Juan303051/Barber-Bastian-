// Emparejar un aparato nuevo (modo «iPhone por Wi-Fi»): el código aparece en la Terminal del Mac, no aquí. Sin él, este aparato no ve nada de Iris.
import { el, logo, poner } from "./util.js";

const raiz = document.getElementById("raiz");
const LARGO = 8;

const entrada = el("input", {
  id: "codigo", name: "codigo", type: "text", clase: "codigo", maxlength: "12", required: true, "aria-describedby": "codigo-ayuda codigo-msg",
  autocomplete: "off", autocapitalize: "characters", autocorrect: "off", spellcheck: "false", inputmode: "text", placeholder: "ABCD-EFGH",
});
const mensaje = el("div", { id: "codigo-msg", clase: "mensaje-campo", role: "alert" });
const boton = el("button", { type: "submit", clase: "boton principal" }, el("span", { texto: "Emparejar este aparato" }));
const formulario = el("form", { clase: "formulario", novalidate: true },
  el("div", { clase: "campo" },
    el("label", { for: "codigo", texto: "Código de la Terminal" }),
    el("div", { clase: "entrada" }, entrada),
    el("p", { id: "codigo-ayuda", clase: "ayuda-campo", texto: "Son 8 letras y números. Se ven en la ventana de la Terminal de tu Mac, debajo de «Código para este aparato»." }),
    mensaje),
  boton);

const tarjeta = el("section", { clase: "acceso-tarjeta vidrio", "aria-labelledby": "emparejar-titulo" },
  el("div", { clase: "marca" }, logo(),
    el("h1", { id: "emparejar-titulo", clase: "titulo-grande", texto: "Empareja este aparato" }),
    el("p", { clase: "subtitulo", texto: "Iris corre en tu Mac. Para abrirla aquí, escribe el código que muestra su Terminal." })),
  formulario,
  el("p", { clase: "nota-red", texto: "La conexión por Wi-Fi no va cifrada: úsala solo en tu red de casa, nunca en una red pública." }));
poner(raiz, el("main", { id: "contenido", clase: "acceso" }, tarjeta));
entrada.focus();

const ocupado = (si) => {
  boton.disabled = si;
  poner(boton, si ? [el("span", { clase: "giro", "aria-hidden": "true" }), el("span", { texto: "Comprobando…" })] : el("span", { texto: "Emparejar este aparato" }));
};

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const codigo = entrada.value.toUpperCase().replace(/[^A-Z0-9]/g, "");
  entrada.setAttribute("aria-invalid", "false");
  if (codigo.length !== LARGO) {
    mensaje.textContent = `El código tiene ${LARGO} letras y números.`;
    entrada.setAttribute("aria-invalid", "true");
    entrada.focus();
    return;
  }
  mensaje.textContent = "";
  ocupado(true);
  try {
    const respuesta = await fetch("/api/emparejar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ codigo }), credentials: "same-origin" });
    const cuerpo = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) throw new Error(cuerpo.mensaje || "No pude comprobar el código. Inténtalo de nuevo.");
    location.replace("/");
  } catch (error) {
    ocupado(false);
    mensaje.textContent = error instanceof TypeError ? "No puedo hablar con Iris. ¿Sigue abierta la Terminal del Mac y estás en la misma Wi-Fi?" : error.message;
    entrada.setAttribute("aria-invalid", "true");
    tarjeta.classList.remove("agitar");
    void tarjeta.offsetWidth;
    tarjeta.classList.add("agitar");
    entrada.select();
  }
});
