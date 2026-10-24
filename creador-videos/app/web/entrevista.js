// El «test del director»: una pregunta por pantalla, con progreso y sin salir de la página. Sus respuestas las usa Iris con o sin IA.
import { api } from "./api.js";
import { aviso } from "./ui.js";
import { el, icono, poner } from "./util.js";

export async function abrirEntrevista({ marcas, marcaInicial = "" }) {
  let marca = marcaInicial;
  let datos = await api.perfil(marca);
  const respuestas = { ...datos.respuestas };
  const preguntas = datos.preguntas;
  let paso = -1; // -1: elegir para qué marca; luego 0…n-1

  const dialogo = el("dialog", { "aria-labelledby": "entrevista-titulo" });
  const forma = el("form", { clase: "hoja entrevista", method: "dialog" });
  dialogo.append(forma);
  document.body.append(dialogo);

  return new Promise((resolver) => {
    const cerrar = (valor) => { dialogo.close(); dialogo.remove(); resolver(valor); };
    dialogo.addEventListener("cancel", (e) => { e.preventDefault(); cerrar(false); });

    function pintar() {
      const total = preguntas.length;
      const cabecera = el("div", { clase: "entrevista-cabecera" },
        el("h2", { id: "entrevista-titulo", texto: "Test del director" }),
        paso >= 0 ? el("span", { clase: "entrevista-progreso", texto: `${paso + 1} de ${total}` }) : null);
      const barra = el("div", { clase: "progreso-pista", "aria-hidden": "true" }, el("i"));
      barra.querySelector("i").style.setProperty("--p", `${Math.round(((paso + 1) / (total + 1)) * 100)}%`);
      const contenido = el("div", { clase: "entrevista-cuerpo" });
      const atras = el("button", { type: "button", clase: "boton", texto: paso <= -1 ? "Cancelar" : "Atrás" });
      const siguiente = el("button", { type: "button", clase: "boton principal", texto: paso === total - 1 ? "Guardar mi director" : "Siguiente" });

      if (paso === -1) {
        const selector = el("select", { id: "entrevista-marca" }, [el("option", { value: "", texto: "General (todas las marcas)", selected: marca === "" }), ...marcas.map((m) => el("option", { value: m.id, texto: m.nombre, selected: m.id === marca }))]);
        selector.addEventListener("change", async () => { marca = selector.value; datos = await api.perfil(marca); Object.keys(respuestas).forEach((k) => delete respuestas[k]); Object.assign(respuestas, datos.respuestas); });
        poner(contenido, el("p", { texto: "Diez preguntas cortas para que Iris sepa cómo quieres tus videos. Las usa con o sin IA, y puedes cambiarlas cuando quieras." }),
          el("div", { clase: "campo" }, el("label", { for: selector.id, clase: "rotulo", texto: "¿Para quién es este director?" }), el("div", { clase: "entrada" }, selector, icono("abajo"))));
        siguiente.textContent = "Empezar";
      } else {
        const pregunta = preguntas[paso];
        const grupo = el("fieldset", { clase: "pregunta" }, el("legend", { texto: pregunta.texto }));
        if (pregunta.tipo === "uno") {
          const lista = el("div", { clase: "opciones-lista", role: "radiogroup" });
          pregunta.opciones.forEach(([valor, texto]) => {
            const radio = el("input", { type: "radio", name: `p-${pregunta.id}`, value: valor, checked: respuestas[pregunta.id] === valor });
            radio.addEventListener("change", () => { respuestas[pregunta.id] = valor; });
            lista.append(el("label", { clase: "opcion-radio" }, radio, el("span", { texto })));
          });
          grupo.append(lista);
        } else {
          const campo = el("input", { type: "text", id: `p-${pregunta.id}`, maxlength: String(pregunta.max), placeholder: pregunta.ejemplo || "", value: respuestas[pregunta.id] || "", "aria-label": pregunta.texto, autocomplete: "off" });
          campo.addEventListener("input", () => { respuestas[pregunta.id] = campo.value; });
          campo.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); siguiente.click(); } });
          grupo.append(el("div", { clase: "entrada" }, campo), el("p", { clase: "ayuda", texto: "Puedes dejarla en blanco." }));
        }
        poner(contenido, grupo);
      }
      atras.addEventListener("click", () => { if (paso <= -1) cerrar(false); else { paso -= 1; pintar(); } });
      siguiente.addEventListener("click", async () => {
        if (paso < total - 1) { paso += 1; pintar(); return; }
        siguiente.disabled = true;
        try {
          await api.perfilGuardar(marca, respuestas);
          aviso(marca ? "Guardé el director de esta marca." : "Guardé tu director general.");
          cerrar(true);
        } catch (error) {
          siguiente.disabled = false;
          aviso(error.message, { tipo: "error" });
        }
      });
      poner(forma, cabecera, barra, contenido, el("div", { clase: "acciones" }, atras, siguiente));
      (contenido.querySelector("input:checked, input[type=text], select, input") ?? siguiente).focus();
    }
    pintar();
    dialogo.showModal();
  });
}
