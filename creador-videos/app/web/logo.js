// Logo de cada marca: se sube una vez, vive en los datos privados de Iris y se anima al final de los videos que lo pidan.
import { api, subir } from "./api.js";
import { aviso, dialogo } from "./ui.js";
import { el } from "./util.js";

export async function abrirLogo({ marca, nombre, tieneLogo, alCambiar }) {
  if (!marca) {
    aviso("Elige primero la marca de este video para poder subir su logo.", { tipo: "error" });
    return;
  }
  const archivo = el("input", { type: "file", id: "logo-archivo", accept: "image/png,image/webp,image/jpeg,.png,.webp,.jpg,.jpeg", "aria-describedby": "logo-ayuda" });
  const derechos = el("input", { type: "checkbox", id: "logo-derechos" });
  const vista = el("div", { clase: "logo-vista" }, tieneLogo
    ? el("img", { src: `/api/marcas/${encodeURIComponent(marca)}/logo?v=${Date.now()}`, alt: `Logo actual de ${nombre}` })
    : el("span", { clase: "ayuda", texto: "Todavía no hay un logo para esta marca." }));
  const cuerpo = el("div", { clase: "formulario" }, vista,
    el("div", { clase: "campo" }, el("label", { for: "logo-archivo", texto: tieneLogo ? "Elegir un logo nuevo" : "Elegir el logo" }), archivo,
      el("p", { clase: "ayuda", id: "logo-ayuda", texto: "Mejor un PNG con fondo transparente. Se guarda solo en tu equipo y nunca se sube al repositorio." })),
    el("div", { clase: "fila-recordar" }, el("label", { for: "logo-derechos", texto: "Tengo derecho a usar este logo (es mío o de la marca)" }), el("span", { clase: "interruptor" }, derechos, el("span"))));
  const acciones = [{ texto: "Ahora no", valor: false }];
  if (tieneLogo) acciones.push({ texto: "Quitar el logo", valor: "quitar", clase: "peligro" });
  acciones.push({ texto: tieneLogo ? "Cambiar logo" : "Subir logo", valor: "subir", clase: "principal" });
  const resultado = await dialogo({
    titulo: `Logo de ${nombre}`, texto: "Iris lo anima (entra con un brillo) al final de los videos que pidan «logo animado».", cuerpo, acciones,
    alValidar: async (valor) => {
      try {
        if (valor === "quitar") { await api.logoBorrar(marca); return null; }
        const elegido = archivo.files[0];
        if (!elegido) return "Elige primero la imagen del logo.";
        if (!derechos.checked) return "Marca la casilla para confirmar que tienes derecho a usar este logo.";
        await subir(`/api/marcas/${encodeURIComponent(marca)}/logo?derechos=1`, elegido, () => {});
        return null;
      } catch (error) { return error.message; }
    },
  });
  if (resultado === "subir" || resultado === "quitar") {
    aviso(resultado === "subir" ? `Logo de ${nombre} guardado.` : `Se quitó el logo de ${nombre}.`);
    await alCambiar();
  }
}
