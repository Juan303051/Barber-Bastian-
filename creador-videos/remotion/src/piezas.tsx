import { ReactNode, useId } from "react";
import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { estadoCalculadora, formatearNumero, opacidadDestello, posicionBarrido, suave, trayecto, valorContador } from "./logica";
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

/** Título de gancho: hasta 7 palabras en varias líneas, dentro de un ancho seguro, con entrada y salida suaves. */
export const Titulo = ({ capa, marca }: { capa: De<"titulo">; marca: Marca }) => {
  const u = useUnidad();
  const { width } = useVideoConfig();
  const entrada = useEntrada();
  const color = capa.color ?? marca.colores.texto;
  return (
    <div
      style={{
        width: width * 0.82,
        textAlign: "center",
        fontFamily: marca.fuente,
        fontWeight: 900,
        fontSize: (capa.tamano ?? 92) * u,
        lineHeight: 1.05,
        color,
        textShadow: `0 ${4 * u}px ${18 * u}px rgba(0,0,0,.55)`,
        WebkitTextStroke: `${9 * u}px rgba(0,0,0,.85)`,
        paintOrder: "stroke fill",
        textWrap: "balance",
        transform: `translateY(${interpolate(entrada, [0, 1], [24 * u, 0])}px) scale(${interpolate(entrada, [0, 1], [0.92, 1])})`,
      }}
    >
      {capa.texto}
    </div>
  );
};


const TECLAS = ["−", "+", "%", "="];
const TECLA_DE: Record<string, number> = { restar: 0, sumar: 1, restar_pct: 2, total: 3 };
const COLOR_DE: Record<string, string> = { restar: "#FF5A52", restar_pct: "#FF5A52", sumar: "#4CFF8A", total: "#FFD24A", mostrar: "#9EC9FF" };

/** Calculadora de dinero: el valor sube o baja en sincronía con la voz y cada operación enciende su tecla. */
export const Calculadora = ({ capa, marca }: { capa: De<"calculadora">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const entrada = useEntrada();
  const t = capa.ini + frame / fps;
  const moneda = capa.moneda ?? "$";
  const { valor, evento, desde } = estadoCalculadora(t, capa.eventos);
  const op = evento?.op ?? "fijar";
  const animando = evento !== null && evento.a !== null && desde < evento.dur;
  const color = animando ? (op === "fijar" ? marca.colores.acento : COLOR_DE[op] ?? "#E8FFE9") : "#E8FFE9";
  const texto = `${valor < 0 ? "-" : ""}${moneda}${formatearNumero(Math.abs(valor), ".")}`;
  const ancho = 900 * u;
  const tamano = Math.min(152 * u, (ancho - 100 * u) / (Math.max(5, texto.length) * 0.62));
  const marcaDelta = evento && desde < Math.max(evento.dur, 2.4) ? Math.min(1, desde / 0.18, (Math.max(evento.dur, 2.4) - desde) / 0.4) : 0;
  const signo = op === "restar" || op === "restar_pct" ? "−" : op === "sumar" ? "+" : op === "total" ? "=" : "";
  const cifraDelta = evento ? (op === "restar_pct" ? `${formatearNumero(evento.valor, ".")}%` : `${moneda}${formatearNumero(evento.valor, ".")}`) : "";
  const tecla = TECLA_DE[op];
  const pulsoTecla = evento && desde < 0.4 ? 1 - Math.sin((desde / 0.4) * Math.PI) * 0.1 : 1;
  const mono = "'SF Mono', Menlo, 'Courier New', monospace";
  return (
    <div
      style={{
        width: ancho,
        borderRadius: 40 * u,
        padding: `${22 * u}px ${26 * u}px ${26 * u}px`,
        background: "linear-gradient(160deg, rgba(34,36,44,.96), rgba(12,13,17,.97))",
        border: `${2 * u}px solid rgba(255,255,255,.14)`,
        boxShadow: `0 ${26 * u}px ${70 * u}px rgba(0,0,0,.55), inset 0 ${2 * u}px 0 rgba(255,255,255,.08)`,
        transform: `translateY(${interpolate(entrada, [0, 1], [30 * u, 0])}px) scale(${interpolate(entrada, [0, 1], [0.85, 1])})`,
        fontFamily: mono,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: 12 * u }}>
        <div style={{ display: "flex", gap: 9 * u }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => (
            <div key={c} style={{ width: 16 * u, height: 16 * u, borderRadius: "50%", backgroundColor: c, opacity: 0.85 }} />
          ))}
        </div>
        <div
          style={{
            fontFamily: marca.fuente,
            fontWeight: 900,
            fontSize: 28 * u,
            letterSpacing: 2 * u,
            textTransform: "uppercase",
            color: evento ? COLOR_DE[op] ?? marca.colores.acento : "#9AA0AA",
            opacity: evento ? 1 : 0.7,
          }}
        >
          {evento?.etiqueta ?? "Calculadora"}
        </div>
      </div>
      <div
        style={{
          borderRadius: 24 * u,
          background: "linear-gradient(180deg, #0A110D, #0F1A13)",
          boxShadow: `inset 0 ${6 * u}px ${18 * u}px rgba(0,0,0,.6)`,
          padding: `${12 * u}px ${28 * u}px ${16 * u}px`,
          textAlign: "right",
          overflow: "hidden",
        }}
      >
        <div style={{ height: 52 * u, fontSize: 42 * u, fontWeight: 800, color: COLOR_DE[op] ?? "#E8FFE9", opacity: marcaDelta, transform: `translateY(${(1 - marcaDelta) * 10 * u}px)`, whiteSpace: "nowrap" }}>
          {signo ? `${signo} ` : ""}
          {cifraDelta}
        </div>
        <div
          style={{
            fontSize: tamano,
            fontWeight: 800,
            lineHeight: 1.05,
            color,
            fontVariantNumeric: "tabular-nums",
            whiteSpace: "nowrap",
            textShadow: `0 0 ${26 * u}px ${color}66`,
          }}
        >
          {texto}
        </div>
      </div>
      <div style={{ display: "flex", gap: 16 * u, paddingTop: 14 * u }}>
        {TECLAS.map((c, i) => {
          const activa = tecla === i && evento !== null && desde < 1.2;
          return (
            <div
              key={c}
              style={{
                flex: 1,
                height: 64 * u,
                borderRadius: 20 * u,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: marca.fuente,
                fontWeight: 900,
                fontSize: 40 * u,
                color: activa ? "#101114" : "#D8DBE2",
                backgroundColor: activa ? COLOR_DE[op] : "rgba(255,255,255,.09)",
                boxShadow: activa ? `0 0 ${30 * u}px ${COLOR_DE[op]}aa` : `inset 0 ${-4 * u}px 0 rgba(0,0,0,.35)`,
                transform: `scale(${activa ? pulsoTecla : 1})`,
              }}
            >
              {c}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** La imagen del logo con un destello que la cruza una vez; la usan el cierre y la capa de logo. */
export const LogoImagen = ({ archivo, lado, destello = true }: { archivo: string; lado: number; destello?: boolean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const u = useUnidad();
  const fuente = recurso(archivo);
  const brillo = interpolate(frame, [Math.round(fps * 0.45), Math.round(fps * 1.25)], [-30, 130], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{ position: "relative", width: lado, height: lado }}>
      <Img src={fuente} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain", filter: `drop-shadow(0 ${10 * u}px ${28 * u}px rgba(0,0,0,.5))` }} />
      {destello && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            WebkitMaskImage: `url(${fuente})`,
            WebkitMaskSize: "contain",
            WebkitMaskRepeat: "no-repeat",
            WebkitMaskPosition: "center",
            backgroundImage: `linear-gradient(105deg, transparent ${brillo - 18}%, rgba(255,255,255,.9) ${brillo}%, transparent ${brillo + 18}%)`,
          }}
        />
      )}
    </div>
  );
};

/** Logo animado: entra con un resorte, un destello lo cruza una vez y respira con un halo del color de la marca. */
export const LogoAnimado = ({ capa, marca }: { capa: De<"logo">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const u = useUnidad();
  const entrada = useEntrada();
  const marcaDeAgua = capa.estilo === "marca";
  const lado = (capa.estilo === "cierre" ? 560 : marcaDeAgua ? 150 : 430) * u;
  const salida = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const respira = 1 + Math.sin(frame / 12) * 0.012;
  const centro = capa.estilo === "cierre" ? { left: "50%", top: "46%" } : marcaDeAgua ? { left: "86%", top: "18%" } : { left: "50%", top: "30%" };
  return (
    <AbsoluteFill style={{ opacity: marcaDeAgua ? Math.min(0.78, salida) : salida }}>
      {capa.estilo === "cierre" && <AbsoluteFill style={{ backgroundColor: `rgba(0,0,0,${0.62 * Math.min(1, entrada * 1.5)})` }} />}
      <div style={{ position: "absolute", ...centro, width: lado, height: lado, transform: `translate(-50%, -50%) scale(${interpolate(entrada, [0, 1], [0.55, 1]) * respira})` }}>
        {!marcaDeAgua && (
          <div style={{ position: "absolute", inset: -40 * u, borderRadius: "50%", background: `radial-gradient(circle, ${marca.colores.acento}55 0%, transparent 65%)`, opacity: 0.4 + Math.sin(frame / 14) * 0.15 }} />
        )}
        <LogoImagen archivo={capa.archivo} lado={lado} destello={!marcaDeAgua} />
      </div>
    </AbsoluteFill>
  );
};

/** Transición sobre un corte: destello, cortina del color de la marca o impacto con anillo. El corte ocurre a mitad de la pieza. */
export const Transicion = ({ capa, marca }: { capa: De<"transicion">; marca: Marca }) => {
  const frame = useCurrentFrame();
  const { durationInFrames, width, height } = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  if (capa.estilo === "destello") {
    return <AbsoluteFill style={{ backgroundColor: "#fff", opacity: 0.9 * opacidadDestello(p) }} />;
  }
  if (capa.estilo === "barrido") {
    const x = posicionBarrido(p);
    return (
      <AbsoluteFill style={{ overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            top: -height * 0.1,
            left: `${x}%`,
            width: "112%",
            height: height * 1.2,
            transform: "skewX(-14deg)",
            background: `linear-gradient(90deg, ${marca.colores.acento}, ${marca.colores.acento}ee)`,
            boxShadow: `-${width * 0.02}px 0 0 rgba(255,255,255,.9), ${width * 0.03}px 0 ${width * 0.06}px rgba(0,0,0,.35)`,
          }}
        />
      </AbsoluteFill>
    );
  }
  const radio = interpolate(suave(p), [0, 1], [0.05, 1.25]) * Math.hypot(width, height) * 0.5;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ backgroundColor: "#fff", opacity: 0.55 * opacidadDestello(Math.min(1, p * 1.6)) }} />
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: radio * 2,
          height: radio * 2,
          marginLeft: -radio,
          marginTop: -radio,
          borderRadius: "50%",
          border: `${width * 0.03 * (1 - p)}px solid ${marca.colores.acento}`,
          opacity: 1 - p * 0.85,
        }}
      />
    </AbsoluteFill>
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
    case "titulo":
      return <Titulo capa={capa} marca={marca} />;
    case "calculadora":
      return <Calculadora capa={capa} marca={marca} />;
    case "logo":
      return <LogoAnimado capa={capa} marca={marca} />;
    case "transicion":
      return <Transicion capa={capa} marca={marca} />;
  }
};
