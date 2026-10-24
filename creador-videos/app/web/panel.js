// Panel de una sola pantalla: referencias, videos a crear y construcción en vivo.
import { api, ErrorApi, subir } from "./api.js";
import { crearTrabajo } from "./trabajo.js";
import { anunciar, aviso, campoSimple, dialogo } from "./ui.js";
import { el, esVideo, establecerProgreso, icono, iniciales, logo, poner } from "./util.js";

const ACTIVOS = new Set(["en_cola", "trabajando"]);
const CREABLES = new Set(["borrador", "error", "cancelado", "interrumpido"]);

export function montarPanel(raiz, usuario, { alSalir }) {
  const estado = { marcas: [], referencias: [], trabajos: [] };
  const tarjetasTrabajo = new Map();
  const tarjetasReferencia = new Map();
  const subiendo = new Map(); // subidas de referencias en curso (todavía sin registro en el servidor)
  const ocultos = new Set(); // lo que se acaba de quitar y todavía se puede deshacer
  const estadoAnterior = new Map();
  let detenido = false;
  let temporizador = null;
  let contadorLocal = 0;

  // ───────────────────────────────────────────────────────────── barra superior
  const textoCrear = el("span", { clase: "texto-largo" });
  const botonCrear = el("button", { type: "button", clase: "boton principal", "aria-label": "Crear videos" }, icono("varita"), textoCrear);
  const avatar = el("button", { type: "button", clase: "avatar", "aria-haspopup": "menu", "aria-expanded": "false", "aria-label": `Cuenta de ${usuario.nombre}`, texto: iniciales(usuario.nombre) });
  const menu = el("div", { clase: "menu-usuario vidrio", role: "menu", hidden: true },
    el("div", { clase: "quien" }, el("strong", { texto: usuario.nombre }), el("span", { texto: usuario.correo })),
    el("button", { type: "button", role: "menuitem", datos: { accion: "anadir" } }, icono("persona"), "Añadir a una persona"),
    el("button", { type: "button", role: "menuitem", datos: { accion: "salir" } }, icono("salir"), "Salir"),
    el("button", { type: "button", role: "menuitem", clase: "rojo", datos: { accion: "eliminar" } }, icono("papelera"), "Eliminar mi cuenta…"));
  const barra = el("header", { clase: "barra vidrio" },
    el("div", { clase: "logo" }, logo(), "Iris"),
    el("div", { clase: "barra-derecha" }, botonCrear, el("div", { clase: "posicion-relativa" }, avatar, menu)));

  // ───────────────────────────────────────────────────────────── sección 1: referencias
  const entradaReferencias = el("input", { type: "file", accept: "video/*,.mp4,.mov,.m4v,.webm,.mkv", multiple: true, hidden: true, "aria-label": "Elegir videos de referencia" });
  const zonaReferencias = el("div", { clase: "soltar", role: "button", tabindex: "0", "aria-label": "Elegir o soltar videos de referencia" },
    icono("subir"), el("strong", { texto: "Suelta aquí los videos que te gustan" }),
    el("span", { clase: "fino", texto: "o haz clic para elegirlos · MP4, MOV, WEBM · se quedan en tu equipo" }));
  const campoEnlace = el("input", { type: "url", id: "enlace-referencia", placeholder: "O pega un enlace de Instagram, TikTok o YouTube", "aria-label": "Enlace de un video de referencia", autocomplete: "off", spellcheck: "false" });
  const botonEnlace = el("button", { type: "button", clase: "boton" }, icono("enlace"), "Añadir enlace");
  const errorEnlace = el("div", { clase: "mensaje-campo", role: "alert" });
  const rejilla = el("div", { clase: "referencias-rejilla" });
  const vacioReferencias = el("p", { clase: "ayuda", texto: "Todavía no hay referencias. Sin ellas, Iris usa un estilo estándar: subtítulos dinámicos y acercamientos suaves." });
  const seccionReferencias = el("section", { clase: "seccion", "aria-labelledby": "t-ref" },
    el("div", { clase: "seccion-cabecera" }, el("div", { clase: "seccion-titulo" }, el("span", { clase: "numero", texto: "1", "aria-hidden": "true" }),
      el("div", {}, el("h2", { id: "t-ref", clase: "titulo-2", texto: "Referencias" }), el("p", { clase: "seccion-sub", texto: "Videos que te gustan. Iris aprende su ritmo y lo aplica a los tuyos." })))),
    el("div", { clase: "tarjeta" }, zonaReferencias, entradaReferencias,
      el("div", { clase: "entrada-enlace" }, el("div", { clase: "entrada" }, campoEnlace), botonEnlace), errorEnlace, vacioReferencias, rejilla));

  // ───────────────────────────────────────────────────────────── sección 2: videos
  const listaTrabajos = el("div", { clase: "trabajos" });
  const botonAnadir = el("button", { type: "button", clase: "boton anadir" }, icono("mas"), "Añadir otro video");
  const seccionTrabajos = el("section", { clase: "seccion", "aria-labelledby": "t-vid" },
    el("div", { clase: "seccion-cabecera" }, el("div", { clase: "seccion-titulo" }, el("span", { clase: "numero", texto: "2", "aria-hidden": "true" }),
      el("div", {}, el("h2", { id: "t-vid", clase: "titulo-2", texto: "Tus videos" }), el("p", { clase: "seccion-sub", texto: "Añade todos los que necesites. Cada uno con sus propias instrucciones." })))),
    listaTrabajos, botonAnadir);

  const cabecera = el("div", { clase: "cabecera" },
    el("h1", { clase: "titulo-grande", texto: "Tus videos de marketing, listos sin editar." }),
    el("p", { texto: "Sube lo que grabaste, cuéntale a Iris cómo lo quieres y míralo construirse." }));
  const principal = el("main", { id: "contenido", clase: "pagina" }, cabecera, seccionReferencias, seccionTrabajos);
  poner(raiz, barra, principal);

  // ───────────────────────────────────────────────────────────── menú de cuenta
  const cerrarMenu = () => { menu.hidden = true; avatar.setAttribute("aria-expanded", "false"); };
  avatar.addEventListener("click", () => { menu.hidden = !menu.hidden; avatar.setAttribute("aria-expanded", String(!menu.hidden)); if (!menu.hidden) menu.querySelector("button").focus(); });
  document.addEventListener("click", (e) => { if (!menu.hidden && !menu.contains(e.target) && !avatar.contains(e.target)) cerrarMenu(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !menu.hidden) { cerrarMenu(); avatar.focus(); } });
  menu.addEventListener("click", async (e) => {
    const boton = e.target.closest("button");
    if (!boton) return;
    cerrarMenu();
    if (boton.dataset.accion === "salir") { await api.salir().catch(() => {}); alSalir(); }
    if (boton.dataset.accion === "anadir") anadirPersona();
    if (boton.dataset.accion === "eliminar") eliminarCuenta();
  });

  async function anadirPersona() {
    const nombre = campoSimple({ id: "nuevo-nombre", etiqueta: "Nombre", ejemplo: "Luis Gómez", autocompletar: "off" });
    const correo = campoSimple({ id: "nuevo-correo", etiqueta: "Correo", tipo: "email", ejemplo: "luis@empresa.com" });
    const clave = campoSimple({ id: "nueva-clave", etiqueta: "Contraseña inicial", tipo: "password", ejemplo: "Mínimo 8 caracteres", autocompletar: "new-password" });
    const resultado = await dialogo({
      titulo: "Añadir a una persona", texto: "Podrá entrar a Iris y ver las referencias y los videos de este equipo.",
      cuerpo: el("div", { clase: "formulario" }, nombre.nodo, correo.nodo, clave.nodo),
      acciones: [{ texto: "Ahora no", valor: false }, { texto: "Añadir persona", valor: "ok", clase: "principal" }],
      alValidar: async () => {
        try {
          await api.registro({ nombre: nombre.entrada.value.trim(), correo: correo.entrada.value.trim(), contrasena: clave.entrada.value });
          return null;
        } catch (error) { return Object.values(error.campos)[0] || error.message; }
      },
    });
    if (resultado === "ok") aviso(`Listo: ${nombre.entrada.value.trim()} ya puede entrar a Iris.`);
  }

  async function eliminarCuenta() {
    const clave = campoSimple({ id: "borrar-clave", etiqueta: "Escribe tu contraseña para confirmar", tipo: "password", autocompletar: "current-password" });
    const borrarTodo = el("input", { type: "checkbox", id: "borrar-todo" });
    const resultado = await dialogo({
      titulo: "Eliminar mi cuenta", texto: "Tu cuenta se borra por completo y no se puede recuperar. Los videos del equipo se quedan, a menos que marques la casilla.",
      cuerpo: el("div", { clase: "formulario" }, clave.nodo, el("div", { clase: "fila-recordar" }, el("label", { for: "borrar-todo", texto: "También borrar mis videos y referencias" }), el("span", { clase: "interruptor" }, borrarTodo, el("span")))),
      acciones: [{ texto: "Cancelar", valor: false }, { texto: "Eliminar cuenta", valor: "ok", clase: "peligro-lleno" }],
      alValidar: async () => {
        try { await api.eliminarCuenta({ contrasena: clave.entrada.value, borrar_trabajos: borrarTodo.checked }); return null; }
        catch (error) { return error.campos.contrasena || error.message; }
      },
    });
    if (resultado === "ok") { aviso("Tu cuenta se eliminó."); alSalir(); }
  }

  // ───────────────────────────────────────────────────────────── referencias: subir y mostrar
  const elegirReferencias = () => entradaReferencias.click();
  zonaReferencias.addEventListener("click", elegirReferencias);
  zonaReferencias.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegirReferencias(); } });
  entradaReferencias.addEventListener("change", () => { subirReferencias([...entradaReferencias.files]); entradaReferencias.value = ""; });
  const sobreReferencias = (e) => {
    e.preventDefault();
    const items = [...(e.dataTransfer?.items || [])];
    const valido = !items.length || items.some((i) => i.kind === "file" && (i.type === "" || i.type.startsWith("video/")));
    zonaReferencias.classList.toggle("sobre", valido);
    zonaReferencias.classList.toggle("invalido", !valido);
    if (e.dataTransfer) e.dataTransfer.dropEffect = valido ? "copy" : "none";
  };
  zonaReferencias.addEventListener("dragenter", sobreReferencias);
  zonaReferencias.addEventListener("dragover", sobreReferencias);
  zonaReferencias.addEventListener("dragleave", () => zonaReferencias.classList.remove("sobre", "invalido"));
  zonaReferencias.addEventListener("drop", (e) => { e.preventDefault(); zonaReferencias.classList.remove("sobre", "invalido"); subirReferencias([...e.dataTransfer.files]); });

  async function subirReferencias(archivos) {
    const validos = archivos.filter(esVideo);
    if (archivos.length > validos.length) aviso(`${archivos.length - validos.length} archivo(s) no son videos compatibles y se omitieron.`, { tipo: "error" });
    for (const archivo of validos) {
      const clave = `local-${++contadorLocal}`;
      subiendo.set(clave, { nombre: archivo.name, fraccion: 0, error: null });
      pintarReferencias();
      try {
        await subir("/api/referencias/archivo", archivo, (f) => { subiendo.get(clave).fraccion = f; pintarReferencias(); });
        subiendo.delete(clave);
      } catch (error) {
        subiendo.get(clave).error = error.message;
      }
      await refrescar();
    }
  }

  const alAnadirEnlace = async () => {
    const url = campoEnlace.value.trim();
    errorEnlace.textContent = "";
    if (!url) { poner(errorEnlace, icono("aviso"), "Pega primero un enlace."); campoEnlace.focus(); return; }
    botonEnlace.disabled = true;
    try {
      await api.referenciaEnlace(url);
      campoEnlace.value = "";
      aviso("Enlace añadido. Iris lo está descargando y analizando.");
      await refrescar();
    } catch (error) {
      poner(errorEnlace, icono("aviso"), error.message);
    } finally { botonEnlace.disabled = false; }
  };
  botonEnlace.addEventListener("click", alAnadirEnlace);
  campoEnlace.addEventListener("keydown", (e) => { if (e.key === "Enter") alAnadirEnlace(); });

  function crearTarjetaReferencia(clave) {
    const imagen = el("img", { alt: "", loading: "lazy", hidden: true });
    const miniatura = el("div", { clase: "miniatura" }, icono("pelicula", "grande"), imagen);
    const titulo = el("h3");
    const zona = el("div", { clase: "chips" });
    const interruptor = el("input", { type: "checkbox", id: `usar-${clave}`, "aria-label": "Usar esta referencia en mis videos" });
    const quitar = el("button", { type: "button", clase: "boton suave cuadrado pequeno peligro", "aria-label": "Quitar esta referencia", title: "Quitar esta referencia" }, icono("papelera"));
    const pie = el("div", { clase: "pie" }, el("label", { clase: "usar", for: interruptor.id }, el("span", { clase: "interruptor" }, interruptor, el("span")), "Usar"), quitar);
    const nodo = el("article", { clase: "referencia" }, miniatura, el("div", { clase: "cuerpo" }, titulo, zona, pie));
    let firma = "";
    interruptor.addEventListener("change", () => api.referenciaCambiar(clave, { activa: interruptor.checked }).then(refrescar).catch((e) => aviso(e.message, { tipo: "error" })));
    quitar.addEventListener("click", () => {
      if (subiendo.has(clave)) { subiendo.delete(clave); pintarReferencias(); return; }
      quitarConDeshacer("referencia", clave, titulo.textContent);
    });
    function actualizar(datos) {
      const nuevaFirma = JSON.stringify([datos.estado, datos.etapa, Math.round((datos.progreso || 0) * 50), datos.error, datos.perfil?.etiquetas, datos.activa, datos.titulo]);
      if (datos.titulo !== titulo.textContent) titulo.textContent = datos.titulo;
      nodo.classList.toggle("apagada", datos.local ? false : !datos.activa && datos.estado === "lista");
      if (datos.miniatura && !imagen.src) { imagen.src = `/api/referencias/${clave}/miniatura`; imagen.hidden = false; miniatura.querySelector(".icono")?.remove(); }
      interruptor.disabled = datos.estado !== "lista";
      if (interruptor.checked !== Boolean(datos.activa) && document.activeElement !== interruptor) interruptor.checked = Boolean(datos.activa);
      if (nuevaFirma === firma) return;
      firma = nuevaFirma;
      if (datos.local && !datos.error) {
        const pista = el("div", { clase: "progreso-pista" }, el("i"));
        establecerProgreso(pista, datos.fraccion);
        poner(zona, el("div", { clase: "progreso" }, pista, el("div", { clase: "progreso-texto" }, el("span", { texto: datos.fraccion >= 0.999 ? "Comprobando…" : `Subiendo… ${Math.round(datos.fraccion * 100)} %` }))));
      } else if (datos.error) {
        poner(zona, el("span", { clase: "etiqueta-chip error" }, icono("aviso"), datos.error));
      } else if (datos.estado !== "lista") {
        const pista = el("div", { clase: "progreso-pista" }, el("i"));
        establecerProgreso(pista, datos.progreso || 0);
        poner(zona, el("div", { clase: "progreso" }, pista, el("div", { clase: "progreso-texto" }, el("span", { texto: datos.etapa || "En espera" }), el("span", { texto: `${Math.round((datos.progreso || 0) * 100)} %` }))));
      } else {
        const etiquetas = (datos.perfil?.etiquetas || []).map((t) => el("span", { clase: "etiqueta-chip", texto: t }));
        const color = datos.perfil?.acento ? el("span", { clase: "etiqueta-chip" }, Object.assign(el("span", { clase: "muestra" }), {}), "Color dominante") : null;
        if (color) color.querySelector(".muestra").style.setProperty("--c", datos.perfil.acento);
        poner(zona, etiquetas, color);
      }
    }
    return { nodo, actualizar };
  }

  function pintarReferencias() {
    const lista = [
      ...[...subiendo].map(([clave, s]) => ({ clave, datos: { local: true, titulo: s.nombre, fraccion: s.fraccion, error: s.error, estado: "subiendo", activa: true } })),
      ...estado.referencias.filter((r) => !ocultos.has(r.id)).map((r) => ({ clave: r.id, datos: r })),
    ];
    const claves = new Set(lista.map((i) => i.clave));
    for (const [clave, tarjeta] of tarjetasReferencia) if (!claves.has(clave)) { tarjeta.nodo.remove(); tarjetasReferencia.delete(clave); }
    lista.forEach((item, i) => {
      let tarjeta = tarjetasReferencia.get(item.clave);
      if (!tarjeta) { tarjeta = crearTarjetaReferencia(item.clave); tarjetasReferencia.set(item.clave, tarjeta); }
      tarjeta.actualizar(item.datos);
      if (rejilla.children[i] !== tarjeta.nodo) rejilla.insertBefore(tarjeta.nodo, rejilla.children[i] || null);
    });
    vacioReferencias.hidden = lista.length > 0;
  }

  // ───────────────────────────────────────────────────────────── quitar con «Deshacer»
  function quitarConDeshacer(tipo, id, titulo) {
    ocultos.add(id);
    pintar();
    let deshecho = false;
    aviso(`«${titulo || (tipo === "video" ? "El video" : "La referencia")}» se quitó.`, {
      duracion: 6000, accion: { texto: "Deshacer", alHacer: () => { deshecho = true; ocultos.delete(id); pintar(); } },
    });
    setTimeout(async () => {
      if (deshecho) return;
      try { await (tipo === "video" ? api.trabajoBorrar(id) : api.referenciaBorrar(id)); }
      catch (error) { ocultos.delete(id); aviso(error.message, { tipo: "error" }); }
      refrescar();
    }, 6200);
  }

  // ───────────────────────────────────────────────────────────── videos
  const contexto = {
    refrescar: () => refrescar(),
    quitar: (id) => quitarConDeshacer("video", id, estado.trabajos.find((t) => t.id === id)?.titulo),
    crear: async (id) => { try { await api.crear(id); await refrescar(); } catch (error) { aviso(error.message, { tipo: "error" }); } },
  };

  async function nuevoTrabajo(enfocar = true) {
    const ultimo = estado.trabajos.filter((t) => !ocultos.has(t.id)).at(-1);
    const { id } = await api.trabajoNuevo(ultimo?.marca || null);
    await refrescar();
    if (!enfocar) return;
    tarjetasTrabajo.get(id)?.nodo.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    tarjetasTrabajo.get(id)?.enfocar();
  }
  botonAnadir.addEventListener("click", () => nuevoTrabajo().catch((e) => aviso(e.message, { tipo: "error" })));

  function pintarTrabajos() {
    const visibles = estado.trabajos.filter((t) => !ocultos.has(t.id));
    const ids = new Set(visibles.map((t) => t.id));
    for (const [id, tarjeta] of tarjetasTrabajo) if (!ids.has(id)) { tarjeta.nodo.remove(); tarjetasTrabajo.delete(id); }
    visibles.forEach((t, i) => {
      let tarjeta = tarjetasTrabajo.get(t.id);
      if (!tarjeta) { tarjeta = crearTrabajo(t.id, contexto); tarjetasTrabajo.set(t.id, tarjeta); }
      tarjeta.actualizar(t, i, estado.marcas);
      if (listaTrabajos.children[i] !== tarjeta.nodo) listaTrabajos.insertBefore(tarjeta.nodo, listaTrabajos.children[i] || null);
    });
  }

  function pintarBarra() {
    const visibles = estado.trabajos.filter((t) => !ocultos.has(t.id));
    const activos = visibles.filter((t) => ACTIVOS.has(t.estado));
    const creables = visibles.filter((t) => t.fuente_nombre && CREABLES.has(t.estado));
    const listos = visibles.filter((t) => t.estado === "listo").length;
    if (activos.length) {
      botonCrear.disabled = true;
      botonCrear.classList.add("ocupado");
      poner(botonCrear, el("span", { clase: "giro", "aria-hidden": "true" }), el("span", { clase: "texto-largo", texto: `Creando ${listos + 1} de ${listos + activos.length + creables.length}…` }));
      botonCrear.setAttribute("aria-label", "Creando videos");
    } else {
      botonCrear.disabled = creables.length === 0;
      botonCrear.classList.remove("ocupado");
      poner(botonCrear, icono("varita"), el("span", { clase: "texto-largo", texto: creables.length > 1 ? `Crear ${creables.length} videos` : "Crear video" }));
      botonCrear.setAttribute("aria-label", creables.length > 1 ? `Crear ${creables.length} videos` : "Crear video");
      botonCrear.title = creables.length ? "" : "Sube un video para poder crearlo";
    }
  }

  botonCrear.addEventListener("click", async () => {
    const creables = estado.trabajos.filter((t) => !ocultos.has(t.id) && t.fuente_nombre && CREABLES.has(t.estado));
    for (const t of creables) await api.crear(t.id).catch((e) => aviso(`${t.titulo}: ${e.message}`, { tipo: "error" }));
    await refrescar();
  });
  document.addEventListener("keydown", (e) => { if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !botonCrear.disabled) botonCrear.click(); });

  // ───────────────────────────────────────────────────────────── actualización periódica
  function pintar() { pintarReferencias(); pintarTrabajos(); pintarBarra(); }

  function avisarCambios() {
    for (const t of estado.trabajos) {
      const antes = estadoAnterior.get(t.id);
      if (antes && antes !== t.estado) {
        if (t.estado === "listo") { aviso(`«${t.titulo}» está listo.`); anunciar(`El video ${t.titulo} está listo.`); }
        if (t.estado === "error") { aviso(`«${t.titulo}»: ${t.error}`, { tipo: "error", duracion: 9000 }); }
      }
      estadoAnterior.set(t.id, t.estado);
    }
  }

  async function refrescar() {
    if (detenido) return;
    try {
      const datos = await api.estado();
      estado.referencias = datos.referencias;
      estado.trabajos = datos.trabajos;
      avisarCambios();
      pintar();
    } catch (error) {
      if (!(error instanceof ErrorApi) || error.estado !== 401) console.error(error);
    }
  }

  function programar() {
    clearTimeout(temporizador);
    if (detenido) return;
    const trabajando = estado.trabajos.some((t) => ACTIVOS.has(t.estado)) || estado.referencias.some((r) => r.estado === "en_cola" || r.estado === "analizando");
    temporizador = setTimeout(async () => { if (!document.hidden) await refrescar(); programar(); }, trabajando ? 800 : 4000);
  }

  (async () => {
    estado.marcas = await api.marcas().catch(() => []);
    await refrescar();
    if (estado.trabajos.length === 0) await nuevoTrabajo(false).catch(() => {});
    programar();
  })();
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refrescar(); });

  return { detener() { detenido = true; clearTimeout(temporizador); } };
}
