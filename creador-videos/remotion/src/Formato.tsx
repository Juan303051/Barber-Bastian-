import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  Series,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { resolverMarca } from "./defecto";
import { Escena, FPS, Marca, Props, fotogramas } from "./tipos";

const recurso = (ruta: string) => (/^https?:\/\//.test(ruta) ? ruta : staticFile(ruta));

/** Todas las medidas están pensadas para 1080 px de ancho y se escalan con esto. */
const useUnidad = () => useVideoConfig().width / 1080;

const Fondo = ({ escena, marca, duracion }: { escena: Escena; marca: Marca; duracion: number }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Un empuje lento hacia adelante da vida a una toma fija.
  const zoom = interpolate(frame, [0, duracion], [1, 1.08], { extrapolateRight: "clamp" });
  if (!escena.clip) {
    return (
      <AbsoluteFill
        style={{ background: `radial-gradient(circle at 50% 35%, ${marca.colores.acento}33, ${marca.colores.fondo} 70%)` }}
      />
    );
  }
  return (
    <AbsoluteFill style={{ backgroundColor: marca.colores.fondo, overflow: "hidden" }}>
      <OffthreadVideo
        src={recurso(escena.clip)}
        startFrom={Math.round((escena.desde ?? 0) * fps)}
        muted={escena.silenciar ?? false}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }}
      />
    </AbsoluteFill>
  );
};

const Gancho = ({ texto, marca }: { texto: string; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = spring({ frame, fps, config: { damping: 12, stiffness: 180 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 70 * u }}>
      <div
        style={{
          fontFamily: marca.fuente, fontWeight: 900,
          fontSize: 124 * u,
          lineHeight: 1.04,
          textAlign: "center",
          textTransform: "uppercase",
          color: marca.colores.texto,
          transform: `scale(${interpolate(entrada, [0, 1], [0.55, 1])})`,
          opacity: interpolate(frame, [0, 3], [0, 1], { extrapolateRight: "clamp" }),
          textShadow: `0 ${8 * u}px 0 rgba(0,0,0,.5), 0 0 ${40 * u}px rgba(0,0,0,.6)`,
          borderBottom: `${14 * u}px solid ${marca.colores.acento}`,
          paddingBottom: 24 * u,
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

const Contenido = ({ texto, marca }: { texto: string; marca: Marca }) => {
  const frame = useCurrentFrame();
  const u = useUnidad();
  const entra = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", padding: `0 ${60 * u}px ${150 * u}px` }}>
      <div
        style={{
          fontFamily: marca.fuente, fontWeight: 900,
          fontSize: 62 * u,
          lineHeight: 1.12,
          color: marca.colores.texto,
          backgroundColor: "rgba(0,0,0,.62)",
          borderLeft: `${16 * u}px solid ${marca.colores.acento}`,
          borderRadius: 14 * u,
          padding: `${28 * u}px ${36 * u}px`,
          opacity: entra,
          transform: `translateY(${(1 - entra) * 60 * u}px)`,
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

const Cierre = ({ texto, marca }: { texto?: string; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = spring({ frame, fps, config: { damping: 14 } });
  return (
    <AbsoluteFill
      style={{ justifyContent: "center", alignItems: "center", gap: 56 * u, padding: 80 * u, transform: `scale(${interpolate(entrada, [0, 1], [0.9, 1])})` }}
    >
      {marca.logo && <Img src={recurso(marca.logo)} style={{ width: 360 * u, height: 360 * u, objectFit: "contain" }} />}
      <div
        style={{ fontFamily: marca.fuente, fontWeight: 900, fontSize: 96 * u, lineHeight: 1.06, textAlign: "center", textTransform: "uppercase", color: marca.colores.texto }}
      >
        {texto ?? marca.nombre}
      </div>
      {marca.usuario && (
        <div
          style={{ fontFamily: marca.fuente, fontWeight: 900, fontSize: 54 * u, color: marca.colores.fondo, backgroundColor: marca.colores.acento, borderRadius: 999, padding: `${16 * u}px ${48 * u}px` }}
        >
          {marca.usuario}
        </div>
      )}
    </AbsoluteFill>
  );
};

const VistaEscena = ({ escena, marca, duracion }: { escena: Escena; marca: Marca; duracion: number }) => (
  <AbsoluteFill>
    <Fondo escena={escena} marca={marca} duracion={duracion} />
    {escena.tipo === "gancho" && <Gancho texto={escena.texto ?? ""} marca={marca} />}
    {escena.tipo === "contenido" && escena.texto && <Contenido texto={escena.texto} marca={marca} />}
    {escena.tipo === "cta" && <Cierre texto={escena.texto} marca={marca} />}
  </AbsoluteFill>
);

const Subtitulo = ({ texto, marca }: { texto: string; marca: Marca }) => {
  const frame = useCurrentFrame();
  const u = useUnidad();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: `0 ${70 * u}px`, top: "12%" }}>
      <div
        style={{
          fontFamily: marca.fuente, fontWeight: 900,
          fontSize: 70 * u,
          lineHeight: 1.1,
          textAlign: "center",
          color: marca.colores.texto,
          WebkitTextStroke: `${11 * u}px #000`,
          paintOrder: "stroke fill",
          transform: `scale(${interpolate(frame, [0, 4], [0.85, 1], { extrapolateRight: "clamp" })})`,
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

export const Formato = (props: Props) => {
  const fps = props.fps ?? FPS;
  const marca = resolverMarca(props.marca);
  return (
    <AbsoluteFill style={{ backgroundColor: marca.colores.fondo }}>
      <Series>
        {props.escenas.map((escena, i) => {
          const duracion = fotogramas(escena.duracion, fps);
          return (
            <Series.Sequence key={i} durationInFrames={duracion}>
              <VistaEscena escena={escena} marca={marca} duracion={duracion} />
            </Series.Sequence>
          );
        })}
      </Series>
      {props.subtitulos?.map((s, i) => (
        <Sequence key={i} from={Math.round(s.ini * fps)} durationInFrames={fotogramas(s.fin - s.ini, fps)}>
          <Subtitulo texto={s.texto} marca={marca} />
        </Sequence>
      ))}
      {props.voz && <Audio src={recurso(props.voz)} />}
      {props.musica && <Audio src={recurso(props.musica.archivo)} volume={props.musica.volumen ?? 0.15} loop />}
    </AbsoluteFill>
  );
};
