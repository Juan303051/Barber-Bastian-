import { Marca, Props } from "./tipos";

export const marcaPorDefecto: Marca = {
  nombre: "Marca",
  colores: { fondo: "#0B0B0F", texto: "#FFFFFF", acento: "#FFC400" },
  fuente: "'Arial Black', Impact, 'Helvetica Neue', Arial, sans-serif",
  fuenteSerif: "Georgia, 'Times New Roman', serif",
};

export const resolverMarca = (parcial: Props["marca"]): Marca => ({
  ...marcaPorDefecto,
  ...parcial,
  colores: { ...marcaPorDefecto.colores, ...parcial?.colores },
});

/** Remotion mezcla estos valores con los del guion: aquí no puede haber nada que un guion que no lo trae vaya a heredar. */
export const propsPorDefecto: Props = { formato: "demo", escenas: [] };
