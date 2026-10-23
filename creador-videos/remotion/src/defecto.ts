import { Marca, Props } from "./tipos";

export const marcaPorDefecto: Marca = {
  nombre: "Marca",
  colores: { fondo: "#0B0B0F", texto: "#FFFFFF", acento: "#FFC400" },
  fuente: "'Arial Black', Impact, 'Helvetica Neue', Arial, sans-serif",
};

export const resolverMarca = (parcial: Props["marca"]): Marca => ({
  ...marcaPorDefecto,
  ...parcial,
  colores: { ...marcaPorDefecto.colores, ...parcial?.colores },
});

export const propsPorDefecto: Props = {
  formato: "demo",
  escenas: [
    { tipo: "gancho", duracion: 2, texto: "Tu gancho aquí" },
    { tipo: "contenido", duracion: 3, texto: "Una sola idea por toma" },
    { tipo: "cta", duracion: 2, texto: "Síguenos" },
  ],
};
