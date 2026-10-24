// Pantalla de acceso: crear la primera cuenta o entrar. Sigue las guías de Apple: etiqueta fija en cada campo, campo seguro con
// botón de mostrar, validación del correo al salir del campo, método de autenticación con nombre y beneficios explicados.
import { api, ErrorApi } from "./api.js";
import { el, icono, logo, poner } from "./util.js";

const CORREO = /^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/;
const COMUNES = new Set(["12345678", "123456789", "password", "contrasena", "contraseña", "qwertyui", "iloveyou", "11111111", "abc12345", "admin123", "bienvenido"]);
const NIVELES = ["Muy débil", "Débil", "Aceptable", "Buena", "Excelente"];
// Valores estándar del atributo autocomplete: permiten que el gestor de contraseñas del navegador proponga y rellene.
const AUTOCOMPLETAR = { crear: "new-password", entrar: "current-password" };

export function fuerzaDeClave(clave) {
  if (!clave) return { nivel: 0, texto: "" };
  if (COMUNES.has(clave.toLowerCase())) return { nivel: 0, texto: "Muy común" };
  let puntos = 0;
  if (clave.length >= 8) puntos += 1;
  if (clave.length >= 12) puntos += 1;
  if (/[a-z]/.test(clave) && /[A-Z]/.test(clave)) puntos += 1;
  if (/\d/.test(clave) && /[^A-Za-z0-9]/.test(clave)) puntos += 1;
  else if (/\d/.test(clave) || /[^A-Za-z0-9]/.test(clave)) puntos += 0.5;
  const nivel = clave.length < 8 ? Math.min(1, Math.floor(puntos)) : Math.max(1, Math.min(4, Math.floor(puntos)));
  return { nivel, texto: NIVELES[nivel] };
}

function campo({ id, etiqueta, tipo = "text", autocompletar, ejemplo, modo }) {
  const entrada = el("input", { id, name: id, type: tipo, autocomplete: autocompletar, placeholder: ejemplo, inputmode: modo, "aria-describedby": `${id}-msg`, required: true, spellcheck: "false", autocapitalize: "off" });
  const mensaje = el("div", { id: `${id}-msg`, clase: "mensaje-campo", "aria-live": "polite" });
  const caja = el("div", { clase: "entrada" }, entrada);
  const grupo = el("div", { clase: "campo" }, el("label", { for: id, texto: etiqueta }), caja, mensaje);
  return {
    grupo, entrada, caja,
    error(texto) {
      caja.classList.toggle("mal", Boolean(texto));
      entrada.setAttribute("aria-invalid", texto ? "true" : "false");
      poner(mensaje, texto ? [icono("aviso"), el("span", { texto })] : []);
    },
  };
}

export function montarAcceso(raiz, { primeraVez, alEntrar }) {
  const modo = primeraVez ? "crear" : "entrar";
  const titulo = el("h1", { id: "acceso-titulo", clase: "titulo-grande", texto: primeraVez ? "Te damos la bienvenida a Iris" : "Qué bueno verte" });
  const nombre = primeraVez ? campo({ id: "nombre", etiqueta: "Tu nombre", autocompletar: "name", ejemplo: "Ana Pérez" }) : null;
  const correo = campo({ id: "correo", etiqueta: "Correo", tipo: "email", autocompletar: "username", ejemplo: "ana@empresa.com", modo: "email" });
  const clave = campo({ id: "contrasena", etiqueta: "Contraseña", tipo: "password", autocompletar: AUTOCOMPLETAR[modo], ejemplo: primeraVez ? "Mínimo 8 caracteres" : "Tu contraseña" });
  const ojo = el("button", { type: "button", clase: "boton suave cuadrado extremo", "aria-label": "Mostrar contraseña", "aria-pressed": "false", title: "Mostrar contraseña" }, icono("ojo"));
  clave.caja.append(ojo);
  clave.entrada.classList.add("con-extremo");
  ojo.addEventListener("click", () => {
    const visible = clave.entrada.type === "password";
    clave.entrada.type = visible ? "text" : "password";
    ojo.setAttribute("aria-pressed", String(visible));
    ojo.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
    ojo.title = ojo.getAttribute("aria-label");
    poner(ojo, icono(visible ? "ojo-no" : "ojo"));
    clave.entrada.focus();
  });

  const medidor = primeraVez ? el("div", { clase: "fuerza" }, el("div", { clase: "fuerza-barra", "aria-hidden": "true" }, el("i")), el("div", { clase: "fuerza-texto", "aria-live": "polite" })) : null;
  const recordar = el("input", { type: "checkbox", id: "recordar", checked: primeraVez });
  const aviso = el("div", { clase: "aviso-formulario", role: "alert" });
  const textoBoton = primeraVez ? "Crear cuenta con contraseña" : "Entrar con contraseña";
  const boton = el("button", { type: "submit", clase: "boton principal" }, el("span", { texto: textoBoton }));
  const formulario = el("form", { clase: "formulario", novalidate: true },
    nombre?.grupo, correo.grupo, clave.grupo, medidor,
    el("div", { clase: "fila-recordar" }, el("label", { for: "recordar", texto: "Recordarme en este equipo" }), el("span", { clase: "interruptor" }, recordar, el("span"))),
    aviso, boton);

  const olvido = el("div", { clase: "nota-clave", hidden: true }, "Iris funciona en tu equipo, así que la contraseña se restablece desde la Terminal: ", el("code", { texto: "./creador cuenta restablecer tu@correo.com" }));
  const botonOlvido = el("button", { type: "button", texto: "¿Olvidaste tu contraseña?", "aria-expanded": "false" });
  botonOlvido.addEventListener("click", () => { olvido.hidden = !olvido.hidden; botonOlvido.setAttribute("aria-expanded", String(!olvido.hidden)); });

  const tarjeta = el("section", { clase: "acceso-tarjeta vidrio", "aria-labelledby": "acceso-titulo" },
    el("div", { clase: "marca" }, logo(), titulo, el("p", { clase: "subtitulo", texto: primeraVez ? "Crea la cuenta con la que vas a entrar. Será la primera de tu equipo." : "Entra para seguir creando videos sin editar." })),
    el("ul", { clase: "beneficios" },
      el("li", {}, icono("rayo"), "Sube una toma y escribe lo que quieres."),
      el("li", {}, icono("varita"), "Iris aprende de tus referencias y lo hace por ti."),
      el("li", {}, icono("escudo"), "Tus videos se procesan en este equipo, no en la nube.")),
    formulario,
    el("div", { clase: "pie-acceso" }, primeraVez ? el("span", { texto: "Después podrás añadir a otras personas de tu equipo." }) : [botonOlvido, olvido]));
  poner(raiz, el("main", { id: "contenido", clase: "acceso" }, tarjeta));

  const validarCorreo = () => {
    const valor = correo.entrada.value.trim();
    correo.error(valor && !CORREO.test(valor) ? "Escribe un correo válido, por ejemplo ana@empresa.com." : "");
    return CORREO.test(valor);
  };
  nombre?.entrada.addEventListener("input", () => { if (nombre.entrada.value.trim()) nombre.error(""); });
  correo.entrada.addEventListener("blur", validarCorreo);
  correo.entrada.addEventListener("input", () => correo.caja.classList.contains("mal") && validarCorreo());
  if (medidor) {
    clave.entrada.addEventListener("input", () => {
      const { nivel, texto } = fuerzaDeClave(clave.entrada.value);
      medidor.querySelector("i").style.setProperty("--p", `${nivel * 25}%`);
      medidor.querySelector(".fuerza-texto").textContent = texto ? `Seguridad: ${texto}` : "";
      if (clave.caja.classList.contains("mal") && clave.entrada.value.length >= 8) clave.error("");
    });
  }

  let cuentaAtras = null;
  const bloquear = (segundos) => {
    clearInterval(cuentaAtras);
    let restante = segundos;
    const pintar = () => {
      boton.disabled = restante > 0;
      poner(boton, el("span", { texto: restante > 0 ? `Inténtalo de nuevo en ${restante >= 60 ? Math.ceil(restante / 60) + " min" : restante + " s"}` : textoBoton }));
      if (restante <= 0) { clearInterval(cuentaAtras); aviso.textContent = ""; }
      restante -= 1;
    };
    pintar();
    cuentaAtras = setInterval(pintar, 1000);
  };
  const ocupado = (si) => {
    boton.disabled = si;
    poner(boton, si ? [el("span", { clase: "giro", "aria-hidden": "true" }), el("span", { texto: primeraVez ? "Creando tu cuenta…" : "Entrando…" })] : el("span", { texto: textoBoton }));
  };
  const agitar = () => { tarjeta.classList.remove("agitar"); void tarjeta.offsetWidth; tarjeta.classList.add("agitar"); };

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    aviso.textContent = "";
    let primero = null;
    if (nombre) { const mal = !nombre.entrada.value.trim(); nombre.error(mal ? "Escribe tu nombre." : ""); if (mal) primero = nombre; }
    if (!validarCorreo()) { if (!correo.entrada.value.trim()) correo.error("Escribe tu correo."); primero ??= correo; }
    if (!clave.entrada.value) { clave.error(primeraVez ? "Elige una contraseña de al menos 8 caracteres." : "Escribe tu contraseña."); primero ??= clave; }
    else if (primeraVez && clave.entrada.value.length < 8) { clave.error("Usa al menos 8 caracteres."); primero ??= clave; }
    else clave.error("");
    if (primero) { primero.entrada.focus(); agitar(); return; }

    ocupado(true);
    const datos = { correo: correo.entrada.value.trim(), contrasena: clave.entrada.value, recordar: recordar.checked };
    try {
      const respuesta = primeraVez ? await api.registro({ ...datos, nombre: nombre.entrada.value.trim() }) : await api.entrar(datos);
      tarjeta.classList.add("sale");
      setTimeout(() => alEntrar(respuesta.usuario), matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 320);
    } catch (error) {
      ocupado(false);
      if (!(error instanceof ErrorApi)) throw error;
      if (error.estado === 429) bloquear(error.espera || 60);
      const campos = { correo, contrasena: clave, nombre };
      let marcado = null;
      for (const [llave, texto] of Object.entries(error.campos)) { campos[llave]?.error(texto); marcado ??= campos[llave]; }
      if (!marcado) poner(aviso, icono("aviso"), el("span", { texto: error.message }));
      (marcado ?? clave).entrada.focus();
      if (!primeraVez && error.estado === 401) clave.entrada.select();
      agitar();
    }
  });
  (nombre ?? correo).entrada.focus();
}
