export type Marca = {
  nombre: string;
  colores: { fondo: string; texto: string; acento: string };
  fuente: string;
  /** Ruta relativa a `empresas/`, p. ej. "al-volante/logo.png". */
  logo?: string;
  /** Usuario que se muestra en el cierre, p. ej. "@alvolante". */
  usuario?: string;
};

export type Escena = {
  /** gancho: texto enorme que entra de golpe · contenido: toma con texto abajo · cta: cierre con logo y usuario */
  tipo: "gancho" | "contenido" | "cta";
  /** Segundos. */
  duracion: number;
  texto?: string;
  /** Ruta relativa a `empresas/` (o una URL). Sin clip, la escena usa el color de fondo de la marca. */
  clip?: string;
  /** Segundo del clip en el que empieza. */
  desde?: number;
  silenciar?: boolean;
};

export type Subtitulo = { ini: number; fin: number; texto: string };

export type Props = {
  formato: string;
  fps?: number;
  ancho?: number;
  alto?: number;
  marca?: Partial<Marca> & { colores?: Partial<Marca["colores"]> };
  escenas: Escena[];
  subtitulos?: Subtitulo[];
  /** Locución. Ruta relativa a `empresas/`. */
  voz?: string;
  musica?: { archivo: string; volumen?: number };
};

export const FPS = 30;

export const fotogramas = (segundos: number, fps: number) => Math.max(1, Math.round(segundos * fps));
