// The home page's main box: paste a report's link, get the tracked claim's status.
import { Lock } from "lucide-react";
import type { FC } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { Frame, StageTrack } from "../brand/marks";
import { arrive, leave, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { USAG1 } from "./claim-data";

export const Lookup: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const paste = at("paste") + 6;
  const press = at("if the claim") - 6;
  const answer = at("the answer comes") - 8;
  const pasted = frame >= paste;
  const pressed = interpolate(frame, [press, press + 3, press + 9], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <>
      {/* The opening band: pale, with ink on it, under the white masthead. */}
      <AbsoluteFill style={{ top: v ? 150 : 111, background: C.panel }} />
      <Stage v={v}>
        <Rise at={2}>
          <div style={{ fontSize: v ? 60 : 68, fontWeight: 700, lineHeight: 1.12 }}>
            What happened to that breakthrough?
          </div>
          <div style={{ fontSize: v ? 28 : 30, color: C.muted, marginTop: 16 }}>
            Paste a link to an article, or search by treatment or condition
          </div>
        </Rise>

        <Rise at={8} style={{ marginTop: 16 }}>
          <div style={{ display: "flex", flexDirection: v ? "column" : "row", gap: 16 }}>
            <div
              style={{
                flex: 1,
                height: 100,
                flexShrink: 0,
                flexBasis: v ? 100 : 0,
                background: C.paper,
                border: `3px solid ${C.blue}`,
                borderRadius: 18,
                padding: "0 30px",
                display: "flex",
                alignItems: "center",
                fontSize: v ? 34 : 36,
                whiteSpace: "nowrap",
                overflow: "hidden",
              }}
            >
              {pasted ? (
                <span
                  style={{
                    borderRadius: 6,
                    background: `rgba(214, 226, 242, ${leave(frame, paste + 6, 16)})`,
                    padding: "2px 4px",
                    marginLeft: -4,
                  }}
                >
                  https://www.{USAG1.article.address}
                </span>
              ) : (
                <span style={{ color: C.muted }}>https://… or tooth regrowth</span>
              )}
            </div>
            <div
              style={{
                height: 100,
                flexShrink: 0,
                padding: "0 48px",
                borderRadius: 18,
                background: C.blue,
                color: C.paper,
                fontSize: 36,
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transform: `translateY(${pressed * 3}px)`,
              }}
            >
              Look up
            </div>
          </div>
        </Rise>

        <Rise at={answer} style={{ marginTop: 28 }}>
          <Frame
            style={{
              padding: v ? "36px 40px" : "30px 40px",
              display: "grid",
              gridTemplateColumns: v ? "1fr" : "auto 1fr",
              gap: v ? 28 : 64,
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontSize: v ? 56 : 50, fontWeight: 700, color: C.blue, lineHeight: 1.15 }}>
                {USAG1.status}
              </div>
              <div style={{ marginTop: 18 }}>
                <StageTrack place={USAG1.place} landAt={answer + 8} width={v ? 520 : 480} words />
              </div>
            </div>
            <div>
              <div style={{ fontSize: v ? 36 : 36, fontWeight: 700, lineHeight: 1.25 }}>{USAG1.headline}</div>
              <div style={{ fontSize: 28, color: C.muted, marginTop: 8, lineHeight: 1.35 }}>{USAG1.meaning}</div>
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 600,
                  color: C.blue,
                  marginTop: 10,
                  textDecoration: "underline",
                  textUnderlineOffset: 5,
                }}
              >
                See the records
              </div>
            </div>
          </Frame>
        </Rise>

        <Rise at={at("the link is compared") - 4} style={{ marginTop: 26 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: v ? 34 : 34, fontWeight: 600 }}>
            <Lock size={34} strokeWidth={2} color={C.muted} />
            Compared inside your browser. Sent nowhere.
          </div>
        </Rise>
      </Stage>
    </>
  );
};
