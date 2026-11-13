// The brand's drawn parts: the icon, the wordmark with its drawn question mark, the
// stage track, and the small pieces of a claim page that scenes share.
import type { CSSProperties, FC, ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { arrive } from "./motion";
import { C } from "./tokens";

/** site/public/mark.svg: the magnifier over the capsule. */
export const Mark: FC<{ size: number }> = ({ size }) => (
  <svg viewBox="0 0 64 64" width={size} height={size} style={{ flex: "none" }}>
    <rect width="64" height="64" rx="16" fill="#ffffff" />
    <path d="M44.5 45.5 51.5 52.5" fill="none" stroke="#16477d" strokeWidth="8" strokeLinecap="round" />
    <circle cx="31" cy="32" r="19.5" fill="#ffffff" stroke="#16477d" strokeWidth="5.7" />
    <path d="M30.4 25h-6.9a7 7 0 0 0 0 14h6.9z" fill="#f28a62" />
    <path d="M31.6 25h6.9a7 7 0 0 1 0 14h-6.9z" fill="#1687da" />
  </svg>
);

/**
 * "What came of it?": a light lead, a heavy tail, and a question mark that is drawn so
 * its dot can be the blue marker. With `drawAt`, the hook is drawn and the dot lands.
 */
export const Wordmark: FC<{ size: number; drawAt?: number; color?: string }> = ({
  size,
  drawAt,
  color = C.ink,
}) => {
  const frame = useCurrentFrame();
  const hook = drawAt === undefined ? 1 : arrive(frame, drawAt, 21);
  const dot = drawAt === undefined ? 1 : arrive(frame, drawAt + 18, 18);
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        fontSize: size,
        letterSpacing: "-0.01em",
        lineHeight: 1.1,
        color,
        whiteSpace: "nowrap",
      }}
    >
      <span style={{ fontWeight: 400 }}>What came</span>
      <span style={{ fontWeight: 800, marginLeft: "0.26em" }}>of it</span>
      <svg
        viewBox="0 0 20 30"
        style={{
          height: "0.94em",
          width: "auto",
          flex: "none",
          marginLeft: "0.05em",
          transform: "translateY(0.13em)",
          overflow: "visible",
        }}
      >
        <path
          d="M4.2 8.8a5.9 5.9 0 1 1 9 5c-2.1 1.3-3.2 2.4-3.2 4.7"
          pathLength={1}
          fill="none"
          stroke="currentColor"
          strokeWidth={4.8}
          strokeLinecap="round"
          strokeDasharray={1}
          strokeDashoffset={1 - hook}
          opacity={hook > 0 ? 1 : 0}
        />
        <circle
          cx={10}
          cy={26}
          r={3.6}
          fill={C.blue}
          style={{ transformBox: "fill-box", transformOrigin: "center", transform: `scale(${dot})` }}
        />
      </svg>
    </span>
  );
};

/** The masthead's name: the icon, then the wordmark. */
export const Lockup: FC<{ size: number }> = ({ size }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: size * 0.4 }}>
    <Mark size={size * 1.45} />
    <Wordmark size={size} />
  </span>
);

export const PLACES = [
  "Preclinical only",
  "Trial registered",
  "Phase 1 trial",
  "Phase 2 trial",
  "Phase 3 trial",
  "Approved",
] as const;

/**
 * Six places on a line, one marked. It shows a position, not progress: the dot lands
 * in place and never travels along the path.
 */
export const StageTrack: FC<{
  place: number | null;
  landAt?: number;
  width: number;
  dot?: number;
  words?: boolean;
}> = ({ place, landAt, width, dot = 16, words = false }) => {
  const frame = useCurrentFrame();
  const landed = landAt === undefined ? 1 : arrive(frame, landAt, 18);
  const ring = landAt === undefined ? 1 : arrive(frame, landAt + 4, 24);
  const here = dot * 1.8;
  return (
    <div style={{ width }}>
      <div style={{ position: "relative", height: here }}>
        <div
          style={{
            position: "absolute",
            left: here / 2,
            right: here / 2,
            top: here / 2 - 1,
            height: 2,
            background: C.rule,
          }}
        />
        {PLACES.map((name, index) => {
          const marked = index === place && landed > 0;
          const size = marked ? dot + (here - dot) * landed : dot;
          return (
            <div
              key={name}
              style={{
                position: "absolute",
                left: (index * (width - here)) / 5,
                top: 0,
                width: here,
                height: here,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {marked && ring < 1 && (
                <div
                  style={{
                    position: "absolute",
                    width: here,
                    height: here,
                    borderRadius: "50%",
                    border: `2px solid ${C.blue}`,
                    transform: `scale(${1 + ring * 1.5})`,
                    opacity: (1 - ring) * 0.6,
                  }}
                />
              )}
              <div
                style={{
                  width: size,
                  height: size,
                  borderRadius: "50%",
                  background: marked ? C.blue : C.paper,
                  border: `${Math.max(2, dot / 7)}px solid ${marked ? C.blue : C.ring}`,
                }}
              />
            </div>
          );
        })}
      </div>
      {words && place !== null && (
        <div style={{ fontSize: 24, color: C.muted, marginTop: 10, opacity: landed, whiteSpace: "nowrap" }}>
          Place {place + 1} of 6, from preclinical to approved
        </div>
      )}
    </div>
  );
};

/** An outlet: a letter tile, its name, and the date it reported. */
export const Outlet: FC<{ name: string; date?: string; size?: number }> = ({ name, date, size = 28 }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: size * 0.45, fontSize: size, color: C.muted }}>
    <span
      style={{
        width: size * 1.15,
        height: size * 1.15,
        borderRadius: size * 0.26,
        background: C.tint,
        color: C.blue,
        fontWeight: 700,
        fontSize: size * 0.72,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flex: "none",
      }}
    >
      {name[0]}
    </span>
    <span style={{ color: C.ink, fontWeight: 600 }}>{name}</span>
    {date && <span style={{ whiteSpace: "nowrap" }}>· {date}</span>}
  </span>
);

/** The blue diamond: a record the status rests on. */
export const Basis: FC<{ size?: number }> = ({ size = 16 }) => (
  <span
    style={{
      display: "inline-block",
      width: size,
      height: size,
      background: C.blue,
      transform: "rotate(45deg)",
      flex: "none",
    }}
  />
);

/** The dashed note that can sit on a status: an overlay, never a status. */
export const Note: FC<{ size?: number; children: ReactNode }> = ({ size = 28, children }) => (
  <span
    style={{
      display: "inline-flex",
      alignItems: "center",
      fontSize: size,
      fontWeight: 700,
      border: `2.5px dashed ${C.blue}`,
      borderRadius: 10,
      padding: `${size * 0.18}px ${size * 0.55}px`,
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

/** A soft panel, as the digest on a claim page. */
export const Panel: FC<{ style?: CSSProperties; children: ReactNode }> = ({ style, children }) => (
  <div style={{ background: C.panel, borderRadius: 28, padding: "40px 48px", ...style }}>{children}</div>
);

/** A white box with a hairline: a table frame, a card, an answer on the blue band. */
export const Frame: FC<{ style?: CSSProperties; children: ReactNode }> = ({ style, children }) => (
  <div
    style={{
      background: C.paper,
      border: `2px solid ${C.rule}`,
      borderRadius: 24,
      ...style,
    }}
  >
    {children}
  </div>
);
