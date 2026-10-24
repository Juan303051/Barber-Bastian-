import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { LogoImagen } from "./piezas";
import { Escena, Marca } from "./tipos";
import { recurso, useUnidad } from "./util";

const Fondo = ({ escena, marca, duracion, hayBase }: { escena: Escena; marca: Marca; duracion: number; hayBase: boolean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Un empuje lento hacia adelante da vida a una toma fija.
  const zoom = interpolate(frame, [0, duracion], [1, 1.08], { extrapolateRight: "clamp" });
  if (!escena.clip) {
    if (hayBase) return escena.tipo === "cta" ? <AbsoluteFill style={{ backgroundColor: "rgba(0,0,0,.62)" }} /> : null;
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
          fontFamily: marca.fuente,
          fontWeight: 900,
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
          fontFamily: marca.fuente,
          fontWeight: 900,
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

const Cierre = ({ texto, clave, marca }: { texto?: string; clave?: string; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = spring({ frame, fps, config: { damping: 14 } });
  const titulo = { fontFamily: marca.fuente, fontWeight: 900, textAlign: "center", color: marca.colores.texto } as const;
  const volumen = Array.from({ length: 8 }, (_, i) => `${(i + 1) * 1.1 * u}px ${(i + 1) * 1.5 * u}px 0 rgba(0,0,0,${0.5 - i * 0.04})`).join(", ");
  return (
    <AbsoluteFill
      style={{ justifyContent: "center", alignItems: "center", gap: 44 * u, padding: 80 * u, transform: `scale(${interpolate(entrada, [0, 1], [0.9, 1])})` }}
    >
      {marca.logo && <LogoImagen archivo={marca.logo} lado={300 * u} />}
      {clave ? (
        <>
          <div style={{ ...titulo, fontSize: 70 * u }}>Comenta</div>
          <div style={{ ...titulo, fontSize: 190 * u, lineHeight: 1, color: marca.colores.acento, textShadow: volumen, textTransform: "uppercase" }}>
            «{clave}»
          </div>
          {texto && <div style={{ ...titulo, fontSize: 56 * u, lineHeight: 1.15 }}>{texto}</div>}
        </>
      ) : (
        <div style={{ ...titulo, fontSize: 96 * u, lineHeight: 1.06, textTransform: "uppercase" }}>{texto ?? marca.nombre}</div>
      )}
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

/** Grabación de pantalla flotante sobre fondo claro, con acercamiento a una zona y recuadros de foco. */
const Pantalla = ({ escena, marca }: { escena: Escena; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const u = useUnidad();
  const t = frame / fps;
  const ancho = width * 0.92;
  const alto = ancho / (escena.relacion ?? 16 / 10);
  const k = interpolate(frame, [0, 28], [0, 1], { extrapolateRight: "clamp", easing: (x) => 1 - Math.pow(1 - x, 3) });
  const zoom = escena.zoom;
  const s = zoom ? 1 + (zoom.escala - 1) * k : 1;
  const tx = zoom ? ((50 - zoom.x) / 100) * ancho * s : 0;
  const ty = zoom ? ((50 - zoom.y) / 100) * alto * s : 0;
  const entra = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ backgroundColor: "#ECEDEF" }}>
      <div
        style={{
          position: "absolute",
          left: (width - ancho) / 2,
          top: (height - alto) / 2 - height * 0.04,
          width: ancho,
          height: alto,
          opacity: entra,
          transform: `translate(${tx}px, ${ty}px) scale(${s})`,
        }}
      >
        <div style={{ width: "100%", height: "100%", borderRadius: 26 * u, overflow: "hidden", backgroundColor: "#fff", boxShadow: `0 ${24 * u}px ${70 * u}px rgba(0,0,0,.32)` }}>
          {escena.clip ? (
            <OffthreadVideo
              src={recurso(escena.clip)}
              startFrom={Math.round((escena.desde ?? 0) * fps)}
              muted={escena.silenciar ?? true}
              style={{ width: "100%", height: "100%", objectFit: "contain" }}
            />
          ) : (
            <div style={{ width: "100%", height: "100%", padding: 30 * u, boxSizing: "border-box" }}>
              <div style={{ display: "flex", gap: 10 * u, paddingBottom: 24 * u }}>
                {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
                  <div key={c} style={{ width: 20 * u, height: 20 * u, borderRadius: "50%", backgroundColor: c }} />
                ))}
              </div>
              {[70, 92, 55, 80, 40].map((w, i) => (
                <div key={i} style={{ width: `${w}%`, height: 26 * u, borderRadius: 8 * u, backgroundColor: i === 0 ? "#D7DAE0" : "#EEF0F3", marginBottom: 22 * u }} />
              ))}
              <div style={{ fontFamily: "'Helvetica Neue', Arial, sans-serif", fontSize: 30 * u, color: "#9AA0AA", paddingTop: 10 * u }}>tu grabación de pantalla</div>
            </div>
          )}
        </div>
        {(escena.focos ?? []).map((f, i) => {
          if (t < f.ini || t > f.fin) return null;
          const pulso = 1 + Math.sin((t - f.ini) * 7) * 0.025;
          return (
            <div
              key={i}
              style={{
                position: "absolute",
                left: `${f.x}%`,
                top: `${f.y}%`,
                width: `${f.ancho}%`,
                height: `${f.alto}%`,
                border: `${6 * u}px solid ${marca.colores.acento}`,
                borderRadius: 16 * u,
                boxShadow: `0 0 ${34 * u}px ${marca.colores.acento}99`,
                transform: `scale(${pulso})`,
              }}
            />
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export const VistaEscena = ({ escena, marca, duracion, hayBase }: { escena: Escena; marca: Marca; duracion: number; hayBase: boolean }) => {
  if (escena.tipo === "pantalla") return <Pantalla escena={escena} marca={marca} />;
  return (
    <AbsoluteFill>
      <Fondo escena={escena} marca={marca} duracion={duracion} hayBase={hayBase} />
      {escena.tipo === "gancho" && <Gancho texto={escena.texto ?? ""} marca={marca} />}
      {escena.tipo === "contenido" && escena.texto && <Contenido texto={escena.texto} marca={marca} />}
      {escena.tipo === "cta" && <Cierre texto={escena.texto} clave={escena.clave} marca={marca} />}
    </AbsoluteFill>
  );
};
