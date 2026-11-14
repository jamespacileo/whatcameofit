// The logo sting: the site's own card (DESIGN.md), put together once in four seconds,
// for the end of a video and for a clip in a post. Silent. Nothing loops.
// The headline's half, the glass, the record's half, the name, the question, the dot.
import type { FC } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { MarkReverseArriving, Wordmark } from "./brand/marks";
import { arrive } from "./brand/motion";
import { C, FACE } from "./brand/tokens";
import { HOST } from "./scenes/claim-data";

export type StingProps = { orientation: "horizontal" | "square" | "vertical" };

// Frames at 30 fps. The mark's own parts arrive from MARK_AT (see MarkReverseArriving).
const MARK_AT = 0;
const LEAD_AT = 39;
const TAIL_AT = 44;
const HOOK_AT = 53; // the dot lands 18 frames after the hook starts
const TAGLINE_AT = 78;

// Sizes in pixels. Wide: the mark beside the name, as the card has it. Square and tall:
// the mark above the name, centred.
const LAYOUT = {
  horizontal: { pad: 120, mark: 310, gap: 86, name: 156, tagline: 62, foot: 38 },
  square: { pad: 84, mark: 250, gap: 44, name: 104, tagline: 44, foot: 30 },
  vertical: { pad: 84, mark: 320, gap: 56, name: 112, tagline: 46, foot: 32 },
} as const;

export const Sting: FC<StingProps> = ({ orientation }) => {
  const frame = useCurrentFrame();
  const size = LAYOUT[orientation];
  const wide = orientation === "horizontal";
  const tagline = arrive(frame, TAGLINE_AT, 18);

  return (
    <AbsoluteFill
      style={{
        background: C.footer,
        color: C.paper,
        fontFamily: FACE,
        padding: size.pad,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: wide ? "row" : "column",
          alignItems: "center",
          justifyContent: wide ? "flex-start" : "center",
          gap: size.gap,
        }}
      >
        <MarkReverseArriving size={size.mark} at={MARK_AT} />
        <div style={{ display: "flex", flexDirection: "column", alignItems: wide ? "flex-start" : "center" }}>
          <Wordmark
            size={size.name}
            leadAt={LEAD_AT}
            tailAt={TAIL_AT}
            drawAt={HOOK_AT}
            color={C.paper}
            dotColor={C.onNavy}
          />
          <div
            style={{
              fontSize: size.tagline,
              lineHeight: 1.25,
              color: C.pale,
              marginTop: size.tagline * 0.5,
              opacity: tagline,
              whiteSpace: "nowrap",
            }}
          >
            What happened after the headline?
          </div>
        </div>
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: size.foot,
          fontSize: size.foot,
          lineHeight: 1.25,
          color: C.pale,
          whiteSpace: "nowrap",
        }}
      >
        <span>{HOST}</span>
        <span>Not medical advice</span>
      </div>
    </AbsoluteFill>
  );
};
