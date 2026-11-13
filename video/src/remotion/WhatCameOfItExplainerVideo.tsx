// The explainer for the site and its browser extension. Seven scenes, each timed by
// the narration's words; drawn at 1920 by 1080 (or 1080 by 1920) and scaled to 4K.
import type { FC } from "react";
import { AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Lockup } from "./brand/marks";
import { SceneFade } from "./brand/motion";
import { CaptionBar, cueFinder, type Captions, type Timing } from "./brand/narration";
import { C, FACE, type SceneProps } from "./brand/tokens";
import { Claim } from "./scenes/Claim";
import { Extension } from "./scenes/Extension";
import { Hero } from "./scenes/Hero";
import { Lookup } from "./scenes/Lookup";
import { Outro } from "./scenes/Outro";
import { Records } from "./scenes/Records";
import { Rules } from "./scenes/Rules";

export type ExplainerProps = {
  orientation: "horizontal" | "vertical";
  /** Captions drawn into the picture. Turn off where the player shows the .srt file. */
  showCaptions: boolean;
  timing: Timing | null;
  captions: Captions | null;
};

const SCENES: Record<string, FC<SceneProps>> = {
  hero: Hero,
  claim: Claim,
  records: Records,
  rules: Rules,
  lookup: Lookup,
  extension: Extension,
  outro: Outro,
};

/** The masthead holds still while the scenes change under it. */
const Masthead: FC<{ v: boolean; from: number; to: number }> = ({ v, from, to }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [from, from + 10, to - 8, to], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        height: v ? 150 : 110,
        padding: v ? "40px 60px 0" : "0 120px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: C.paper,
        borderBottom: `2px solid ${C.rule}`,
        opacity,
      }}
    >
      <Lockup size={v ? 34 : 32} />
      <span style={{ fontSize: 24, color: C.muted }}>Not medical advice</span>
    </div>
  );
};

export const Video: FC<ExplainerProps> = ({ orientation, showCaptions, timing, captions }) => {
  const { width, fps } = useVideoConfig();
  if (!timing || !captions) return null;
  const v = orientation === "vertical";
  const [w, h] = v ? [1080, 1920] : [1920, 1080];
  const section = (name: string) => timing.sections.find((s) => s.name === name)!;
  const claim = section("claim");

  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <div
        style={{
          position: "relative",
          width: w,
          height: h,
          transform: `scale(${width / w})`,
          transformOrigin: "top left",
          fontFamily: FACE,
          fontVariantNumeric: "tabular-nums lining-nums",
          color: C.ink,
          overflow: "hidden",
        }}
      >
        {timing.sections.map((s) => {
          const Scene = SCENES[s.name];
          return (
            <Sequence key={s.name} name={s.name} from={s.start_frame} durationInFrames={s.duration_frames}>
              {/* The name carries over from the opening into the next scene, so no fade between them. */}
              <SceneFade dur={s.duration_frames} fadeIn={s.name !== "claim"} fadeOut={s.name !== "hero" && s.name !== "outro"}>
                <Scene at={cueFinder(captions, s, fps)} dur={s.duration_frames} v={v} />
              </SceneFade>
            </Sequence>
          );
        })}
        <Masthead
          v={v}
          from={claim.start_frame + cueFinder(captions, claim, fps)("each claim") - 8}
          to={section("outro").start_frame}
        />
        {showCaptions && <CaptionBar captions={captions} v={v} />}
      </div>
      <Audio src={staticFile("podcast_audio.wav")} />
    </AbsoluteFill>
  );
};
