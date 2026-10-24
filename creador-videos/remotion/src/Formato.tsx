import { ReactNode, useMemo } from "react";
import { AbsoluteFill, Audio, OffthreadVideo, Sequence, Series, useCurrentFrame, useVideoConfig } from "remotion";
import { resolverMarca } from "./defecto";
import { VistaEscena } from "./escenas";
import { escalaPorPulso, filtroDeAcabado, paginar, zoomEn } from "./logica";
import { Colocada, VistaCapa } from "./piezas";
import { SubtitulosPalabras } from "./subtitulos";
import { FPS, Marca, Props, fotogramas } from "./tipos";
import { recurso, useUnidad } from "./util";

/** Capas que ocupan todo el cuadro (se colocan solas): transiciones y logo animado. */
const PANTALLA_COMPLETA = new Set<string>(["transicion", "logo"]);

type BaseProps = { base: NonNullable<Props["base"]>; zooms: Props["zooms"]; silenciar: boolean; acabado: Props["acabado"]; pulso: Props["pulso"] };

const BaseContinua = ({ base, zooms, silenciar, acabado, pulso }: BaseProps) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const { escala, x, y } = zoomEn(t, zooms);
  const { filtro, vineta } = filtroDeAcabado(acabado);
  const latido = pulso ? escalaPorPulso(t, pulso.tiempos, pulso.intensidad) : 1;
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000" }}>
      <OffthreadVideo
        src={recurso(base.clip)}
        startFrom={Math.round((base.desde ?? 0) * fps)}
        muted={silenciar}
        style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${escala * latido})`, transformOrigin: `${x}% ${y}%`, filter: filtro }}
      />
      {vineta > 0 && <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,${vineta}) 100%)` }} />}
    </AbsoluteFill>
  );
};

const SubtituloFrase = ({ texto, marca }: { texto: string; marca: Marca }) => {
  const u = useUnidad();
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: `0 ${70 * u}px`, top: "12%" }}>
      <div
        style={{
          fontFamily: marca.fuente,
          fontWeight: 900,
          fontSize: 70 * u,
          lineHeight: 1.1,
          textAlign: "center",
          color: marca.colores.texto,
          WebkitTextStroke: `${11 * u}px #000`,
          paintOrder: "stroke fill",
        }}
      >
        {texto}
      </div>
    </AbsoluteFill>
  );
};

/** Todo lo que se ve del video (toma base, escenas, capas y subtítulos) sin el audio de locución ni de música. */
const Cuerpo = ({ props, marca, silenciarBase }: { props: Props; marca: Marca; silenciarBase: boolean }) => {
  const fps = props.fps ?? FPS;
  const paginas = useMemo(
    () => (props.palabras ? paginar(props.palabras, props.estiloPalabras, props.correcciones) : []),
    [props.palabras, props.estiloPalabras, props.correcciones],
  );
  return (
    <AbsoluteFill
      style={{ background: props.base ? marca.colores.fondo : `radial-gradient(circle at 50% 35%, ${marca.colores.acento}33, ${marca.colores.fondo} 70%)` }}
    >
      {props.base && (
        <BaseContinua base={props.base} zooms={props.zooms} silenciar={silenciarBase || (props.base.silenciar ?? false)} acabado={props.acabado} pulso={props.pulso} />
      )}
      <Series>
        {(props.escenas ?? []).filter((e) => e.ini === undefined).map((escena, i) => {
          const duracion = fotogramas(escena.duracion, fps);
          return (
            <Series.Sequence key={i} durationInFrames={duracion}>
              <VistaEscena escena={escena} marca={marca} duracion={duracion} hayBase={props.base !== undefined} />
            </Series.Sequence>
          );
        })}
      </Series>
      {(props.escenas ?? []).filter((e) => e.ini !== undefined).map((escena, i) => {
        const duracion = fotogramas(escena.duracion, fps);
        return (
          <Sequence key={`colocada-${i}`} from={Math.round((escena.ini ?? 0) * fps)} durationInFrames={duracion}>
            <VistaEscena escena={escena} marca={marca} duracion={duracion} hayBase={props.base !== undefined} />
          </Sequence>
        );
      })}
      {(props.capas ?? []).filter((c) => !PANTALLA_COMPLETA.has(c.tipo)).map((capa, i) => (
        <Sequence key={i} from={Math.round(capa.ini * fps)} durationInFrames={fotogramas(capa.fin - capa.ini, fps)}>
          <Colocada x={capa.x} y={capa.y}>
            <VistaCapa capa={capa} marca={marca} />
          </Colocada>
        </Sequence>
      ))}
      {paginas.length > 0 && <SubtitulosPalabras paginas={paginas} marca={marca} estilo={props.estiloPalabras ?? {}} fps={fps} />}
      {(props.capas ?? []).filter((c) => PANTALLA_COMPLETA.has(c.tipo)).map((capa, i) => (
        <Sequence key={`completa-${i}`} from={Math.round(capa.ini * fps)} durationInFrames={fotogramas(capa.fin - capa.ini, fps)}>
          <VistaCapa capa={capa} marca={marca} />
        </Sequence>
      ))}
      {props.subtitulos?.map((s, i) => (
        <Sequence key={i} from={Math.round(s.ini * fps)} durationInFrames={fotogramas(s.fin - s.ini, fps)}>
          <SubtituloFrase texto={s.texto} marca={marca} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

/** Un cuadro con el aspecto del video, reducido y con bordes redondeados y sombra. */
const Panel = ({ x, y, ancho, children }: { x: number; y: number; ancho: number; children: ReactNode }) => {
  const { width, height } = useVideoConfig();
  const u = useUnidad();
  const escala = ancho / width;
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: ancho,
        height: height * escala,
        borderRadius: 26 * u,
        overflow: "hidden",
        backgroundColor: "#000",
        boxShadow: `0 ${18 * u}px ${50 * u}px rgba(0,0,0,.3)`,
      }}
    >
      <div style={{ width, height, transform: `scale(${escala})`, transformOrigin: "top left" }}>{children}</div>
    </div>
  );
};

const Etiqueta = ({ texto, x, y }: { texto: string; x: number; y: number }) => {
  const u = useUnidad();
  return (
    <div style={{ position: "absolute", left: x, top: y, fontFamily: "'Helvetica Neue', Arial, sans-serif", fontWeight: 800, fontSize: 40 * u, color: "#111" }}>{texto}</div>
  );
};

const TomaCruda = ({ props, marca }: { props: Props; marca: Marca }) => {
  const u = useUnidad();
  if (props.base) {
    return <Cuerpo props={{ ...props, escenas: [], capas: [], palabras: undefined, subtitulos: [], zooms: [], diseno: "pleno" }} marca={marca} silenciarBase />;
  }
  return (
    <AbsoluteFill style={{ backgroundColor: "#2B2D33", justifyContent: "center", alignItems: "center" }}>
      <div style={{ fontFamily: "'Helvetica Neue', Arial, sans-serif", fontWeight: 700, fontSize: 64 * u, color: "#8D929C", textAlign: "center", padding: 60 * u }}>tu toma cruda</div>
    </AbsoluteFill>
  );
};

const AntesDespues = ({ props, marca }: { props: Props; marca: Marca }) => {
  const { width, height } = useVideoConfig();
  const u = useUnidad();
  const etiquetas = props.etiquetas ?? { antes: "antes", despues: "después" };
  const anchoAntes = width * 0.26;
  const anchoDespues = width * 0.6;
  const xAntes = width * 0.05;
  const xDespues = width * 0.35;
  const yAntes = height * 0.3;
  const yDespues = height * 0.1;
  return (
    <AbsoluteFill style={{ backgroundColor: "#FBFBFC" }}>
      <Etiqueta texto={etiquetas.antes} x={xAntes} y={yAntes - 62 * u} />
      <Panel x={xAntes} y={yAntes} ancho={anchoAntes}>
        <TomaCruda props={props} marca={marca} />
      </Panel>
      <Etiqueta texto={etiquetas.despues} x={xDespues} y={yDespues - 62 * u} />
      <Panel x={xDespues} y={yDespues} ancho={anchoDespues}>
        <Cuerpo props={props} marca={marca} silenciarBase={false} />
      </Panel>
    </AbsoluteFill>
  );
};

export const Formato = (props: Props) => {
  const marca = resolverMarca(props.marca);
  return (
    <AbsoluteFill style={{ backgroundColor: marca.colores.fondo }}>
      {props.diseno === "antes-despues" ? <AntesDespues props={props} marca={marca} /> : <Cuerpo props={props} marca={marca} silenciarBase={false} />}
      {props.voz && <Audio src={recurso(props.voz)} />}
      {props.musica && <Audio src={recurso(props.musica.archivo)} volume={props.musica.volumen ?? 0.15} loop />}
    </AbsoluteFill>
  );
};
