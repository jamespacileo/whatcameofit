// Cover image for the video: the icon, the name, the question. One layout, sized by its frame.
import type { FC } from "react";
import { AbsoluteFill, useVideoConfig } from "remotion";
import { Mark, Wordmark } from "./brand/marks";
import { C, FACE } from "./brand/tokens";
import { HOST } from "./scenes/claim-data";

export const Thumbnail: FC = () => {
  const { width, height } = useVideoConfig();
  const tall = height > width;
  // The name is the largest thing on the cover: as wide as the frame allows.
  const name = Math.min(width / (tall ? 7.6 : 8.4), 190);
  return (
    <AbsoluteFill
      style={{
        background: C.paper,
        fontFamily: FACE,
        color: C.ink,
        alignItems: "center",
        justifyContent: "center",
        padding: name * 0.5,
      }}
    >
      <AbsoluteFill style={{ top: "auto", height: "34%", background: C.panel, borderTop: `3px solid ${C.rule}` }} />
      <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <Mark size={name * 1.75} />
        <div style={{ marginTop: name * 0.22 }}>
          <Wordmark size={name} />
        </div>
        <div
          style={{
            fontSize: name * 0.44,
            fontWeight: 600,
            color: C.blue,
            marginTop: name * 0.42,
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          What happened after the headline?
        </div>
        <div style={{ fontSize: name * 0.26, color: C.muted, marginTop: name * 0.3 }}>
          {HOST} · Not medical advice
        </div>
      </div>
    </AbsoluteFill>
  );
};
