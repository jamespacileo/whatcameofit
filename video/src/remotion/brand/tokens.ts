// The site's visual system (DESIGN.md), restated for video. One face, one accent,
// pale amber for "promised" and nothing else. No colour for any status.
import "@fontsource-variable/figtree";
import { continueRender, delayRender } from "remotion";

export const C = {
  paper: "#ffffff",
  ink: "#0f1f38",
  blue: "#14427f",
  muted: "#46566b",
  panel: "#f1f5fb",
  tint: "#e6eef8",
  tag: "#d6e2f2",
  rule: "#d9e2ee",
  ruleSoft: "#e9eff5",
  promise: "#fff7df",
  promiseRule: "#d9c88a",
  ring: "#7f90a3",
  footer: "#0b2545",
  // The accent, lifted to read on navy: the name's dot in the masthead.
  onNavy: "#8ec1f5",
} as const;

export const FACE = '"Figtree Variable", "Helvetica Neue", Arial, sans-serif';

// A frame is not drawn until the face has loaded, or the first frames fall back to Arial.
if (typeof document !== "undefined") {
  const handle = delayRender("Loading Figtree");
  Promise.all([
    document.fonts.load(`400 40px "Figtree Variable"`),
    document.fonts.load(`800 40px "Figtree Variable"`),
  ]).then(
    () => continueRender(handle),
    () => continueRender(handle),
  );
}

// What every scene is told: where a spoken phrase falls, how long it runs, which shape.
export type SceneProps = {
  /** Frame, counted from the scene's start, at which the narrator says this phrase. */
  at: (phrase: string) => number;
  dur: number;
  /** True for the tall 9:16 cut. */
  v: boolean;
};
