// Biblioteca de música: sube canciones, las analiza solas (tempo, pulso, energía) y pide declarar la licencia de cada una.
import { api, subir } from "./api.js";
import { aviso } from "./ui.js";
import { el, esAudio, establecerProgreso, icono, poner } from "./util.js";

const LICENCIAS = [
  ["sin-confirmar", "Sin confirmar"],
  ["propia", "Música propia"],
  ["licenciada", "Licencia comprada"],
  ["plataforma", "De la plataforma"],
];

function crearTarjeta(id, contexto) {
  const reproductor = el("button", { type: "button", clase: "disco", "aria-label": "Escuchar esta canción", "aria-pressed": "false" }, icono("play"));
  const titulo = el("h3");
  const zona = el("div", { clase: "chips" });
  const selector = el("select", { id: `licencia-${id}`, "aria-label": "Licencia de esta canción" }, LICENCIAS.map(([valor, texto]) => el("option", { value: valor, texto })));
  const interruptor = el("input", { type: "checkbox", id: `usar-musica-${id}`, "aria-label": "Usar esta canción en mis videos" });
  const quitar = el("button", { type: "button", clase: "boton suave cuadrado pequeno peligro", "aria-label": "Quitar esta canción", title: "Quitar esta canción" }, icono("papelera"));
  const licencia = el("div", { clase: "campo licencia" }, el("label", { for: selector.id, clase: "rotulo", texto: "Licencia" }), el("div", { clase: "entrada" }, selector, icono("abajo")));
  const pie = el("div", { clase: "pie" }, el("label", { clase: "usar", for: interruptor.id }, el("span", { clase: "interruptor" }, interruptor, el("span")), "Usar"), quitar);
  const nodo = el("article", { clase: "cancion" }, reproductor, el("div", { clase: "cuerpo" }, titulo, zona, licencia, pie));
  let sonido = null;
  let firma = "";

  reproductor.addEventListener("click", () => {
    if (!sonido) {
      sonido = new Audio(`/api/musica/${id}/audio`);
      sonido.addEventListener("ended", () => detener());
    }
    if (sonido.paused) {
      contexto.pausarOtras(id);
      sonido.play().catch(() => aviso("No pude reproducir esta canción en el navegador.", { tipo: "error" }));
      reproductor.setAttribute("aria-pressed", "true");
      poner(reproductor, icono("pausa"));
    } else detener();
  });
  function detener() {
    sonido?.pause();
    reproductor.setAttribute("aria-pressed", "false");
    poner(reproductor, icono("play"));
  }
  selector.addEventListener("change", () => api.musicaCambiar(id, { licencia: selector.value }).then(contexto.refrescar).catch((e) => aviso(e.message, { tipo: "error" })));
  interruptor.addEventListener("change", () => api.musicaCambiar(id, { activa: interruptor.checked }).then(contexto.refrescar).catch((e) => aviso(e.message, { tipo: "error" })));
  quitar.addEventListener("click", () => { detener(); contexto.quitar(id, titulo.textContent); });

  function actualizar(m) {
    if (m.titulo !== titulo.textContent) titulo.textContent = m.titulo;
    nodo.classList.toggle("apagada", m.estado === "lista" && !m.activa);
    reproductor.disabled = m.estado !== "lista";
    interruptor.disabled = m.estado !== "lista";
    selector.disabled = m.estado === "error" || Boolean(m.local);
    if (document.activeElement !== selector) selector.value = m.licencia;
    if (interruptor.checked !== Boolean(m.activa) && document.activeElement !== interruptor) interruptor.checked = Boolean(m.activa);
    const nuevaFirma = JSON.stringify([m.estado, m.etapa, m.error, m.bpm, m.confianza, m.licencia]);
    if (nuevaFirma === firma) return;
    firma = nuevaFirma;
    if (m.estado === "error") {
      poner(zona, el("span", { clase: "etiqueta-chip error" }, icono("aviso"), m.error || "No pude analizar esta canción."));
    } else if (m.estado !== "lista") {
      const pista = el("div", { clase: "progreso-pista" }, el("i"));
      establecerProgreso(pista, m.estado === "analizando" ? 0.6 : 0.1);
      poner(zona, el("div", { clase: "progreso" }, pista, el("div", { clase: "progreso-texto" }, el("span", { texto: m.etapa || "En espera" }))));
    } else {
      const chips = [el("span", { clase: "etiqueta-chip", texto: `${Math.round(m.bpm)} BPM · ${m.ritmo}` }), el("span", { clase: "etiqueta-chip", texto: `Energía ${m.intensidad}` })];
      if (m.confianza < 0.55) chips.push(el("span", { clase: "etiqueta-chip aviso" }, icono("aviso"), "Pulso poco claro"));
      if (m.licencia === "sin-confirmar") chips.push(el("span", { clase: "etiqueta-chip aviso" }, icono("aviso"), "Solo borradores"));
      poner(zona, chips);
    }
  }
  return { nodo, actualizar, detener };
}

export function crearSeccionMusica({ refrescar, quitarConDeshacer }) {
  const tarjetas = new Map();
  const subiendo = new Map();
  let contador = 0;
  const entrada = el("input", { type: "file", accept: "audio/*,.mp3,.wav,.m4a,.aac,.flac,.ogg,.opus", multiple: true, hidden: true, "aria-label": "Elegir canciones" });
  const zona = el("div", { clase: "soltar", role: "button", tabindex: "0", "aria-label": "Elegir o soltar canciones" },
    icono("musica"), el("strong", { texto: "Suelta aquí tus canciones" }),
    el("span", { clase: "fino", texto: "o haz clic para elegirlas · MP3, WAV, M4A, FLAC · Iris mide su pulso y energía" }));
  const lista = el("div", { clase: "referencias-rejilla" });
  const vacio = el("p", { clase: "ayuda", texto: "Sin música, los videos salen solo con tu voz. Con música, Iris elige la pista que encaja, la baja cuando hablas y apoya los acercamientos en su pulso." });
  const nota = el("p", { clase: "ayuda aviso-licencia" }, icono("escudo"),
    "Usa solo música con licencia comercial: propia, comprada o de la biblioteca de música comercial de tu plataforma. Iris no puede saber si una canción está libre: declara la licencia de cada una.");
  const nodo = el("div", { clase: "tarjeta" }, zona, entrada, nota, vacio, lista);

  const elegir = () => entrada.click();
  zona.addEventListener("click", elegir);
  zona.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); elegir(); } });
  entrada.addEventListener("change", () => { subirCanciones([...entrada.files]); entrada.value = ""; });
  const sobre = (e) => {
    e.preventDefault();
    const items = [...(e.dataTransfer?.items || [])];
    const valido = !items.length || items.some((i) => i.kind === "file" && (i.type === "" || i.type.startsWith("audio/")));
    zona.classList.toggle("sobre", valido);
    zona.classList.toggle("invalido", !valido);
    if (e.dataTransfer) e.dataTransfer.dropEffect = valido ? "copy" : "none";
  };
  zona.addEventListener("dragenter", sobre);
  zona.addEventListener("dragover", sobre);
  zona.addEventListener("dragleave", () => zona.classList.remove("sobre", "invalido"));
  zona.addEventListener("drop", (e) => { e.preventDefault(); zona.classList.remove("sobre", "invalido"); subirCanciones([...e.dataTransfer.files]); });

  async function subirCanciones(archivos) {
    const validos = archivos.filter(esAudio);
    if (archivos.length > validos.length) aviso(`${archivos.length - validos.length} archivo(s) no son música compatible y se omitieron.`, { tipo: "error" });
    for (const archivo of validos) {
      const clave = `local-${++contador}`;
      subiendo.set(clave, { nombre: archivo.name, fraccion: 0, error: null });
      pintar(ultimaLista);
      try {
        await subir("/api/musica/archivo", archivo, (f) => { subiendo.get(clave).fraccion = f; pintar(ultimaLista); });
        subiendo.delete(clave);
      } catch (error) {
        subiendo.get(clave).error = error.message;
      }
      await refrescar();
    }
  }

  const contexto = {
    refrescar: () => refrescar(),
    quitar: (id, titulo) => {
      if (subiendo.has(id)) { subiendo.delete(id); pintar(ultimaLista); return; }
      quitarConDeshacer("musica", id, titulo);
    },
    pausarOtras: (id) => { for (const [otra, t] of tarjetas) if (otra !== id) t.detener(); },
  };
  let ultimaLista = [];
  function pintar(lista_) {
    ultimaLista = lista_;
    const locales = [...subiendo].map(([clave, s]) => ({ clave, datos: { id: clave, local: true, titulo: s.nombre, estado: "subiendo", etapa: `Subiendo… ${Math.round(s.fraccion * 100)} %`, error: s.error, licencia: "sin-confirmar", activa: true } }));
    const remotas = lista_.map((m) => ({ clave: m.id, datos: m }));
    const todo = [...locales, ...remotas];
    const claves = new Set(todo.map((i) => i.clave));
    for (const [clave, t] of tarjetas) if (!claves.has(clave)) { t.detener(); t.nodo.remove(); tarjetas.delete(clave); }
    todo.forEach((item, i) => {
      let t = tarjetas.get(item.clave);
      if (!t) { t = crearTarjeta(item.clave, contexto); tarjetas.set(item.clave, t); }
      t.actualizar(item.datos);
      if (lista.children[i] !== t.nodo) lista.insertBefore(t.nodo, lista.children[i] || null);
    });
    vacio.hidden = todo.length > 0;
  }
  return { nodo, pintar };
}
