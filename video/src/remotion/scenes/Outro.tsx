// Closing: what the site does not do, then the name and where to find it.
import type { FC } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Mark, Wordmark } from "../brand/marks";
import { arrive, leave, Rise } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { HOST, NOTICES, SOURCES } from "./claim-data";

export const Outro: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const name = at("what came of it") - 8;
  const big = { fontSize: v ? 76 : 88, fontWeight: 700, lineHeight: 1.2, textAlign: "center" } as const;

  return (
    <>
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: v ? "0 60px 260px" : "0 120px 120px",
          opacity: leave(frame, name - 6),
        }}
      >
        <Rise at={at("no medical advice") - 4}>
          <div style={big}>No medical advice.</div>
        </Rise>
        <Rise at={at("no verdicts") - 4}>
          <div style={big}>No verdicts.</div>
        </Rise>
        <Rise at={at("only what") - 4} style={{ marginTop: 28 }}>
          <div style={{ ...big, fontSize: v ? 52 : 60, fontWeight: 500, color: C.muted }}>
            Only what the records show, and when.
          </div>
        </Rise>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: v ? "0 60px 260px" : "0 120px 110px",
          opacity: arrive(frame, name, 10),
        }}
      >
        <Mark size={v ? 150 : 170} />
        <div style={{ marginTop: 26 }}>
          <Wordmark size={v ? 104 : 140} drawAt={name + 4} />
        </div>
        <Rise at={at("find out") + 4} style={{ marginTop: 30 }}>
          <div style={{ fontSize: v ? 60 : 68, fontWeight: 700, color: C.blue }}>{HOST}</div>
        </Rise>
        <Rise at={at("find out") + 20} style={{ marginTop: 44 }}>
          <div style={{ fontSize: v ? 26 : 26, color: C.muted, textAlign: "center", lineHeight: 1.45, maxWidth: 1300 }}>
            {NOTICES.map((notice) => (
              <div key={notice}>{notice}</div>
            ))}
            Data: {SOURCES.join(", ")}
          </div>
        </Rise>
      </AbsoluteFill>
    </>
  );
};
