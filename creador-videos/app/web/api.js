// Comunicación con el servidor local. Los errores traen siempre un mensaje listo para mostrar.
export class ErrorApi extends Error {
  constructor(estado, cuerpo) {
    super(cuerpo?.mensaje || "Algo salió mal. Inténtalo de nuevo.");
    this.estado = estado;
    this.campos = cuerpo?.campos || {};
    this.espera = cuerpo?.espera || 0;
  }
}

async function pedir(metodo, ruta, cuerpo) {
  let respuesta;
  try {
    respuesta = await fetch(ruta, {
      method: metodo,
      headers: cuerpo !== undefined ? { "Content-Type": "application/json" } : {},
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
      credentials: "same-origin",
    });
  } catch {
    throw new ErrorApi(0, { mensaje: "No puedo hablar con Iris. ¿Sigue abierta la ventana de la Terminal?" });
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    if (respuesta.status === 401 && ruta !== "/api/entrar") document.dispatchEvent(new CustomEvent("sesion-caducada"));
    throw new ErrorApi(respuesta.status, datos);
  }
  return datos;
}

export const api = {
  sesion: () => pedir("GET", "/api/sesion"),
  registro: (cuerpo) => pedir("POST", "/api/registro", cuerpo),
  entrar: (cuerpo) => pedir("POST", "/api/entrar", cuerpo),
  salir: () => pedir("POST", "/api/salir", {}),
  eliminarCuenta: (cuerpo) => pedir("DELETE", "/api/cuenta", cuerpo),
  aceptarTextos: () => pedir("POST", "/api/cuenta/aceptar", { acepto: true }),
  marcas: () => pedir("GET", "/api/marcas"),
  estado: () => pedir("GET", "/api/estado"),
  interpretar: (prompt, opciones, marca) => pedir("POST", "/api/interpretar", { prompt, opciones, marca: marca || null }),
  escenasOrdenar: (id, orden) => pedir("PATCH", `/api/trabajos/${id}/escenas`, { orden }),
  escenaBorrar: (id, escena) => pedir("DELETE", `/api/trabajos/${id}/escenas/${escena}`),
  logoBorrar: (marca) => pedir("DELETE", `/api/marcas/${encodeURIComponent(marca)}/logo`),
  permisoMenores: (id, confirmo) => pedir("POST", `/api/trabajos/${id}/permiso-menores`, { confirmo }),
  referenciaEnlace: (url) => pedir("POST", "/api/referencias/enlace", { url }),
  referenciaCambiar: (id, cambios) => pedir("PATCH", `/api/referencias/${id}`, cambios),
  referenciaBorrar: (id) => pedir("DELETE", `/api/referencias/${id}`),
  trabajoNuevo: (marca) => pedir("POST", "/api/trabajos", { marca }),
  trabajoCambiar: (id, cambios) => pedir("PATCH", `/api/trabajos/${id}`, cambios),
  trabajoBorrar: (id) => pedir("DELETE", `/api/trabajos/${id}`),
  crear: (id) => pedir("POST", `/api/trabajos/${id}/crear`, {}),
  cancelar: (id) => pedir("POST", `/api/trabajos/${id}/cancelar`, {}),
  musicaCambiar: (id, cambios) => pedir("PATCH", `/api/musica/${id}`, cambios),
  musicaBorrar: (id) => pedir("DELETE", `/api/musica/${id}`),
  ia: () => pedir("GET", "/api/ia"),
  iaGuardar: (cambios) => pedir("PUT", "/api/ia", cambios),
  iaProbar: () => pedir("POST", "/api/ia/probar", {}),
  perfil: (marca) => pedir("GET", `/api/perfil?marca=${encodeURIComponent(marca || "")}`),
  perfilGuardar: (marca, respuestas) => pedir("PUT", "/api/perfil", { marca: marca || null, respuestas }),
};

/** Sube un video como flujo (PUT) con avance real; devuelve una promesa y permite cancelar. */
export function subir(ruta, archivo, alAvanzar) {
  return new Promise((resolver, rechazar) => {
    const peticion = new XMLHttpRequest();
    peticion.open("PUT", `${ruta}${ruta.includes("?") ? "&" : "?"}nombre=${encodeURIComponent(archivo.name)}`);
    peticion.upload.addEventListener("progress", (e) => e.lengthComputable && alAvanzar(e.loaded / e.total));
    peticion.addEventListener("load", () => {
      let cuerpo = {};
      try { cuerpo = JSON.parse(peticion.responseText); } catch { /* sin cuerpo */ }
      peticion.status >= 200 && peticion.status < 300 ? resolver(cuerpo) : rechazar(new ErrorApi(peticion.status, cuerpo));
    });
    peticion.addEventListener("error", () => rechazar(new ErrorApi(0, { mensaje: "Se cortó la subida. Revisa que Iris siga abierta e inténtalo otra vez." })));
    peticion.send(archivo);
  });
}
