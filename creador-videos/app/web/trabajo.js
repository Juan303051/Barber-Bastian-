// Tarjeta de un video: escenas, instrucciones, formato, extras, construcción en vivo y resultado. Se crea una vez y se va actualizando,
// así lo que la persona está escribiendo nunca se pierde cuando llegan novedades del servidor.
import { api, ErrorApi, subir } from "./api.js";
import { anunciar, aviso, dialogo } from "./ui.js";
import { aproximado, debounce, el, esVideo, establecerProgreso, formatoTiempo, icono, poner } from "./util.js";

const IDIOMAS = [["", "Automático"], ["es", "Español"], ["en", "English"], ["pt", "Português"]];
const ACABADOS = [["auto", "Que decida Iris"], ["natural", "Natural"], ["calido", "Cálido"], ["frio", "Frío"], ["cine", "Cine"], ["vibrante", "Vibrante"]];
const FORMATOS_BASE = [{ id: "auto", nombre: "Automático", ayuda: "Iris elige según lo que pidas y lo que digas." }];

// Lo que Iris puede añadir: [clave, icono, nombre, ayuda]. Un interruptor que la persona no toca sigue lo que pidió en su texto.
const EXTRAS = [
  ["calculadora", "calculadora", "Calculadora de dinero", "Suma, resta y confirma cada cifra que dices."],
  ["transiciones", "transicion", "Transiciones", "Un efecto en cada corte entre escenas."],
  ["sonidos", "sonido", "Efectos de sonido", "Whoosh, teclas y caja, siempre bajo tu voz."],
  ["logo", "logo", "Logo animado", "El logo de la marca entra con brillo al final."],
  ["quitar_pausas", "tijeras", "Quitar pausas largas", "Corta los silencios para que no se sienta lento."],
  ["musica", "musica", "Música de fondo", "Elige una canción de tu biblioteca bajo tu voz."],
];
const AJUSTES = [
  ["acercamientos", "Acercamientos", "Un zoom suave en una de cada dos frases para dar ritmo."],
  ["insignias", "Pasos numerados", "Si dices «primero, segundo…», pone el 1, 2, 3 en pantalla."],
  ["contadores", "Contadores de cifras", "Una cifra suelta sube contando (si hay calculadora, no se usan)."],
  ["cierre", "Cierre con palabra clave", "Si dices «comenta EDITOR», lo destaca al final."],
  ["color_referencias", "Usar el color de mis referencias", "Toma el color dominante de los videos de referencia."],
  ["ia", "Director con IA", "Una IA propone el gancho, qué resaltar y el acabado."],
  ["borrador", "Borrador rápido", "A la mitad de tamaño: se construye mucho más deprisa para probar."],
];
// Atajos: frases completas. Lo que hay entre `[` y `]` queda seleccionado para escribir encima.
const ATAJOS = [
  ["Calculadora de dinero", "Muestra una calculadora que sume y reste cada cifra que diga."],
  ["Transiciones", "Agrega transiciones con efecto entre escenas."],
  ["Efectos de sonido", "Agrega efectos de sonido sutiles."],
  ["Logo animado", "Cierra con el logo animado."],
  ["Palabras en grande", "Resalta las palabras: [precio, descuento]."],
  ["Quitar pausas", "Quita las pausas largas."],
  ["Cierre con «Comenta…»", "Cierra pidiendo que comenten la palabra: [EDITOR]."],
  ["Antes y después", "Hazlo en formato antes y después."],
];
const ESTADOS_ACTIVOS = new Set(["en_cola", "trabajando"]);
const ORIGEN_TEXTO = { texto: "Lo pediste en tu texto", formato: "Viene con este formato", manual: "" };

export function crearTrabajo(id, contexto) {
  const local = { editando: false, subidas: new Map(), contador: 0, ultimoFotograma: -1, firmaPasos: "", interpretadoEn: 0, anunciado: "", viendoVivo: false,
                  opciones: { _v: 2 }, escenas: [], firmaEscenas: "", efectivo: null, datos: null, firmaExtras: "" };

  // ───────────────────────────────────────────────────────── cabecera
  const numero = el("span", { clase: "trabajo-numero" });
  const titulo = el("input", { clase: "trabajo-titulo", maxlength: "80", "aria-label": "Nombre del video", spellcheck: "false" });
  const marca = el("select", { id: `marca-${id}`, "aria-label": "Marca de este video" });
  const cajaMarca = el("div", { clase: "entrada trabajo-marca" }, marca, icono("abajo"));
  const borrar = el("button", { type: "button", clase: "boton suave cuadrado peligro", "aria-label": "Quitar este video", title: "Quitar este video" }, icono("papelera"));
  const cabecera = el("div", { clase: "trabajo-cabecera" }, numero, titulo, cajaMarca, borrar);

  // ───────────────────────────────────────────────────────── 1 · escenas
  const entradaArchivo = el("input", { type: "file", accept: "video/*,.mp4,.mov,.m4v,.webm,.mkv", multiple: true, hidden: true, "aria-label": "Elegir las escenas del video" });
  const listaEscenas = el("ol", { clase: "escenas", "aria-label": "Escenas del video, en orden" });
  const zonaSoltar = el("div", { clase: "soltar escenas-soltar", role: "button", tabindex: "0", "aria-label": "Añadir escenas: haz clic o suelta tus videos aquí" },
    icono("subir"), el("strong", { texto: "Suelta tus escenas aquí" }), el("span", { clase: "fino", texto: "o haz clic para elegirlas · puedes elegir varias · MP4, MOV, WEBM" }));
  const totalEscenas = el("p", { clase: "ayuda escenas-total" });
  const cajaEscenas = el("div", { clase: "escenas-caja" },
    el("h3", { clase: "bloque-titulo" }, el("span", { clase: "bloque-icono" }, icono("pelicula")), "Tus escenas"),
    el("p", { clase: "bloque-sub", texto: "Sube las tomas tal como las grabaste. Iris las une en este orden." }),
    listaEscenas, zonaSoltar, totalEscenas, entradaArchivo);

  // ───────────────────────────────────────────────────────── 2 · instrucciones y formato
  const pedido = el("textarea", { id: `pedido-${id}`, maxlength: "4000", rows: "5", placeholder: "Ejemplo: Contador de dinero: muestra una calculadora con cada precio y descuento que diga. Agrega transiciones entre escenas, efectos de sonido y el logo animado al final." });
  const atajos = el("div", { clase: "sugerencias", role: "group", "aria-label": "Atajos para escribir lo que quieres" },
    ATAJOS.map(([texto, frase]) => el("button", { type: "button", datos: { frase } }, icono("mas", "pequeno-icono"), texto)));
  const nombreFormato = `formato-${id}`;
  const grupoFormato = el("div", { clase: "formatos", role: "radiogroup", "aria-label": "Formato del video" });
  const ayudaFormato = el("p", { clase: "ayuda formato-ayuda", "aria-live": "polite" });
  const entendido = el("div", { clase: "entendido", "aria-live": "off" });
  const cajaPedido = el("div", { clase: "pedido-caja" },
    el("h3", { clase: "bloque-titulo" }, el("span", { clase: "bloque-icono" }, icono("texto")), "Cuéntale a Iris cómo lo quieres"),
    el("div", { clase: "campo" }, el("label", { for: pedido.id, clase: "solo-lector", texto: "Instrucciones para este video" }), el("div", { clase: "entrada" }, pedido)),
    atajos,
    el("div", { clase: "formato-bloque" }, el("span", { clase: "rotulo-pequeno", id: `rot-formato-${id}`, texto: "Formato" }), grupoFormato, ayudaFormato),
    entendido);

  // ───────────────────────────────────────────────────────── 3 · extras
  const extras = new Map();
  const tarjetasExtras = EXTRAS.map(([clave, nombreIcono, nombre, ayuda]) => {
    const entrada = el("input", { type: "checkbox", id: `extra-${clave}-${id}` });
    const origen = el("span", { clase: "extra-origen" });
    const extra = el("span", { clase: "extra-extra" });
    const nodo = el("div", { clase: "extra", datos: { clave } },
      el("span", { clase: "extra-icono" }, icono(nombreIcono)),
      el("label", { clase: "extra-texto", for: entrada.id }, el("strong", { texto: nombre }), el("span", { texto: ayuda }), origen),
      el("span", { clase: "interruptor" }, entrada, el("span")), extra);
    extras.set(clave, { entrada, origen, nodo, extra });
    return nodo;
  });
  const botonLogo = el("button", { type: "button", clase: "boton pequeno" }, icono("subir"), "Subir logo");
  extras.get("logo").extra.append(botonLogo);
  const menores = el("input", { type: "checkbox", id: `menores-${id}` });
  const cajaMenores = el("div", { clase: "extra extra-aviso", hidden: true },
    el("span", { clase: "extra-icono" }, icono("escudo")),
    el("label", { clase: "extra-texto", for: menores.id }, el("strong", { texto: "Autorización de los padres" }),
      el("span", { texto: "Esta marca habla a niños o de niños: confirmo que tengo la autorización por escrito de los padres o tutores de los menores que aparezcan." })),
    el("span", { clase: "interruptor" }, menores, el("span")));
  const cajaExtras = el("div", { clase: "extras-caja" },
    el("h3", { clase: "bloque-titulo" }, el("span", { clase: "bloque-icono" }, icono("varita")), "Efectos y piezas"),
    el("p", { clase: "bloque-sub", texto: "Lo que pides en tu texto se enciende solo. Aquí lo corriges con un toque." }),
    el("div", { clase: "extras" }, tarjetasExtras, cajaMenores));

  // ───────────────────────────────────────────────────────── más opciones
  const ajustes = new Map();
  const filasAjustes = AJUSTES.map(([clave, nombre, ayuda]) => {
    const entrada = el("input", { type: "checkbox", id: `opc-${clave}-${id}` });
    ajustes.set(clave, entrada);
    const textoAyuda = el("span", { texto: ayuda });
    if (clave === "ia") ajustes.set("ia-ayuda", textoAyuda);
    return el("div", { clase: "opcion" }, el("label", { clase: "texto", for: entrada.id }, el("strong", { texto: nombre }), textoAyuda), el("span", { clase: "interruptor" }, entrada, el("span")));
  });
  const acabado = el("select", { id: `acabado-${id}` }, ACABADOS.map(([valor, texto]) => el("option", { value: valor, texto })));
  const idioma = el("select", { id: `idioma-${id}` }, IDIOMAS.map(([valor, texto]) => el("option", { value: valor, texto })));
  const botonTest = el("button", { type: "button", clase: "boton pequeno" }, icono("director"), "Hacer o cambiar el test");
  const avanzado = el("details", { clase: "avanzado" },
    el("summary", {}, icono("abajo"), "Más opciones"),
    el("div", { clase: "opciones" }, filasAjustes,
      el("div", { clase: "opcion" }, el("label", { clase: "texto", for: acabado.id }, el("strong", { texto: "Acabado de color" }), el("span", { texto: "Un ajuste suave de color y contraste sobre tu toma." })), el("div", { clase: "entrada" }, acabado, icono("abajo"))),
      el("div", { clase: "opcion" }, el("label", { clase: "texto", for: idioma.id }, el("strong", { texto: "Idioma del video" }), el("span", { texto: "Si lo dejas en automático, Iris lo detecta." })), el("div", { clase: "entrada" }, idioma, icono("abajo"))),
      el("div", { clase: "opcion" }, el("div", { clase: "texto" }, el("strong", { texto: "Test del director" }), el("span", { texto: "Tono, ritmo, música y lo que nunca debe aparecer en esta marca." })), botonTest)));

  const cuerpoFormulario = el("div", { clase: "trabajo-cuerpo" }, cajaEscenas, cajaPedido);
  const cuerpoExtras = el("div", { clase: "trabajo-extras" }, cajaExtras, avanzado);

  // ───────────────────────────────────────────────────────── pie del formulario
  const estadoTexto = el("div", { clase: "estado-texto" });
  const botonCrear = el("button", { type: "button", clase: "boton principal" }, icono("varita"), "Crear este video");
  const pie = el("div", { clase: "trabajo-pie" }, estadoTexto, botonCrear);
  const formulario = el("div", {}, cuerpoFormulario, cuerpoExtras, pie);

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
  const notasListo = el("details", { clase: "avanzado notas-detalle" });
  const cumplimientoCaja = el("div", { clase: "cumplimiento" });
  const calidadCaja = el("div", { clase: "calidad" });
  const direccionCaja = el("div", { clase: "direccion" });
  const descargar = el("a", { clase: "boton principal", href: `/api/trabajos/${id}/resultado?descargar=1` }, icono("descargar"), "Descargar");
  const editarOtra = el("button", { type: "button", clase: "boton" }, icono("varita"), "Cambiar y volver a crear");
  const resultado = el("div", { clase: "resultado", hidden: true }, marcoResultado,
    el("div", { clase: "vivo-lado" }, tituloListo, el("div", { clase: "resultado-acciones" }, descargar, editarOtra), cumplimientoCaja, calidadCaja, direccionCaja, notasListo));

  const nodo = el("article", { clase: "trabajo", "aria-labelledby": `titulo-${id}` },
    el("h3", { id: `titulo-${id}`, clase: "solo-lector" }), cabecera, formulario, vivo, resultado);
  const rotuloOculto = nodo.querySelector("h3");

  // ───────────────────────────────────────────────────────── guardar y entender
  const guardarPedido = debounce(() => api.trabajoCambiar(id, { prompt: pedido.value }).catch(() => {}), 700);
  const interpretar = debounce(async () => {
    try {
      const r = await api.interpretar(pedido.value, local.opciones, marca.value);
      local.interpretadoEn = Date.now();
      local.efectivo = r.efectivo;
      pintarEntendido(r.entendido, r.pendiente);
      pintarEfectivo();
    } catch { /* se queda lo anterior */ }
  }, 400);
  const guardarOpciones = () => api.trabajoCambiar(id, { opciones: local.opciones }).then(() => interpretar.ahora()).catch((e) => aviso(e.message, { tipo: "error" }));
  const tocar = (clave, valor) => {
    local.interpretadoEn = Date.now(); // mientras se guarda, las novedades del servidor no pisan lo que la persona acaba de tocar
    local.opciones = { ...local.opciones, _v: 2, [clave]: valor };
    if (valor === null) delete local.opciones[clave];
    return guardarOpciones();
  };

  pedido.addEventListener("input", () => { guardarPedido(); interpretar(); });
  pedido.addEventListener("blur", () => guardarPedido.ahora());
  atajos.addEventListener("click", (e) => {
    const boton = e.target.closest("button");
    if (!boton) return;
    const frase = boton.dataset.frase;
    const limpia = frase.replace(/[[\]]/g, "");
    const inicioMarca = frase.indexOf("["), finMarca = frase.indexOf("]") - 1;
    if (!pedido.value.includes(limpia)) {
      const separador = pedido.value && !/\n$/.test(pedido.value) ? (/\s$/.test(pedido.value) ? "" : " ") : "";
      const base = pedido.value + separador;
      pedido.value = base + limpia;
      pedido.focus();
      if (inicioMarca >= 0) pedido.setSelectionRange(base.length + inicioMarca, base.length + finMarca); else pedido.setSelectionRange(pedido.value.length, pedido.value.length);
      pedido.dispatchEvent(new Event("input"));
    } else {
      pedido.focus();
      const desde = pedido.value.indexOf(limpia);
      pedido.setSelectionRange(desde + (inicioMarca >= 0 ? inicioMarca : 0), desde + (inicioMarca >= 0 ? finMarca : limpia.length));
      aviso("Ese atajo ya está en tu texto.");
    }
  });
  for (const [clave, { entrada }] of extras) entrada.addEventListener("change", () => tocar(clave, entrada.checked));
  for (const [clave, entrada] of ajustes) {
    if (clave === "ia-ayuda") continue;
    entrada.addEventListener("change", () => (clave === "borrador" ? tocar("calidad", entrada.checked ? "borrador" : "completa") : tocar(clave, entrada.checked)));
  }
  menores.addEventListener("change", () => tocar("permiso_menores", menores.checked));
  idioma.addEventListener("change", () => tocar("idioma", idioma.value || null));
  acabado.addEventListener("change", () => tocar("acabado", acabado.value || "auto"));
  botonTest.addEventListener("click", () => contexto.perfil(marca.value));
  botonLogo.addEventListener("click", () => contexto.logo(marca.value));

  titulo.addEventListener("change", () => api.trabajoCambiar(id, { titulo: titulo.value }).catch(() => {}));
  titulo.addEventListener("keydown", (e) => { if (e.key === "Enter") titulo.blur(); });
  marca.addEventListener("change", () => api.trabajoCambiar(id, { marca: marca.value || null }).then(() => contexto.refrescar()).catch((e) => aviso(e.message, { tipo: "error" })));
  borrar.addEventListener("click", () => contexto.quitar(id));
  editarOtra.addEventListener("click", () => { local.editando = true; contexto.refrescar(); });

  // ───────────────────────────────────────────────────────── escenas: subir, ordenar, quitar
  const elegir = () => entradaArchivo.click();
  zonaSoltar.addEventListener("click", elegir);
  zonaSoltar.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(); } });
  entradaArchivo.addEventListener("change", () => { const archivos = [...entradaArchivo.files]; entradaArchivo.value = ""; subirEscenas(archivos); });
  const sobre = (e) => {
    e.preventDefault();
    const items = [...(e.dataTransfer?.items || [])];
    const valido = !items.length || items.some((i) => i.kind === "file" && (i.type === "" || i.type.startsWith("video/")));
    cajaEscenas.classList.toggle("sobre", valido);
    cajaEscenas.classList.toggle("invalido", !valido);
    if (e.dataTransfer) e.dataTransfer.dropEffect = valido ? "copy" : "none";
  };
  cajaEscenas.addEventListener("dragenter", sobre);
  cajaEscenas.addEventListener("dragover", sobre);
  cajaEscenas.addEventListener("dragleave", (e) => { if (!cajaEscenas.contains(e.relatedTarget)) cajaEscenas.classList.remove("sobre", "invalido"); });
  cajaEscenas.addEventListener("drop", (e) => { e.preventDefault(); cajaEscenas.classList.remove("sobre", "invalido"); subirEscenas([...e.dataTransfer.files]); });

  async function subirEscenas(archivos) {
    const validos = archivos.filter(esVideo);
    if (archivos.length > validos.length) aviso(`${archivos.length - validos.length} archivo(s) no son videos compatibles (usa MP4, MOV, M4V, WEBM o MKV) y se omitieron.`, { tipo: "error" });
    validos.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    for (const archivo of validos) {
      const clave = `local-${++local.contador}`;
      local.subidas.set(clave, { nombre: archivo.name, fraccion: 0, error: null });
      pintarEscenas();
      try {
        await subir(`/api/trabajos/${id}/escenas`, archivo, (f) => { local.subidas.get(clave).fraccion = f; pintarEscenas(); });
        local.subidas.delete(clave);
      } catch (error) {
        local.subidas.get(clave).error = `${archivo.name}: ${error.message}`;
        aviso(`${archivo.name}: ${error.message}`, { tipo: "error" });
        setTimeout(() => { local.subidas.delete(clave); pintarEscenas(); }, 6000);
      }
      await contexto.refrescar();
    }
    if (validos.length) anunciar(`${validos.length} escena(s) subida(s).`);
  }

  async function moverEscena(indice, delta) {
    const nueva = [...local.escenas];
    const destino = indice + delta;
    if (destino < 0 || destino >= nueva.length) return;
    [nueva[indice], nueva[destino]] = [nueva[destino], nueva[indice]];
    local.escenas = nueva;
    pintarEscenas();
    anunciar(`Escena movida a la posición ${destino + 1}.`);
    try { await api.escenasOrdenar(id, nueva.map((e) => e.id)); } catch (error) { aviso(error.message, { tipo: "error" }); }
    contexto.refrescar();
  }

  async function quitarEscena(escena, indice) {
    try { await api.escenaBorrar(id, escena.id); anunciar(`Escena ${indice + 1} quitada.`); } catch (error) { aviso(error.message, { tipo: "error" }); }
    contexto.refrescar();
  }

  function pintarEscenas() {
    const subiendo = [...local.subidas];
    const firma = JSON.stringify([local.escenas.map((e) => [e.id, e.nombre, e.duracion]), subiendo.map(([k, s]) => [k, Math.round(s.fraccion * 50), s.error])]);
    if (firma !== local.firmaEscenas) {
      local.firmaEscenas = firma;
      const total = local.escenas.length;
      const filas = local.escenas.map((e, i) => el("li", { clase: "escena" },
        el("img", { src: `/api/trabajos/${id}/escenas/${e.id}/miniatura`, alt: `Vista previa de la escena ${i + 1}`, loading: "lazy" }),
        el("div", { clase: "escena-datos" }, el("strong", { texto: `Escena ${i + 1}` }), el("span", { clase: "escena-nombre", texto: e.nombre }), el("span", { clase: "ayuda", texto: formatoTiempo(e.duracion) })),
        el("div", { clase: "escena-acciones" },
          el("button", { type: "button", clase: "boton suave cuadrado pequeno", "aria-label": `Subir la escena ${i + 1}`, title: "Subir", disabled: i === 0, enClick: () => moverEscena(i, -1) }, icono("arriba")),
          el("button", { type: "button", clase: "boton suave cuadrado pequeno", "aria-label": `Bajar la escena ${i + 1}`, title: "Bajar", disabled: i === total - 1, enClick: () => moverEscena(i, 1) }, icono("abajo")),
          el("button", { type: "button", clase: "boton suave cuadrado pequeno peligro", "aria-label": `Quitar la escena ${i + 1}`, title: "Quitar", enClick: () => quitarEscena(e, i) }, icono("papelera")))));
      const pendientes = subiendo.map(([, s]) => {
        const pista = el("div", { clase: "progreso-pista" }, el("i"));
        establecerProgreso(pista, s.fraccion);
        return el("li", { clase: `escena subiendo ${s.error ? "con-error" : ""}` },
          el("div", { clase: "escena-miniatura vacia" }, icono("pelicula")),
          el("div", { clase: "escena-datos" }, el("strong", { texto: s.error ? "No se pudo subir" : "Subiendo…" }), el("span", { clase: "escena-nombre", texto: s.error || s.nombre }),
            s.error ? null : el("div", { clase: "progreso" }, pista, el("div", { clase: "progreso-texto" }, el("span", { texto: s.fraccion >= 0.999 ? "Comprobando…" : `${Math.round(s.fraccion * 100)} %` })))));
      });
      poner(listaEscenas, filas, pendientes);
    }
    const segundos = local.escenas.reduce((suma, e) => suma + e.duracion, 0);
    totalEscenas.textContent = local.escenas.length ? `${local.escenas.length} escena${local.escenas.length === 1 ? "" : "s"} · ${formatoTiempo(segundos)} en total` : "";
    listaEscenas.hidden = !local.escenas.length && !local.subidas.size;
    zonaSoltar.classList.toggle("compacta", local.escenas.length > 0 || local.subidas.size > 0);
    zonaSoltar.querySelector("strong").textContent = local.escenas.length ? "Añadir más escenas" : "Suelta tus escenas aquí";
  }

  botonCrear.addEventListener("click", () => contexto.crear(id));
  cancelar.addEventListener("click", async () => {
    const decision = await dialogo({
      titulo: "¿Cancelar este video?", texto: "Se pierde lo que Iris lleva construido de este video. Tus escenas y tus instrucciones se quedan guardadas.",
      acciones: [{ texto: "Cancelar video", valor: "si", clase: "peligro-lleno" }, { texto: "Seguir creando", valor: "no", clase: "principal" }],
    });
    if (decision === "si") { await api.cancelar(id).catch((e) => aviso(e.message, { tipo: "error" })); contexto.refrescar(); }
  });

  // ───────────────────────────────────────────────────────── «Esto haré», formato y extras
  const iconoDe = { texto: "texto", estrella: "estrella", mensaje: "mensaje", tijeras: "tijeras", color: "color", musica: "musica", calculadora: "calculadora", transicion: "transicion", sonido: "sonido", logo: "logo" };
  function pintarEntendido(lista, pendientes) {
    const iaActiva = Boolean(contexto.ia?.().activa) && local.opciones.ia !== false;
    poner(entendido, el("h4", { texto: "Esto haré" }),
      el("ul", {}, lista.map((f) => el("li", {}, icono(iconoDe[f.icono] || "info"), f.texto)), (pendientes || []).map((t) => el("li", { clase: "pendiente" }, icono("aviso"), t))),
      iaActiva ? el("p", { clase: "ayuda", texto: "Con la IA activa, el director ajusta los detalles al construir. Al final verás qué se hizo con cada cosa que pediste." }) : null);
  }

  function pintarFormatos() {
    const lista = contexto.formatos?.().length ? contexto.formatos() : FORMATOS_BASE;
    const firma = lista.map((f) => f.id).join(",");
    if (firma !== local.firmaFormatos) {
      local.firmaFormatos = firma;
      poner(grupoFormato, lista.map((f) => el("label", { clase: "formato", title: f.ayuda },
        el("input", { type: "radio", name: nombreFormato, value: f.id, enChange: () => tocar("formato", f.id) }), el("span", { texto: f.nombre }))));
    }
    const elegido = local.opciones.formato || "auto";
    for (const r of grupoFormato.querySelectorAll("input")) r.checked = r.value === elegido;
    const actual = lista.find((f) => f.id === elegido) || lista[0];
    const ef = local.efectivo;
    const deducido = elegido === "auto" && ef && ef.formato_origen === "texto" ? lista.find((f) => f.id === ef.formato) : null;
    ayudaFormato.textContent = deducido ? `Automático: según tu texto, Iris eligió «${deducido.nombre}». ${deducido.ayuda}` : actual?.ayuda || "";
  }

  function pintarEfectivo() {
    const ef = local.efectivo;
    if (!ef) return;
    const tieneLogo = Boolean(local.datos?.tiene_logo);
    for (const [clave, { entrada, origen, nodo: tarjeta }] of extras) {
      const valor = ef.valores[clave];
      if (document.activeElement !== entrada) entrada.checked = valor === true;
      const textoOrigen = valor === null ? "Lo decide el director" : (ORIGEN_TEXTO[ef.origenes[clave]] ?? "");
      if (origen.textContent !== textoOrigen) origen.textContent = textoOrigen;
      origen.classList.toggle("destacado", ef.origenes[clave] === "texto" || ef.origenes[clave] === "formato");
      tarjeta.classList.toggle("encendida", valor === true);
    }
    for (const [clave, entrada] of ajustes) {
      if (clave === "ia-ayuda" || document.activeElement === entrada) continue;
      entrada.checked = clave === "borrador" ? local.opciones.calidad === "borrador" : ef.valores[clave] !== false && ef.valores[clave] !== null;
    }
    botonLogo.hidden = false;
    poner(botonLogo, icono("subir"), tieneLogo ? "Cambiar logo" : "Subir logo");
    extras.get("logo").nodo.classList.toggle("falta", ef.valores.logo === true && !tieneLogo);
    pintarFormatos();
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
    const [iconoNombre, tituloCalidad, tono] = ETIQUETA_CALIDAD[c.veredicto] || ETIQUETA_CALIDAD.revisar;
    const orden = { error: 0, aviso: 1, ok: 2 };
    const pruebas = [...c.pruebas].sort((a, b) => orden[a.nivel] - orden[b.nivel]);
    const problemas = pruebas.filter((p) => p.nivel !== "ok");
    const correctas = pruebas.filter((p) => p.nivel === "ok");
    const fila = (p) => el("li", { clase: `prueba ${p.nivel}` }, icono(ICONO_NIVEL[p.nivel]), el("span", { texto: p.texto }));
    const pideMenores = c.pruebas.some((p) => p.id === "menores" && p.nivel !== "ok");
    const confirmar = pideMenores ? el("button", { type: "button", clase: "boton pequeno", enClick: async () => { await api.permisoMenores(id, true).catch((e) => aviso(e.message, { tipo: "error" })); contexto.refrescar(); } },
      icono("escudo"), "Confirmo que tengo la autorización de los padres") : null;
    poner(calidadCaja,
      el("h4", { clase: `calidad-titulo ${tono}` }, icono(iconoNombre), tituloCalidad),
      el("p", { clase: "ayuda", texto: c.resumen }),
      problemas.length ? el("ul", { clase: "pruebas" }, problemas.map(fila)) : null, confirmar,
      correctas.length ? el("details", { clase: "avanzado pruebas-ok" }, el("summary", {}, icono("abajo"), `${correctas.length} prueba(s) en orden`), el("ul", { clase: "pruebas" }, correctas.map(fila))) : null);
  }

  const ICONO_CUMPLIMIENTO = { hecho: "ok-circulo", parcial: "aviso", no: "x", omitido: "pausa" };
  const TEXTO_CUMPLIMIENTO = { hecho: "Hecho", parcial: "A medias", no: "No se pudo", omitido: "Apagado por ti" };
  function pintarCumplimiento(filas) {
    if (!filas?.length) { poner(cumplimientoCaja); return; }
    poner(cumplimientoCaja,
      el("h4", {}, icono("ok"), "Lo que pediste"),
      el("ul", { clase: "pruebas" }, filas.map((f) => el("li", { clase: `prueba cumple-${f.estado}` }, icono(ICONO_CUMPLIMIENTO[f.estado] || "info"),
        el("span", {}, el("strong", { texto: f.pedido }), " · ", el("span", { clase: `estado-cumple ${f.estado}`, texto: TEXTO_CUMPLIMIENTO[f.estado] || f.estado }), f.detalle ? el("span", { clase: "ayuda detalle-cumple", texto: f.detalle }) : null)))));
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
      d.alternativas?.length ? el("p", { clase: "ayuda", texto: `Otras ideas de gancho: ${d.alternativas.map((a) => `«${a}»`).join(" · ")}` }) : null);
  }

  function pintarResultado(t) {
    const fuenteVideo = `/api/trabajos/${id}/resultado?v=${Math.round(t.actualizado)}`;
    if (video.dataset.fuente !== fuenteVideo) {
      video.dataset.fuente = fuenteVideo;
      video.src = fuenteVideo;
      video.poster = `/api/trabajos/${id}/miniatura?v=${Math.round(t.actualizado)}`;
    }
    marcoResultado.classList.toggle("horizontal", !t.vertical);
    pintarCumplimiento(t.cumplimiento);
    pintarCalidad(t.calidad);
    pintarDireccion(t);
    poner(notasListo, el("summary", {}, icono("abajo"), `Qué hizo Iris, paso a paso${t.mensaje ? ` · ${t.mensaje}` : ""}`),
      el("ul", { clase: "notas" }, (t.notas || []).map((n) => el("li", { texto: n }))));
    notasListo.hidden = !(t.notas || []).length;
  }

  // ───────────────────────────────────────────────────────── actualizar con lo que dice el servidor
  function actualizar(t, indice, marcas) {
    local.datos = t;
    numero.textContent = String(indice + 1);
    rotuloOculto.textContent = `Video ${indice + 1}: ${t.titulo}`;
    if (document.activeElement !== titulo && titulo.value !== t.titulo) titulo.value = t.titulo;
    const firmaMarcas = marcas.map((m) => `${m.id}:${m.logo ? 1 : 0}`).join(",");
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
    const interruptorIA = ajustes.get("ia");
    interruptorIA.disabled = !iaInfo.disponible || !iaInfo.activa;
    const costo = iaInfo.costo_estimado_usd ? ` · ≈ US$ ${iaInfo.costo_estimado_usd.toFixed(2).replace(".", ",")} por video (lo cobra Anthropic)` : "";
    ajustes.get("ia-ayuda").textContent = !iaInfo.disponible ? "Sin clave de IA: se usan reglas. Configúrala en el menú de tu cuenta."
      : !iaInfo.consentida ? "Falta confirmar qué datos se envían: abre «Director con IA» en el menú de tu cuenta."
      : !iaInfo.activa ? "La IA está apagada en los ajustes." : `Una IA propone el gancho, qué resaltar y el acabado${costo}.`;

    local.escenas = t.escenas || [];
    pintarEscenas();

    if (document.activeElement !== pedido && pedido.value !== (t.prompt || "") && Date.now() - local.interpretadoEn > 1500) pedido.value = t.prompt || "";
    if (!formulario.contains(document.activeElement) || document.activeElement === pedido) {
      if (Date.now() - local.interpretadoEn > 1500 || !local.efectivo) local.opciones = { ...(t.opciones || {}), _v: 2 };
    }
    if (document.activeElement !== idioma) idioma.value = local.opciones.idioma || "";
    if (document.activeElement !== acabado) acabado.value = local.opciones.acabado || "auto";
    cajaMenores.hidden = !t.menores_marca;
    if (document.activeElement !== menores) menores.checked = Boolean(local.opciones.permiso_menores);
    if (Date.now() - local.interpretadoEn > 2000 || !local.efectivo) {
      local.efectivo = t.efectivo;
      pintarEntendido(t.entendido, t.pendiente);
    }
    pintarEfectivo();

    const tieneEscenas = local.escenas.length > 0;
    const subiendo = local.subidas.size > 0 && [...local.subidas.values()].some((s) => !s.error);
    botonCrear.disabled = !tieneEscenas || subiendo;
    botonCrear.title = tieneEscenas ? "" : "Sube primero al menos una escena";
    estadoTexto.className = `estado-texto ${t.estado === "error" ? "error" : ""}`;
    const costoIA = iaInfo.activa && local.opciones.ia !== false && iaInfo.costo_estimado_usd ? ` Con IA: ≈ US$ ${iaInfo.costo_estimado_usd.toFixed(2).replace(".", ",")} (lo cobra Anthropic).` : "";
    const texto = t.estado === "error" ? t.error : t.estado === "cancelado" ? "Lo cancelaste. Puedes volver a crearlo cuando quieras." : t.estado === "interrumpido" ? t.mensaje
      : tieneEscenas ? `Listo para crear.${costoIA}` : "Sube al menos una escena para empezar.";
    poner(estadoTexto, t.estado === "error" ? icono("aviso") : tieneEscenas ? icono("ok-circulo") : icono("info"), texto || "");
    botonCrear.lastChild.textContent = t.estado === "error" || t.estado === "cancelado" || t.estado === "interrumpido" ? "Intentar de nuevo" : t.estado === "listo" ? "Crear otra vez" : "Crear este video";
  }

  return { nodo, actualizar, enfocar: () => titulo.focus(), local };
}
