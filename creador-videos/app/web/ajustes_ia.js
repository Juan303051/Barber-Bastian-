// Ajustes del director con IA: activar, elegir modelo, guardar la clave (solo se envía al servidor de este equipo) y probar la conexión.
import { api } from "./api.js";
import { aviso, dialogo } from "./ui.js";
import { el, icono, poner } from "./util.js";

export async function abrirAjustesIA(alCambiar) {
  const estado = await api.ia();
  const activa = el("input", { type: "checkbox", id: "ia-activa", checked: estado.activa });
  const fotogramas = el("input", { type: "checkbox", id: "ia-fotogramas", checked: estado.ver_fotogramas });
  const modelo = el("select", { id: "ia-modelo" }, estado.modelos.map((m) => el("option", { value: m.id, texto: m.nombre, selected: m.id === estado.modelo })));
  const clave = el("input", { id: "ia-clave-nueva", type: "password", autocomplete: "off", spellcheck: "false", placeholder: estado.final_clave ? `Clave guardada (${estado.final_clave})` : "Pega aquí tu clave de Anthropic", "aria-describedby": "ia-clave-ayuda" });
  const resultado = el("div", { clase: "mensaje-campo", role: "status" });
  const botonProbar = el("button", { type: "button", clase: "boton pequeno" }, icono("rayo"), "Probar conexión");
  const botonBorrar = el("button", { type: "button", clase: "boton suave pequeno peligro", hidden: estado.origen !== "archivo" }, icono("papelera"), "Borrar la clave guardada");

  const origen = { entorno: "Usa la clave de la variable de entorno ANTHROPIC_API_KEY.", perfil: "Usa la sesión iniciada con «ant auth login».", archivo: `Hay una clave guardada en este equipo (${estado.final_clave}).` }[estado.origen];
  const fila = (casilla, titulo, ayuda) => el("div", { clase: "opcion" }, el("label", { clase: "texto", for: casilla.id }, el("strong", { texto: titulo }), el("span", { texto: ayuda })), el("span", { clase: "interruptor" }, casilla, el("span")));
  const cuerpo = el("div", { clase: "formulario" },
    el("p", { clase: "estado-ia" }, icono(estado.disponible ? "ok-circulo" : "info"), origen || "Todavía no hay una clave: Iris dirige con reglas. Con una clave, un director con IA propone el gancho, el énfasis y el acabado."),
    fila(activa, "Dirigir con IA", "Si la IA falla, el video se hace igual con reglas."),
    el("div", { clase: "campo" }, el("label", { for: modelo.id, clase: "rotulo", texto: "Modelo" }), el("div", { clase: "entrada" }, modelo, icono("abajo")),
      el("p", { clase: "ayuda", texto: "Costo estimado por video: unos 0,05–0,20 USD con el modelo de calidad máxima y la mitad con el equilibrado (estimación, depende del largo del video)." })),
    fila(fotogramas, "Dejar que la IA vea el video", "Envía 6 imágenes pequeñas del video. Si lo apagas, la IA solo recibe el texto."),
    el("div", { clase: "campo" }, el("label", { for: clave.id, clase: "rotulo", texto: "Clave de Anthropic" }), el("div", { clase: "entrada" }, clave),
      el("p", { id: "ia-clave-ayuda", clase: "ayuda", texto: "Se guarda solo en este equipo, con permisos de lectura solo para ti, y nunca vuelve al navegador. Para más seguridad, usa la variable de entorno ANTHROPIC_API_KEY." }),
      el("div", { clase: "acciones-fila" }, botonProbar, botonBorrar), resultado),
    el("p", { clase: "ayuda aviso-privacidad" }, icono("escudo"), "Con la IA activa, a Anthropic se envía: el texto de lo que dices en el video con sus tiempos, tu instrucción, la ficha de la marca y tus respuestas del test. Tus videos y tus canciones no se envían."));

  async function guardar() {
    const cambios = { activa: activa.checked, ver_fotogramas: fotogramas.checked, modelo: modelo.value };
    if (clave.value.trim()) cambios.clave = clave.value.trim();
    return api.iaGuardar(cambios);
  }
  botonProbar.addEventListener("click", async () => {
    botonProbar.disabled = true;
    poner(resultado, el("span", { texto: "Probando…" }));
    try {
      await guardar();
      clave.value = "";
      const r = await api.iaProbar();
      poner(resultado, icono(r.ok ? "ok-circulo" : "aviso"), el("span", { texto: r.mensaje }));
      resultado.classList.toggle("bien", r.ok);
    } catch (error) {
      poner(resultado, icono("aviso"), el("span", { texto: error.message }));
    } finally { botonProbar.disabled = false; }
  });
  botonBorrar.addEventListener("click", async () => {
    await api.iaGuardar({ clave: "" });
    poner(resultado, icono("ok-circulo"), el("span", { texto: "Clave borrada." }));
    botonBorrar.hidden = true;
  });
  const decision = await dialogo({
    titulo: "Director con IA", texto: "Un director con IA decide el gancho, qué resaltar y el acabado de cada video, dentro de límites que Iris hace cumplir.", cuerpo,
    acciones: [{ texto: "Cerrar", valor: false }, { texto: "Guardar", valor: "ok", clase: "principal" }],
    alValidar: async () => { try { await guardar(); return null; } catch (error) { return error.message; } },
  });
  if (decision === "ok") aviso("Ajustes de la IA guardados.");
  alCambiar();
}
