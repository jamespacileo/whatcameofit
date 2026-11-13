// Motion as the site has it: things arrive on one easing and land in place.
// Nothing loops and nothing flashes.
import type { CSSProperties, FC, ReactNode } from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";

const EASE = Easing.bezier(0.16, 1, 0.3, 1);
const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** 0 to 1 from `start`, over `frames`, on the site's arrival easing. */
export const arrive = (frame: number, start: number, frames = 18): number =>
  interpolate(frame, [start, start + frames], [0, 1], { ...CLAMP, easing: EASE });

/** 1 to 0 from `start`: leaving is quicker than arriving. */
export const leave = (frame: number, start: number, frames = 8): number =>
  interpolate(frame, [start, start + frames], [1, 0], CLAMP);

/** Fades in and rises a little into place at frame `at`; gone again at `until`. */
export const Rise: FC<{
  at: number;
  until?: number;
  dy?: number;
  style?: CSSProperties;
  children: ReactNode;
}> = ({ at, until, dy = 18, style, children }) => {
  const frame = useCurrentFrame();
  const shown = arrive(frame, at);
  const kept = until === undefined ? 1 : leave(frame, until);
  return (
    <div
      style={{ opacity: shown * kept, transform: `translateY(${(1 - shown) * dy}px)`, ...style }}
    >
      {children}
    </div>
  );
};

/** A scene's content box, clear of the masthead above and the captions below. */
export const Stage: FC<{ v: boolean; style?: CSSProperties; children: ReactNode }> = ({
  v,
  style,
  children,
}) => (
  <AbsoluteFill
    style={{
      padding: v ? "230px 60px 480px" : "140px 120px 170px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      ...style,
    }}
  >
    {children}
  </AbsoluteFill>
);

/** Cross-fade between scenes: a scene's content fades in, and out before the next. */
export const SceneFade: FC<{
  dur: number;
  fadeIn?: boolean;
  fadeOut?: boolean;
  children: ReactNode;
}> = ({ dur, fadeIn = true, fadeOut = true, children }) => {
  const frame = useCurrentFrame();
  const opacity =
    (fadeIn ? interpolate(frame, [0, 8], [0, 1], CLAMP) : 1) *
    (fadeOut ? interpolate(frame, [dur - 7, dur - 1], [1, 0], CLAMP) : 1);
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
