import { staticFile, useVideoConfig } from "remotion";

export const recurso = (ruta: string) => (/^https?:\/\//.test(ruta) ? ruta : staticFile(ruta));

/** Todas las medidas están pensadas para 1080 px de ancho y se escalan con esto. */
export const useUnidad = () => useVideoConfig().width / 1080;
