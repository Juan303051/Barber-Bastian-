export type Marca = {
  nombre: string;
  colores: { fondo: string; texto: string; acento: string };
  fuente: string;
  /** Para la palabra importante de cada frase (cursiva elegante). */
  fuenteSerif: string;
  /** Ruta relativa a `empresas/`, p. ej. "al-volante/logo.png". */
  logo?: string;
  /** Usuario que se muestra en el cierre, p. ej. "@alvolante". */
  usuario?: string;
};

export type Foco = {
  /** Posición y tamaño en % de la grabación de pantalla. */
  x: number;
  y: number;
  ancho: number;
  alto: number;
  /** Segundos desde el inicio de la escena. */
  ini: number;
  fin: number;
};

export type Escena = {
  /**
   * gancho: texto enorme que entra de golpe · contenido: toma con texto abajo · cta: cierre con logo, usuario y palabra clave ·
   * pantalla: grabación de pantalla flotante con zoom y recuadros de foco
   */
  tipo: "gancho" | "contenido" | "cta" | "pantalla";
  /** Segundos. */
  duracion: number;
  /** Segundo del video en el que empieza. Sin esto, la escena empieza cuando termina la anterior. */
  ini?: number;
  texto?: string;
  /** Solo en `cta`: palabra que el público debe comentar, p. ej. "EDITOR". */
  clave?: string;
  /** Ruta relativa a `empresas/` (o una URL). Sin clip, la escena usa el color de fondo de la marca. */
  clip?: string;
  /** Segundo del clip en el que empieza. */
  desde?: number;
  silenciar?: boolean;
  /** Solo en `pantalla`: recuadros que resaltan una zona, y el acercamiento (x, y en % de la grabación). */
  focos?: Foco[];
  zoom?: { escala: number; x: number; y: number };
  /** Solo en `pantalla`: ancho/alto de la grabación (por defecto 16/10). */
  relacion?: number;
};

export type Subtitulo = { ini: number; fin: number; texto: string };

/** Cada palabra con su tiempo: [inicio, fin, palabra], en segundos. Es el formato que guarda `./creador analizar`. */
export type PalabraT = [number, number, string];

export type EstiloPalabras = {
  /** Palabras que se ven a la vez (por defecto 3). */
  maxPalabras?: number;
  /** Segundos de silencio que cortan la página (por defecto 0.35). */
  pausa?: number;
  /** Palabras que se resaltan en grande y con el color de acento. */
  claves?: string[];
  /** Palabras que se escriben en serif cursiva. */
  serif?: string[];
  posicion?: "centro" | "abajo" | "arriba";
  mayusculas?: boolean;
};

export type Tiempo = { ini: number; fin: number };
/** Centro del elemento en % del cuadro (por defecto, el centro). */
export type Posicion = { x?: number; y?: number };

export type Capa = (
  | { tipo: "contador"; desde: number; hasta: number; prefijo?: string; sufijo?: string; color?: string; tamano?: number }
  | { tipo: "insignia"; numero: number }
  | {
      tipo: "tarjeta";
      variante: "comentario" | "notificacion" | "estadistica" | "foto";
      nombre?: string;
      texto?: string;
      cifra?: string;
      etiqueta?: string;
      meGusta?: string;
      /** Ruta relativa a `empresas/` (variante `foto`). */
      imagen?: string;
      ancho?: number;
      rotacion?: number;
    }
  | { tipo: "mira"; etiqueta?: string; radio?: number }
  | { tipo: "texto-curvo"; texto: string; forma?: "arco" | "onda"; tamano?: number; color?: string }
  | { tipo: "palabra"; texto: string; serif?: boolean; color?: string; tamano?: number }
  | { tipo: "titulo"; texto: string; color?: string; tamano?: number }
) &
  Tiempo &
  Posicion;

export type Zoom = { ini: number; fin: number; escala: number; x?: number; y?: number };

/** Acabado de color de la toma base. `intensidad` va de 0 (sin efecto) a 1. */
export type Acabado = { look: "natural" | "calido" | "frio" | "cine" | "vibrante"; intensidad?: number };

/** Latido sutil sobre la música: un pequeño acercamiento que se relaja en cada tiempo fuerte (segundos del video). */
export type Pulso = { tiempos: number[]; intensidad?: number };

export type Props = {
  formato: string;
  fps?: number;
  ancho?: number;
  alto?: number;
  marca?: Partial<Omit<Marca, "colores">> & { colores?: Partial<Marca["colores"]> };
  /** pleno: un solo cuadro · antes-despues: la misma toma cruda a la izquierda y la editada a la derecha */
  diseno?: "pleno" | "antes-despues";
  etiquetas?: { antes: string; despues: string };
  /** Toma continua que corre durante todo el video (la persona hablando). Las escenas se dibujan encima. */
  base?: { clip: string; desde?: number; silenciar?: boolean };
  /** Segundos. Obligatorio si no hay escenas; con `base`, `./creador render` lo calcula solo. */
  duracion?: number;
  escenas?: Escena[];
  zooms?: Zoom[];
  acabado?: Acabado;
  pulso?: Pulso;
  capas?: Capa[];
  subtitulos?: Subtitulo[];
  palabras?: PalabraT[];
  estiloPalabras?: EstiloPalabras;
  /** Arregla errores de la transcripción: { "cloud": "Claude" }. */
  correcciones?: Record<string, string>;
  /** Locución. Ruta relativa a `empresas/`. */
  voz?: string;
  musica?: { archivo: string; volumen?: number };
};

export const FPS = 30;

export const fotogramas = (segundos: number, fps: number) => Math.max(1, Math.round(segundos * fps));

export const duracionTotal = (props: Props, fps: number) =>
  Math.max(1, calcularDuracion(props, fps));

/** Con `duracion` manda ella; si no, el final de la última escena (las que tienen `ini` se colocan en su segundo exacto). */
const calcularDuracion = (props: Props, fps: number) => {
  if (props.duracion !== undefined) return fotogramas(props.duracion, fps);
  const escenas = props.escenas ?? [];
  const seguidas = escenas.filter((e) => e.ini === undefined).reduce((total, e) => total + fotogramas(e.duracion, fps), 0);
  const colocadas = escenas.filter((e) => e.ini !== undefined).map((e) => Math.round((e.ini ?? 0) * fps) + fotogramas(e.duracion, fps));
  return Math.max(seguidas, ...colocadas);
};
