// The brand's drawn parts: the icon, the wordmark with its drawn question mark, the
// stage track, and the small pieces of a claim page that scenes share.
import type { CSSProperties, FC, ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { arrive } from "./motion";
import { C } from "./tokens";

// The mark's shapes, as in site/public/mark.svg: the glass as one outline (ring, handle,
// a small arc in each corner where they meet, the lens cut out) and the capsule's halves.
const GLASS =
  "M42.38 49.02A22 22 0 1 1 49.02 42.38A1.2 1.2 0 0 0 49.18 43.88L54.36 49.06A3.75 3.75 0 0 1 49.06 54.36L43.88 49.18A1.2 1.2 0 0 0 42.38 49.02ZM47 30.5A16.5 16.5 0 1 0 14 30.5A16.5 16.5 0 1 0 47 30.5Z";
const CORAL = "M29.7 23.75h-6.2a6.75 6.75 0 0 0 0 13.5h6.2z";
const BLUE = "M31.3 23.75h6.2a6.75 6.75 0 0 1 0 13.5h-6.2z";
/** The lens centre, on both axes of the mark's 64-unit grid. */
const LENS = 30.5;

/** site/public/mark-reverse.svg: for navy ground. No tile, the glass in white, the capsule in its own colours. */
export const MarkReverse: FC<{ size: number }> = ({ size }) => (
  <svg viewBox="8 8 48 48" width={size} height={size} style={{ flex: "none" }}>
    <path d={GLASS} fill="#ffffff" fillRule="evenodd" />
    <path d={CORAL} fill="#f28a62" />
    <path d={BLUE} fill="#1687da" />
  </svg>
);

/** site/public/mark.svg: the magnifier over the capsule. */
export const Mark: FC<{ size: number }> = ({ size }) => (
  <svg viewBox="0 0 64 64" width={size} height={size} style={{ flex: "none" }}>
    <rect width="64" height="64" rx="16" fill="#ffffff" />
    <path d={GLASS} fill="#16477d" fillRule="evenodd" />
    <path d={CORAL} fill="#f28a62" />
    <path d={BLUE} fill="#1687da" />
  </svg>
);

/**
 * The reverse mark put together part by part from frame `at`: the headline's half rises
 * into the lens, the glass is lowered over it, the record's half arrives beside it.
 * At rest it is MarkReverse.
 */
export const MarkReverseArriving: FC<{ size: number; at?: number }> = ({ size, at = 0 }) => {
  const frame = useCurrentFrame();
  const coral = arrive(frame, at, 15);
  const glass = arrive(frame, at + 14, 21);
  const blue = arrive(frame, at + 30, 18);
  // Lowered onto the capsule: from up and to the left, a little larger, about the lens centre.
  const lift = 1.5 * (1 - glass);
  const scale = 1 + 0.14 * (1 - glass);
  return (
    <svg viewBox="8 8 48 48" width={size} height={size} style={{ flex: "none", overflow: "visible" }}>
      <path
        d={GLASS}
        fill="#ffffff"
        fillRule="evenodd"
        opacity={glass}
        transform={`translate(${LENS - lift} ${LENS - lift}) scale(${scale}) translate(${-LENS} ${-LENS})`}
      />
      <path
        d={CORAL}
        fill="#f28a62"
        opacity={coral}
        transform={`translate(0 ${3 * (1 - coral)})`}
      />
      <path
        d={BLUE}
        fill="#1687da"
        opacity={blue}
        transform={`translate(${3 * (1 - blue)} 0)`}
      />
    </svg>
  );
};

/** Fades in and rises a little, over 15 frames from `at`. Nothing when `at` is not given. */
const wordArrival = (frame: number, at: number | undefined): CSSProperties => {
  if (at === undefined) return {};
  const shown = arrive(frame, at, 15);
  return { opacity: shown, transform: `translateY(${(1 - shown) * 0.05}em)` };
};

/**
 * "What came of it?": a light lead, a heavy tail, and a question mark that is drawn so
 * its dot can be the blue marker. With `drawAt`, the hook is drawn and the dot lands.
 * With `leadAt` and `tailAt`, "What came" and "of it" each fade in and rise into place.
 */
export const Wordmark: FC<{
  size: number;
  drawAt?: number;
  leadAt?: number;
  tailAt?: number;
  color?: string;
  dotColor?: string;
}> = ({ size, drawAt, leadAt, tailAt, color = C.ink, dotColor = C.blue }) => {
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
      <span style={{ fontWeight: 400, ...wordArrival(frame, leadAt) }}>What came</span>
      <span style={{ fontWeight: 800, marginLeft: "0.26em", ...wordArrival(frame, tailAt) }}>of it</span>
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
          fill={dotColor}
          style={{ transformBox: "fill-box", transformOrigin: "center", transform: `scale(${dot})` }}
        />
      </svg>
    </span>
  );
};

/** The name with its icon. `reverse` is the masthead's: white on navy, the dot in the lifted blue. */
export const Lockup: FC<{ size: number; reverse?: boolean }> = ({ size, reverse = false }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: size * 0.45 }}>
    {reverse ? <MarkReverse size={size * 1.4} /> : <Mark size={size * 1.45} />}
    <Wordmark size={size} color={reverse ? C.paper : C.ink} dotColor={reverse ? C.onNavy : C.blue} />
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
