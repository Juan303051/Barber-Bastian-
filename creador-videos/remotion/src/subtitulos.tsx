import { AbsoluteFill, Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Pagina, duracionPagina } from "./logica";
import { EstiloPalabras, Marca, fotogramas } from "./tipos";
import { useUnidad } from "./util";

const Palabra = ({ texto, ini, clave, serif, marca, mayusculas }: {
  texto: string;
  ini: number;
  clave: boolean;
  serif: boolean;
  marca: Marca;
  mayusculas: boolean;
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = spring({ frame: frame - Math.round(ini * fps), fps, config: { damping: 11, stiffness: 220 } });
  const visible = frame >= Math.round(ini * fps);
  const grande = clave ? 1.45 : 1;
  return (
    <span
      style={{
        display: "inline-block",
        opacity: visible ? 1 : 0,
        transform: `scale(${interpolate(entrada, [0, 1], [0.6, 1])}) translateY(${interpolate(entrada, [0, 1], [14, 0])}px)`,
        fontFamily: serif ? marca.fuenteSerif : marca.fuente,
        fontStyle: serif ? "italic" : "normal",
        fontWeight: serif ? 700 : 900,
        fontSize: 70 * u * grande,
        color: clave ? marca.colores.acento : marca.colores.texto,
        textTransform: mayusculas && !serif ? "uppercase" : "none",
        WebkitTextStroke: `${10 * u}px #000`,
        paintOrder: "stroke fill",
        textShadow: `0 ${6 * u}px ${18 * u}px rgba(0,0,0,.5)`,
        margin: `0 ${9 * u}px`,
        lineHeight: 1.05,
      }}
    >
      {texto}
    </span>
  );
};

/** Subtítulos palabra por palabra: cada palabra aparece cuando se dice; las claves crecen y toman el color de acento. */
export const SubtitulosPalabras = ({ paginas, marca, estilo, fps }: {
  paginas: Pagina[];
  marca: Marca;
  estilo: EstiloPalabras;
  fps: number;
}) => {
  const alto = { arriba: "26%", centro: "58%", abajo: "78%" }[estilo.posicion ?? "centro"];
  return (
    <>
      {paginas.map((pagina, i) => (
        <Sequence key={i} from={Math.round(pagina.ini * fps)} durationInFrames={fotogramas(duracionPagina(pagina, paginas[i + 1]), fps)}>
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", top: `calc(${alto} - 50%)`, padding: "0 60px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", alignItems: "baseline", maxWidth: "100%" }}>
              {pagina.tokens.map((t, j) => (
                <Palabra key={j} texto={t.texto} ini={t.ini - pagina.ini} clave={t.clave} serif={t.serif} marca={marca} mayusculas={estilo.mayusculas ?? false} />
              ))}
            </div>
          </AbsoluteFill>
        </Sequence>
      ))}
    </>
  );
};
