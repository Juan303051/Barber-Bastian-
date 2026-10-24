import { ReactNode, useId } from "react";
import { Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { formatearNumero, trayecto, valorContador } from "./logica";
import { Capa, Marca } from "./tipos";
import { recurso, useUnidad } from "./util";

type De<T extends Capa["tipo"]> = Extract<Capa, { tipo: T }>;

/** Coloca un elemento por su centro, en % del cuadro, y lo hace entrar y salir con un fundido. */
export const Colocada = ({ x = 50, y = 50, children }: { x?: number; y?: number; children: ReactNode }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacidad = interpolate(frame, [0, 4, durationInFrames - 6, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div style={{ position: "absolute", left: `${x}%`, top: `${y}%`, transform: "translate(-50%, -50%)", opacity: opacidad }}>
      {children}
    </div>
  );
};

const useEntrada = (retraso = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - retraso, fps, config: { damping: 12, stiffness: 170 } });
};

export const Contador = ({ capa, marca }: { capa: De<"contador">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = useEntrada();
  const color = capa.color ?? "#3DFF7A";
  const valor = valorContador(frame / fps, 0, capa.fin - capa.ini, capa.desde, capa.hasta);
  return (
    <div
      style={{
        fontFamily: marca.fuente,
        fontWeight: 900,
        fontSize: (capa.tamano ?? 150) * u,
        color,
        transform: `scale(${interpolate(entrada, [0, 1], [0.6, 1])})`,
        textShadow: `0 0 ${30 * u}px ${color}88, 0 ${6 * u}px 0 rgba(0,0,0,.45)`,
        whiteSpace: "nowrap",
      }}
    >
      {capa.prefijo}
      {formatearNumero(valor)}
      {capa.sufijo}
    </div>
  );
};

export const Insignia = ({ capa, marca }: { capa: De<"insignia">; marca: Marca }) => {
  const u = useUnidad();
  const entrada = useEntrada();
  return (
    <div
      style={{
        width: 120 * u,
        height: 120 * u,
        borderRadius: 30 * u,
        backgroundColor: marca.colores.acento,
        color: marca.colores.fondo,
        fontFamily: marca.fuente,
        fontWeight: 900,
        fontSize: 78 * u,
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        boxShadow: `0 ${10 * u}px ${30 * u}px rgba(0,0,0,.4)`,
        transform: `scale(${interpolate(entrada, [0, 1], [0.3, 1])}) rotate(${interpolate(entrada, [0, 1], [-18, 0])}deg)`,
      }}
    >
      {capa.numero}.
    </div>
  );
};

const Avatar = ({ nombre, color, tamano }: { nombre: string; color: string; tamano: number }) => (
  <div
    style={{
      width: tamano,
      height: tamano,
      borderRadius: "50%",
      backgroundColor: color,
      color: "#fff",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      fontWeight: 800,
      fontSize: tamano * 0.5,
      flexShrink: 0,
    }}
  >
    {nombre.trim().charAt(0).toUpperCase() || "·"}
  </div>
);

export const Tarjeta = ({ capa, marca }: { capa: De<"tarjeta">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const u = useUnidad();
  const entrada = useEntrada();
  const flota = Math.sin(frame / 14) * 6 * u;
  const ancho = (capa.ancho ?? (capa.variante === "foto" ? 380 : 560)) * u;
  const marco = {
    width: ancho,
    transform: `translateY(${flota}px) scale(${interpolate(entrada, [0, 1], [0.7, 1])}) rotate(${capa.rotacion ?? 0}deg)`,
    fontFamily: "'Helvetica Neue', Arial, sans-serif",
  } as const;

  if (capa.variante === "foto") {
    return (
      <div style={{ ...marco, backgroundColor: "#fff", padding: 14 * u, borderRadius: 18 * u, boxShadow: `0 ${18 * u}px ${50 * u}px rgba(0,0,0,.45)` }}>
        {capa.imagen ? (
          <Img src={recurso(capa.imagen)} style={{ width: "100%", aspectRatio: "3 / 4", objectFit: "cover", borderRadius: 8 * u, display: "block" }} />
        ) : (
          <div style={{ width: "100%", aspectRatio: "3 / 4", backgroundColor: "#D8DADF", borderRadius: 8 * u }} />
        )}
        {capa.texto && <div style={{ color: "#222", fontSize: 30 * u, fontWeight: 700, paddingTop: 10 * u, textAlign: "center" }}>{capa.texto}</div>}
      </div>
    );
  }

  if (capa.variante === "notificacion") {
    return (
      <div style={marco}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 * u, backgroundColor: "#fff", borderRadius: 60 * u, padding: `${14 * u}px ${28 * u}px ${14 * u}px ${14 * u}px`, boxShadow: `0 ${10 * u}px ${34 * u}px rgba(0,0,0,.35)` }}>
          <Avatar nombre={capa.nombre ?? ""} color={marca.colores.acento} tamano={64 * u} />
          <div style={{ color: "#16161A", fontSize: 32 * u, fontWeight: 600, lineHeight: 1.15 }}>{capa.texto}</div>
        </div>
        {capa.etiqueta && <div style={{ color: "#fff", fontSize: 24 * u, opacity: 0.85, paddingTop: 10 * u, paddingLeft: 24 * u, textShadow: "0 1px 4px rgba(0,0,0,.6)" }}>{capa.etiqueta}</div>}
      </div>
    );
  }

  const oscura = {
    backgroundColor: "rgba(18,18,22,.86)",
    color: "#fff",
    borderRadius: 34 * u,
    padding: 30 * u,
    boxShadow: `0 ${16 * u}px ${44 * u}px rgba(0,0,0,.45)`,
  } as const;

  if (capa.variante === "estadistica") {
    return (
      <div style={{ ...marco, ...oscura, textAlign: "center" }}>
        <div style={{ fontFamily: marca.fuente, fontWeight: 900, fontSize: 110 * u, lineHeight: 1, color: marca.colores.acento }}>{capa.cifra}</div>
        {capa.etiqueta && <div style={{ fontSize: 34 * u, fontWeight: 600, paddingTop: 8 * u, opacity: 0.9 }}>{capa.etiqueta}</div>}
        {capa.texto && <div style={{ fontSize: 26 * u, paddingTop: 12 * u, opacity: 0.65 }}>{capa.texto}</div>}
      </div>
    );
  }

  return (
    <div style={{ ...marco, ...oscura }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18 * u }}>
        <Avatar nombre={capa.nombre ?? ""} color={marca.colores.acento} tamano={70 * u} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 30 * u, fontWeight: 800 }}>{capa.nombre}</div>
          {capa.etiqueta && <div style={{ fontSize: 22 * u, opacity: 0.6 }}>{capa.etiqueta}</div>}
        </div>
        {capa.meGusta && <div style={{ fontSize: 28 * u, fontWeight: 700, color: marca.colores.acento }}>♥ {capa.meGusta}</div>}
      </div>
      {capa.cifra && <div style={{ fontFamily: marca.fuente, fontWeight: 900, fontSize: 84 * u, lineHeight: 1, paddingTop: 22 * u }}>{capa.cifra}</div>}
      {capa.texto && <div style={{ fontSize: 30 * u, lineHeight: 1.25, paddingTop: 16 * u, opacity: 0.92 }}>{capa.texto}</div>}
    </div>
  );
};

export const Mira = ({ capa, marca }: { capa: De<"mira">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const u = useUnidad();
  const entrada = useEntrada();
  const radio = (capa.radio ?? 260) * u;
  const lado = radio * 2 + 60 * u;
  const centro = lado / 2;
  const esquina = 46 * u;
  const trazo = 4 * u;
  const rincones = [[-1, -1], [1, -1], [-1, 1], [1, 1]];
  return (
    <div style={{ width: lado, height: lado, position: "relative", transform: `scale(${interpolate(entrada, [0, 1], [1.4, 1])})` }}>
      <svg width={lado} height={lado} style={{ position: "absolute", inset: 0 }}>
        <circle
          cx={centro}
          cy={centro}
          r={radio}
          fill="none"
          stroke="#fff"
          strokeOpacity={0.9}
          strokeWidth={trazo}
          strokeDasharray={`${radio * 0.9} ${radio * 0.35}`}
          transform={`rotate(${frame * 1.6} ${centro} ${centro})`}
        />
        {rincones.map(([sx, sy], i) => {
          const px = centro + sx * (radio + 8 * u);
          const py = centro + sy * (radio + 8 * u);
          return <path key={i} d={`M ${px - sx * esquina} ${py} L ${px} ${py} L ${px} ${py - sy * esquina}`} fill="none" stroke={marca.colores.acento} strokeWidth={trazo} strokeLinecap="round" />;
        })}
      </svg>
      {capa.etiqueta && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: -4 * u,
            transform: "translateX(-50%)",
            backgroundColor: marca.colores.acento,
            color: marca.colores.fondo,
            fontFamily: "'Helvetica Neue', Arial, sans-serif",
            fontWeight: 800,
            fontSize: 28 * u,
            padding: `${6 * u}px ${20 * u}px`,
            borderRadius: 8 * u,
            letterSpacing: 1,
            textTransform: "uppercase",
          }}
        >
          {capa.etiqueta}
        </div>
      )}
    </div>
  );
};

export const TextoCurvo = ({ capa, marca }: { capa: De<"texto-curvo">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const u = useUnidad();
  const entrada = useEntrada();
  const ancho = 900 * u;
  const alto = 420 * u;
  const id = `trayecto${useId().replace(/[^A-Za-z0-9]/g, "")}`;
  const desplazamiento = interpolate(entrada, [0, 1], [38, 50]);
  return (
    <svg width={ancho} height={alto} style={{ overflow: "visible", opacity: Math.min(1, entrada * 1.4) }}>
      <defs>
        <path id={id} d={trayecto(capa.forma ?? "arco", ancho, alto)} />
      </defs>
      <text
        fill={capa.color ?? marca.colores.texto}
        fontFamily={marca.fuente}
        fontWeight={900}
        fontSize={(capa.tamano ?? 84) * u}
        textAnchor="middle"
        stroke="rgba(0,0,0,.55)"
        strokeWidth={8 * u}
        paintOrder="stroke fill"
        style={{ transform: `translateY(${Math.sin(frame / 18) * 4 * u}px)` }}
      >
        <textPath href={`#${id}`} startOffset={`${desplazamiento}%`}>
          {capa.texto}
        </textPath>
      </text>
    </svg>
  );
};

export const PalabraGigante = ({ capa, marca }: { capa: De<"palabra">; marca: Marca }) => {
  const u = useUnidad();
  const entrada = useEntrada();
  const color = capa.color ?? marca.colores.acento;
  const tamano = (capa.tamano ?? 260) * u;
  // Un apilado de sombras sin desenfoque da el volumen de una letra extruida.
  const volumen = Array.from({ length: 10 }, (_, i) => `${(i + 1) * 1.2 * u}px ${(i + 1) * 1.6 * u}px 0 rgba(0,0,0,${0.55 - i * 0.03})`).join(", ");
  return (
    <div
      style={{
        fontFamily: capa.serif ? marca.fuenteSerif : marca.fuente,
        fontStyle: capa.serif ? "italic" : "normal",
        fontWeight: 900,
        fontSize: tamano,
        lineHeight: 0.95,
        color,
        textTransform: capa.serif ? "none" : "uppercase",
        textShadow: volumen,
        whiteSpace: "nowrap",
        transform: `scale(${interpolate(entrada, [0, 1], [0.5, 1])}) rotate(${interpolate(entrada, [0, 1], [-6, 0])}deg)`,
      }}
    >
      {capa.texto}
    </div>
  );
};

export const VistaCapa = ({ capa, marca }: { capa: Capa; marca: Marca }) => {
  switch (capa.tipo) {
    case "contador":
      return <Contador capa={capa} marca={marca} />;
    case "insignia":
      return <Insignia capa={capa} marca={marca} />;
    case "tarjeta":
      return <Tarjeta capa={capa} marca={marca} />;
    case "mira":
      return <Mira capa={capa} marca={marca} />;
    case "texto-curvo":
      return <TextoCurvo capa={capa} marca={marca} />;
    case "palabra":
      return <PalabraGigante capa={capa} marca={marca} />;
  }
};
