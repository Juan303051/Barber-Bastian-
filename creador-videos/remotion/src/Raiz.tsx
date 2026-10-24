import { CalculateMetadataFunction, Composition } from "remotion";
import { Formato } from "./Formato";
import { propsPorDefecto } from "./defecto";
import { FPS, Props, duracionTotal } from "./tipos";

const calcular: CalculateMetadataFunction<Props> = ({ props }) => {
  const fps = props.fps ?? FPS;
  return {
    durationInFrames: duracionTotal(props, fps),
    fps,
    width: props.ancho ?? 1080,
    height: props.alto ?? 1920,
  };
};

export const Raiz = () => (
  <Composition
    id="Formato"
    component={Formato}
    durationInFrames={210}
    fps={FPS}
    width={1080}
    height={1920}
    defaultProps={propsPorDefecto}
    calculateMetadata={calcular}
  />
);
