// Tarjeta de un video: formulario (video + instrucciones), construcción en vivo y resultado. Se crea una vez y se va actualizando,
// así lo que la persona está escribiendo nunca se pierde cuando llegan novedades del servidor.
import { api, ErrorApi, subir } from "./api.js";
import { anunciar, aviso, dialogo } from "./ui.js";
import { aproximado, debounce, el, esVideo, establecerProgreso, formatoTiempo, icono, poner } from "./util.js";

const IDIOMAS = [["", "Automático"], ["es", "Español"], ["en", "English"], ["pt", "Português"]];
const INTERRUPTORES = [
  ["quitar_pausas", "Quitar pausas largas", "Corta los silencios para que el video no se sienta lento.", false],
  ["acercamientos", "Acercamientos", "Un zoom suave en una de cada dos frases para dar ritmo.", true],
  ["insignias", "Pasos numerados", "Si dices «primero, segundo…», pone el 1, 2, 3 en pantalla.", true],
  ["contadores", "Contadores de cifras", "Si dices una cifra, la muestra contando hacia arriba.", true],
  ["cierre", "Cierre con palabra clave", "Si dices «comenta EDITOR», lo destaca al final.", true],
  ["color_referencias", "Usar el color de mis referencias", "Toma el color dominante de los videos de referencia.", false],
  ["musica", "Música de fondo", "Elige una canción de tu biblioteca y la mezcla bajo tu voz.", true],
  ["ia", "Director con IA", "Una IA propone el gancho, qué resaltar y el acabado.", true],
  ["borrador", "Borrador rápido", "A la mitad de tamaño: se construye mucho más deprisa para probar.", false],
];
const ACABADOS = [["auto", "Que decida Iris"], ["natural", "Natural"], ["calido", "Cálido"], ["frio", "Frío"], ["cine", "Cine"], ["vibrante", "Vibrante"]];
const SUGERENCIAS = [
  ["Palabras en grande", "Resalta las palabras: "],
  ["Quitar pausas", "Quita las pausas largas."],
  ["Antes y después", "Hazlo en formato antes y después."],
  ["Cierre con «Comenta…»", "Cierra pidiendo que comenten la palabra: "],
  ["Subtítulos abajo", "Subtítulos abajo."],
];
const ESTADOS_ACTIVOS = new Set(["en_cola", "trabajando"]);

export function crearTrabajo(id, contexto) {
  const local = { editando: false, fraccionSubida: null, ultimoFotograma: -1, cuadros: [], firmaPasos: "", ultimoPaso: null, interpretadoEn: 0, anunciado: "", viendoVivo: false };

  // ───────────────────────────────────────────────────────── cabecera
  const numero = el("span", { clase: "trabajo-numero" });
  const titulo = el("input", { clase: "trabajo-titulo", maxlength: "80", "aria-label": "Nombre del video", spellcheck: "false" });
  const marca = el("select", { id: `marca-${id}`, "aria-label": "Marca de este video" });
  const cajaMarca = el("div", { clase: "entrada trabajo-marca" }, marca, icono("abajo"));
  const borrar = el("button", { type: "button", clase: "boton suave cuadrado peligro", "aria-label": "Quitar este video", title: "Quitar este video" }, icono("papelera"));
  const cabecera = el("div", { clase: "trabajo-cabecera" }, numero, titulo, cajaMarca, borrar);

  // ───────────────────────────────────────────────────────── formulario: video de origen
  const entradaArchivo = el("input", { type: "file", accept: "video/*,.mp4,.mov,.m4v,.webm,.mkv", hidden: true, "aria-label": "Elegir el video que quieres editar" });
  const zonaSoltar = el("div", { clase: "soltar", role: "button", tabindex: "0", "aria-label": "Elegir o soltar el video que quieres editar" },
    icono("subir"), el("strong", { texto: "Suelta tu video aquí" }), el("span", { clase: "fino", texto: "o haz clic para elegirlo" }));
  const miniatura = el("img", { alt: "Vista previa del video que subiste", hidden: true });
  const progresoSubida = el("div", { clase: "progreso", hidden: true }, el("div", { clase: "progreso-pista" }, el("i")), el("div", { clase: "progreso-texto" }, el("span")));
  const visor = el("div", { clase: "visor" }, zonaSoltar, miniatura, progresoSubida);
  const nombreArchivo = el("div", { clase: "nombre" });
  const cambiar = el("button", { type: "button", clase: "boton pequeno", hidden: true }, icono("subir"), "Cambiar video");
  const fuente = el("div", { clase: "fuente" }, visor, nombreArchivo, cambiar, entradaArchivo);

  // ───────────────────────────────────────────────────────── formulario: instrucciones
  const pedido = el("textarea", { id: `pedido-${id}`, maxlength: "4000", rows: "4", placeholder: "Ejemplo: Subtítulos dinámicos, resalta las palabras dinero y gratis, quita las pausas y cierra pidiendo que comenten EDITOR." });
  const chips = el("div", { clase: "sugerencias", role: "group", "aria-label": "Atajos para escribir lo que quieres" },
    SUGERENCIAS.map(([texto, frase]) => el("button", { type: "button", datos: { frase } }, icono("mas", "pequeno-icono"), texto)));
  const entendido = el("div", { clase: "entendido", "aria-live": "off" });
  const sugeridas = el("div", { clase: "sugeridas" });
  const interruptores = new Map();
  let ayudaIA = null;
  const filas = INTERRUPTORES.map(([clave, nombre, ayuda, defecto]) => {
    const entrada = el("input", { type: "checkbox", id: `opc-${clave}-${id}`, checked: defecto });
    interruptores.set(clave, { entrada, defecto });
    const textoAyuda = el("span", { texto: ayuda });
    if (clave === "ia") ayudaIA = textoAyuda;
    return el("div", { clase: "opcion" }, el("label", { clase: "texto", for: entrada.id }, el("strong", { texto: nombre }), textoAyuda), el("span", { clase: "interruptor" }, entrada, el("span")));
  });
  const acabado = el("select", { id: `acabado-${id}` }, ACABADOS.map(([valor, texto]) => el("option", { value: valor, texto })));
  const botonTest = el("button", { type: "button", clase: "boton pequeno" }, icono("director"), "Hacer o cambiar el test");
  const nombreFormato = `formato-${id}`;
  const radios = [["subtitulos", "Subtítulos dinámicos"], ["antes-despues", "Antes y después"]].map(([valor, texto]) =>
    el("label", {}, el("input", { type: "radio", name: nombreFormato, value: valor, checked: valor === "subtitulos" }), texto));
  const idioma = el("select", { id: `idioma-${id}` }, IDIOMAS.map(([valor, texto]) => el("option", { value: valor, texto })));
  const avanzado = el("details", { clase: "avanzado" },
    el("summary", {}, icono("abajo"), "Opciones avanzadas"),
    el("div", { clase: "opciones" },
      el("div", { clase: "opcion" }, el("div", { clase: "texto" }, el("strong", { texto: "Formato" }), el("span", { texto: "Cómo se muestra tu video." })), el("div", { clase: "segmentado", role: "radiogroup", "aria-label": "Formato" }, radios)),
      filas,
      el("div", { clase: "opcion" }, el("label", { clase: "texto", for: acabado.id }, el("strong", { texto: "Acabado de color" }), el("span", { texto: "Un ajuste suave de color y contraste sobre tu toma." })), el("div", { clase: "entrada" }, acabado, icono("abajo"))),
      el("div", { clase: "opcion" }, el("label", { clase: "texto", for: idioma.id }, el("strong", { texto: "Idioma del video" }), el("span", { texto: "Si lo dejas en automático, Iris lo detecta." })), el("div", { clase: "entrada" }, idioma, icono("abajo"))),
      el("div", { clase: "opcion" }, el("div", { clase: "texto" }, el("strong", { texto: "Test del director" }), el("span", { texto: "Tono, ritmo, música y lo que nunca debe aparecer en esta marca." })), botonTest)));
  const cuerpoPedido = el("div", { clase: "pedido" },
    el("div", { clase: "campo" }, el("label", { for: pedido.id, clase: "rotulo", texto: "Cuéntale a Iris cómo lo quieres" }), el("div", { clase: "entrada" }, pedido)),
    chips, entendido, sugeridas, avanzado);
  const cuerpoFormulario = el("div", { clase: "trabajo-cuerpo" }, fuente, cuerpoPedido);

  // ───────────────────────────────────────────────────────── formulario: pie
  const estadoTexto = el("div", { clase: "estado-texto" });
  const botonCrear = el("button", { type: "button", clase: "boton" }, icono("varita"), "Crear este video");
  const pie = el("div", { clase: "trabajo-pie" }, estadoTexto, botonCrear);
  const formulario = el("div", {}, cuerpoFormulario, pie);

  // ───────────────────────────────────────────────────────── construcción en vivo
  const imagenVivo = el("img", { alt: "Vista previa del video mientras se construye", hidden: true });
  const imagenBase = el("img", { clase: "base-tenue", alt: "", hidden: true });
  const sello = el("div", { clase: "sello", hidden: true });
  const telefono = el("div", { clase: "telefono" }, el("div", { clase: "pantalla" }, imagenBase, imagenVivo, el("div", { clase: "destello" }), sello));
  const listaEtapas = el("ol", { clase: "etapas", "aria-label": "Etapas de la creación" });
  const pistaVivo = el("div", { clase: "progreso-pista", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": "100", "aria-label": "Avance del video" }, el("i"));
  const textoPorcentaje = el("span");
  const textoTiempo = el("span");
  const tira = el("div", { clase: "tira", "aria-hidden": "true" }, Array.from({ length: 12 }, () => el("div", { clase: "cuadro" }, el("img", { alt: "" }))));
  const cancelar = el("button", { type: "button", clase: "boton" }, icono("x"), "Cancelar");
  const vivo = el("div", { clase: "vivo", hidden: true }, telefono,
    el("div", { clase: "vivo-lado" }, listaEtapas, el("div", { clase: "progreso" }, pistaVivo, el("div", { clase: "progreso-texto" }, textoPorcentaje, textoTiempo)), tira, el("div", {}, cancelar)));

  // ───────────────────────────────────────────────────────── resultado
  const video = el("video", { controls: true, playsinline: true, preload: "metadata" });
  const marcoResultado = el("div", { clase: "telefono" }, el("div", { clase: "pantalla" }, video));
  const tituloListo = el("div", { clase: "listo" }, icono("ok-circulo"), el("span", { texto: "Tu video está listo" }));
  const notasListo = el("div", { clase: "notas" });
  const calidadCaja = el("div", { clase: "calidad" });
  const direccionCaja = el("div", { clase: "direccion" });
  const descargar = el("a", { clase: "boton principal", href: `/api/trabajos/${id}/resultado?descargar=1` }, icono("descargar"), "Descargar");
  const editarOtra = el("button", { type: "button", clase: "boton" }, icono("varita"), "Cambiar y volver a crear");
  const resultado = el("div", { clase: "resultado", hidden: true }, marcoResultado,
    el("div", { clase: "vivo-lado" }, tituloListo, calidadCaja, direccionCaja, notasListo, el("div", { clase: "resultado-acciones" }, descargar, editarOtra)));

  const nodo = el("article", { clase: "trabajo", "aria-labelledby": `titulo-${id}` },
    el("h3", { id: `titulo-${id}`, clase: "solo-lector" }), cabecera, formulario, vivo, resultado);
  const rotuloOculto = nodo.querySelector("h3");

  // ───────────────────────────────────────────────────────── comportamiento
  const opcionesActuales = () => {
    const o = { formato: radios.map((r) => r.querySelector("input")).find((i) => i.checked)?.value || "subtitulos", idioma: idioma.value || null, acabado: acabado.value || "auto", calidad: interruptores.get("borrador").entrada.checked ? "borrador" : "completa" };
    for (const [clave, { entrada }] of interruptores) if (clave !== "borrador") o[clave] = entrada.checked;
    return o;
  };
  const guardarPedido = debounce(() => api.trabajoCambiar(id, { prompt: pedido.value }).catch(() => {}), 700);
  const interpretar = debounce(async () => {
    try {
      const r = await api.interpretar(pedido.value, opcionesActuales());
      local.interpretadoEn = Date.now();
      pintarEntendido(r.entendido, r.pendiente, r.sugerencias);
    } catch { /* se queda lo anterior */ }
  }, 400);
  const guardarOpciones = () => api.trabajoCambiar(id, { opciones: opcionesActuales() }).then(() => interpretar.ahora()).catch((e) => aviso(e.message, { tipo: "error" }));

  pedido.addEventListener("input", () => { guardarPedido(); interpretar(); });
  pedido.addEventListener("blur", () => guardarPedido.ahora());
  chips.addEventListener("click", (e) => {
    const boton = e.target.closest("button");
    if (!boton) return;
    const separador = pedido.value && !/\s$/.test(pedido.value) ? " " : "";
    pedido.value += separador + boton.dataset.frase;
    pedido.focus();
    pedido.setSelectionRange(pedido.value.length, pedido.value.length);
    pedido.dispatchEvent(new Event("input"));
  });
  for (const { entrada } of interruptores.values()) entrada.addEventListener("change", guardarOpciones);
  radios.forEach((r) => r.querySelector("input").addEventListener("change", guardarOpciones));
  idioma.addEventListener("change", guardarOpciones);
  acabado.addEventListener("change", guardarOpciones);
  botonTest.addEventListener("click", () => contexto.perfil(marca.value));
  sugeridas.addEventListener("click", async (e) => {
    const boton = e.target.closest("button");
    if (!boton) return;
    const o = opcionesActuales();
    o[boton.dataset.clave] = boton.dataset.clave === "formato" ? "antes-despues" : true;
    await api.trabajoCambiar(id, { opciones: o }).catch(() => {});
    sincronizarOpciones(o, true);
    interpretar.ahora();
  });

  titulo.addEventListener("change", () => api.trabajoCambiar(id, { titulo: titulo.value }).catch(() => {}));
  titulo.addEventListener("keydown", (e) => { if (e.key === "Enter") titulo.blur(); });
  marca.addEventListener("change", () => api.trabajoCambiar(id, { marca: marca.value || null }).catch((e) => aviso(e.message, { tipo: "error" })));
  borrar.addEventListener("click", () => contexto.quitar(id));
  editarOtra.addEventListener("click", () => { local.editando = true; contexto.refrescar(); });

  const elegir = () => entradaArchivo.click();
  zonaSoltar.addEventListener("click", elegir);
  zonaSoltar.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(); } });
  cambiar.addEventListener("click", elegir);
  entradaArchivo.addEventListener("change", () => { const archivo = entradaArchivo.files[0]; entradaArchivo.value = ""; if (archivo) subirVideo(archivo); });
  const sobre = (e) => {
    e.preventDefault();
    const items = [...(e.dataTransfer?.items || [])];
    const valido = !items.length || items.some((i) => i.kind === "file" && (i.type === "" || i.type.startsWith("video/")));
    visor.classList.toggle("sobre", valido);
    visor.classList.toggle("invalido", !valido);
    if (e.dataTransfer) e.dataTransfer.dropEffect = valido ? "copy" : "none";
  };
  visor.addEventListener("dragenter", sobre);
  visor.addEventListener("dragover", sobre);
  visor.addEventListener("dragleave", (e) => { if (!visor.contains(e.relatedTarget)) visor.classList.remove("sobre", "invalido"); });
  visor.addEventListener("drop", (e) => {
    e.preventDefault();
    visor.classList.remove("sobre", "invalido");
    const archivo = [...e.dataTransfer.files].find(esVideo);
    if (!archivo) { aviso("Ese archivo no es un video compatible. Usa MP4, MOV, M4V, WEBM o MKV.", { tipo: "error" }); return; }
    subirVideo(archivo);
  });

  async function subirVideo(archivo) {
    if (!esVideo(archivo)) { aviso("Ese archivo no es un video compatible. Usa MP4, MOV, M4V, WEBM o MKV.", { tipo: "error" }); return; }
    local.fraccionSubida = 0;
    pintarSubida();
    try {
      await subir(`/api/trabajos/${id}/video`, archivo, (f) => { local.fraccionSubida = f; pintarSubida(); });
      aviso("Video subido. Ahora cuéntale a Iris cómo lo quieres.");
    } catch (error) {
      aviso(error.message, { tipo: "error" });
    } finally {
      local.fraccionSubida = null;
      pintarSubida();
      contexto.refrescar();
    }
  }

  function pintarSubida() {
    const subiendo = local.fraccionSubida !== null;
    progresoSubida.hidden = !subiendo;
    zonaSoltar.classList.toggle("cargando", subiendo);
    if (subiendo) {
      establecerProgreso(progresoSubida.querySelector(".progreso-pista"), local.fraccionSubida);
      progresoSubida.querySelector("span").textContent = local.fraccionSubida >= 0.999 ? "Comprobando el video…" : `Subiendo… ${Math.round(local.fraccionSubida * 100)} %`;
    }
  }

  botonCrear.addEventListener("click", () => contexto.crear(id));
  cancelar.addEventListener("click", async () => {
    const decision = await dialogo({
      titulo: "¿Cancelar este video?", texto: "Se pierde lo que Iris lleva construido de este video. Tu video original y tus instrucciones se quedan guardados.",
      acciones: [{ texto: "Cancelar video", valor: "si", clase: "peligro-lleno" }, { texto: "Seguir creando", valor: "no", clase: "principal" }],
    });
    if (decision === "si") { await api.cancelar(id).catch((e) => aviso(e.message, { tipo: "error" })); contexto.refrescar(); }
  });

  const iconoDe = { texto: "texto", estrella: "estrella", mensaje: "mensaje", tijeras: "tijeras", color: "color", musica: "musica" };
  function pintarEntendido(lista, pendientes, sugerencias) {
    const filasEntendido = lista.map((f) => el("li", {}, icono(iconoDe[f.icono] || "info"), f.texto));
    const filasPendiente = (pendientes || []).map((t) => el("li", { clase: "pendiente" }, icono("aviso"), t));
    poner(entendido, el("h4", { texto: "Esto entendí" }), el("ul", {}, filasEntendido, filasPendiente));
    poner(sugeridas, (sugerencias || []).map((s) => el("div", { clase: "sugerida" }, el("span", { texto: `Pediste algo parecido a «${s.texto}».` }),
      el("button", { type: "button", clase: "boton pequeno", datos: { clave: s.clave }, texto: "Activar" }))));
  }

  function sincronizarOpciones(o, forzar = false) {
    if (!forzar && avanzado.contains(document.activeElement)) return;
    for (const [clave, { entrada, defecto }] of interruptores) {
      const valor = clave === "borrador" ? o.calidad === "borrador" : (o[clave] ?? defecto);
      if (entrada.checked !== valor) entrada.checked = valor;
    }
    radios.forEach((r) => { const i = r.querySelector("input"); i.checked = i.value === (o.formato || "subtitulos"); });
    idioma.value = o.idioma || "";
    acabado.value = o.acabado || "auto";
  }

  // ───────────────────────────────────────────────────────── construcción en vivo: pintar
  function pintarVivo(t) {
    telefono.classList.toggle("horizontal", !t.vertical);
    tira.classList.toggle("horizontal", !t.vertical);
    const pasos = t.estado === "en_cola" ? [{ clave: "cola", texto: "Esperando su turno" }, ...t.pasos] : t.pasos;
    const firma = pasos.map((p) => p.clave).join(",");
    if (firma !== local.firmaPasos) {
      local.firmaPasos = firma;
      poner(listaEtapas, pasos.map((p) => el("li", { clase: "etapa", datos: { clave: p.clave } },
        el("span", { clase: "punto" }, icono("ok")), el("span", {}, p.texto, el("span", { clase: "detalle" })))));
    }
    const actual = Math.max(0, pasos.findIndex((p) => p.clave === t.paso));
    [...listaEtapas.children].forEach((li, i) => {
      li.classList.toggle("hecha", i < actual);
      li.classList.toggle("actual", i === actual);
      i === actual ? li.setAttribute("aria-current", "step") : li.removeAttribute("aria-current");
      const detalle = li.querySelector(".detalle");
      const texto = i === actual ? (t.paso === "render" && t.fotogramas_total ? `Fotograma ${Math.min(t.fotogramas_listos, t.fotogramas_total)} de ${t.fotogramas_total}` : t.mensaje || "") : "";
      if (detalle.textContent !== texto) detalle.textContent = texto;
    });
    const fraccion = t.progreso || 0;
    establecerProgreso(pistaVivo, fraccion);
    pistaVivo.setAttribute("aria-valuenow", String(Math.round(fraccion * 100)));
    textoPorcentaje.textContent = `${Math.round(fraccion * 100)} %`;
    textoTiempo.textContent = t.estado === "en_cola" ? "Esperando su turno" : t.eta ? `Faltan ${aproximado(t.eta)}` : t.paso === "voz" ? "Esto toma un rato en la primera pasada" : "";

    const enRender = t.paso === "render" && t.fotogramas_listos > 0;
    imagenBase.hidden = enRender || !t.miniatura;
    if (!imagenBase.hidden && !imagenBase.src) imagenBase.src = `/api/trabajos/${id}/miniatura`;
    sello.hidden = !enRender;
    if (enRender) {
      sello.textContent = `${Math.min(t.fotogramas_listos, t.fotogramas_total)} / ${t.fotogramas_total}`;
      const objetivo = Math.max(0, t.fotogramas_listos - 2);
      if (objetivo !== local.ultimoFotograma) {
        local.ultimoFotograma = objetivo;
        const precarga = new Image();
        precarga.onload = () => { imagenVivo.src = precarga.src; imagenVivo.hidden = false; };
        precarga.src = `/api/trabajos/${id}/fotograma?n=${objetivo}`;
      }
      tira.querySelectorAll(".cuadro img").forEach((img, i) => {
        const indice = Math.min(t.fotogramas_total - 1, Math.round(((i + 0.5) * t.fotogramas_total) / 12));
        if (!img.dataset.cargado && t.fotogramas_listos > indice + 4) {
          img.dataset.cargado = "1";
          img.onload = () => img.classList.add("visible");
          img.src = `/api/trabajos/${id}/fotograma?n=${indice}`;
        }
      });
    } else {
      imagenVivo.hidden = true;
      local.ultimoFotograma = -1;
      tira.querySelectorAll(".cuadro img").forEach((img) => { delete img.dataset.cargado; img.classList.remove("visible"); img.removeAttribute("src"); });
    }
    if (t.etapa && t.etapa !== local.anunciado) { local.anunciado = t.etapa; anunciar(`${titulo.value}: ${t.etapa}`); }
  }

  const ETIQUETA_CALIDAD = { listo: ["ok-circulo", "Listo para revisar", "exito"], revisar: ["aviso", "Revisa antes de publicar", "aviso"], error: ["x", "Hay problemas que corregir", "error"] };
  const ICONO_NIVEL = { ok: "ok-circulo", aviso: "aviso", error: "x" };

  function pintarCalidad(c) {
    if (!c) { poner(calidadCaja); return; }
    const [iconoNombre, titulo, tono] = ETIQUETA_CALIDAD[c.veredicto] || ETIQUETA_CALIDAD.revisar;
    const orden = { error: 0, aviso: 1, ok: 2 };
    const pruebas = [...c.pruebas].sort((a, b) => orden[a.nivel] - orden[b.nivel]);
    const problemas = pruebas.filter((p) => p.nivel !== "ok");
    const correctas = pruebas.filter((p) => p.nivel === "ok");
    const fila = (p) => el("li", { clase: `prueba ${p.nivel}` }, icono(ICONO_NIVEL[p.nivel]), el("span", { texto: p.texto }));
    poner(calidadCaja,
      el("h4", { clase: `calidad-titulo ${tono}` }, icono(iconoNombre), titulo),
      el("p", { clase: "ayuda", texto: c.resumen }),
      problemas.length ? el("ul", { clase: "pruebas" }, problemas.map(fila)) : null,
      correctas.length ? el("details", { clase: "avanzado pruebas-ok" }, el("summary", {}, icono("abajo"), `${correctas.length} prueba(s) en orden`), el("ul", { clase: "pruebas" }, correctas.map(fila))) : null);
  }

  function pintarDireccion(t) {
    const d = t.direccion;
    if (!d) { poner(direccionCaja); return; }
    const ia = t.ia || {};
    const etiqueta = ia.usada
      ? el("span", { clase: "etiqueta-chip exito" }, icono("varita"), `Dirigido con IA${ia.costo_usd ? ` · ≈ US$ ${ia.costo_usd.toFixed(2).replace(".", ",")}` : ""}`)
      : el("span", { clase: "etiqueta-chip" }, icono("info"), ia.motivo ? `Sin IA: ${ia.motivo}` : "Dirigido con reglas");
    const musica = t.musica ? el("span", { clase: "etiqueta-chip" }, icono("musica"), `${t.musica.titulo} · ${Math.round(t.musica.bpm)} BPM`) : null;
    poner(direccionCaja,
      el("h4", { texto: "Cómo lo dirigió Iris" }),
      el("div", { clase: "chips" }, etiqueta, musica, el("span", { clase: "etiqueta-chip", texto: `Acabado ${d.look}` })),
      d.resumen ? el("p", { clase: "ayuda", texto: d.resumen }) : null,
      d.gancho ? el("p", { clase: "gancho" }, el("strong", { texto: "Gancho: " }), `«${d.gancho}»`) : null,
      d.alternativas?.length ? el("p", { clase: "ayuda", texto: `Otras ideas de gancho: ${d.alternativas.map((a) => `«${a}»`).join(" · ")}` }) : null,
      null);
  }

  function pintarResultado(t) {
    const fuenteVideo = `/api/trabajos/${id}/resultado?v=${Math.round(t.actualizado)}`;
    if (video.dataset.fuente !== fuenteVideo) {
      video.dataset.fuente = fuenteVideo;
      video.src = fuenteVideo;
      video.poster = `/api/trabajos/${id}/miniatura?v=${Math.round(t.actualizado)}`;
    }
    marcoResultado.classList.toggle("horizontal", !t.vertical);
    pintarCalidad(t.calidad);
    pintarDireccion(t);
    poner(notasListo, (t.notas || []).map((n) => el("div", {}, "· ", n)), t.mensaje ? el("div", { clase: "ayuda", texto: t.mensaje }) : null);
  }

  // ───────────────────────────────────────────────────────── actualizar con lo que dice el servidor
  function actualizar(t, indice, marcas) {
    numero.textContent = String(indice + 1);
    rotuloOculto.textContent = `Video ${indice + 1}: ${t.titulo}`;
    if (document.activeElement !== titulo && titulo.value !== t.titulo) titulo.value = t.titulo;
    const firmaMarcas = marcas.map((m) => m.id).join(",");
    if (marca.dataset.firma !== firmaMarcas) {
      marca.dataset.firma = firmaMarcas;
      poner(marca, el("option", { value: "", texto: "Sin marca" }), marcas.map((m) => el("option", { value: m.id, texto: m.nombre })));
    }
    if (document.activeElement !== marca) marca.value = t.marca || "";

    const activo = ESTADOS_ACTIVOS.has(t.estado);
    if (activo) local.editando = false;
    const modo = activo ? "vivo" : t.estado === "listo" && !local.editando ? "resultado" : "formulario";
    formulario.hidden = modo !== "formulario";
    vivo.hidden = modo !== "vivo";
    resultado.hidden = modo !== "resultado";
    titulo.disabled = marca.disabled = borrar.disabled = false;
    if (modo === "vivo" && !local.viendoVivo) { local.viendoVivo = true; nodo.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" }); }
    if (modo !== "vivo") local.viendoVivo = false;
    if (modo === "vivo") pintarVivo(t);
    if (modo === "resultado") pintarResultado(t);

    const iaInfo = contexto.ia ? contexto.ia() : { disponible: false };
    const interruptorIA = interruptores.get("ia").entrada;
    interruptorIA.disabled = !iaInfo.disponible || !iaInfo.activa;
    if (ayudaIA) ayudaIA.textContent = !iaInfo.disponible ? "Sin clave de IA: se usan reglas. Configúrala en el menú de tu cuenta." : !iaInfo.activa ? "La IA está apagada en los ajustes." : "Una IA propone el gancho, qué resaltar y el acabado.";

    const tieneVideo = Boolean(t.fuente_nombre);
    zonaSoltar.hidden = tieneVideo;
    miniatura.hidden = !tieneVideo || !t.miniatura;
    cambiar.hidden = !tieneVideo;
    if (tieneVideo && t.miniatura && !miniatura.src.includes(`v=${Math.round(t.actualizado)}`) && local.fraccionSubida === null) miniatura.src = `/api/trabajos/${id}/miniatura?v=${Math.round(t.actualizado)}`;
    poner(nombreArchivo, tieneVideo ? `${t.fuente_nombre} · ${formatoTiempo(t.fuente_duracion || 0)}` : "");

    if (document.activeElement !== pedido && pedido.value !== (t.prompt || "") && Date.now() - local.interpretadoEn > 1500) pedido.value = t.prompt || "";
    sincronizarOpciones(t.opciones || {});
    if (Date.now() - local.interpretadoEn > 2000) pintarEntendido(t.entendido, t.pendiente, t.sugerencias);

    botonCrear.disabled = !tieneVideo || local.fraccionSubida !== null;
    botonCrear.title = tieneVideo ? "" : "Sube primero el video que quieres editar";
    estadoTexto.className = `estado-texto ${t.estado === "error" ? "error" : ""}`;
    const texto = t.estado === "error" ? t.error : t.estado === "cancelado" ? "Lo cancelaste. Puedes volver a crearlo cuando quieras." : t.estado === "interrumpido" ? t.mensaje
      : tieneVideo ? "Listo para crear." : "Sube un video para empezar.";
    poner(estadoTexto, t.estado === "error" ? icono("aviso") : tieneVideo ? icono("ok-circulo") : icono("info"), texto || "");
    botonCrear.lastChild.textContent = t.estado === "error" || t.estado === "cancelado" || t.estado === "interrumpido" ? "Intentar de nuevo" : t.estado === "listo" ? "Crear otra vez" : "Crear este video";
  }

  return { nodo, actualizar, enfocar: () => titulo.focus(), local };
}
