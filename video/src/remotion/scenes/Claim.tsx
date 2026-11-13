// What the site is, then a claim page: one treatment for one condition, and at the
// top where it stands now.
import type { FC, ReactNode } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Panel, StageTrack } from "../brand/marks";
import { arrive, leave, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { USAG1 } from "./claim-data";
import { BrandMoment } from "./Hero";

/** A fact under the headline: a small grey label over its value, tinted while spoken of. */
const Fact: FC<{ label: string; lit: number; v: boolean; children: ReactNode }> = ({
  label,
  lit,
  v,
  children,
}) => (
  <div style={{ position: "relative", padding: "14px 20px", marginLeft: -20 }}>
    <div
      style={{ position: "absolute", inset: 0, borderRadius: 16, background: C.tag, opacity: lit }}
    />
    <div style={{ position: "relative" }}>
      <div style={{ fontSize: 24, color: C.muted }}>{label}</div>
      <div style={{ fontSize: v ? 32 : 34, fontWeight: 600, lineHeight: 1.25 }}>{children}</div>
    </div>
  </div>
);

export const Claim: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const page = at("each claim") - 8;
  const top = at("at the top");
  const reached = at("has reached");
  const between = (from: number, to: number) => arrive(frame, from, 10) * leave(frame, to, 10);

  return (
    <>
      {/* The name stays where the opening left it, and says what it is. */}
      <BrandMoment v={v} lift={arrive(frame, 4, 24) * (v ? 150 : 110)} opacity={leave(frame, page - 8)} />
      <AbsoluteFill
        style={{ alignItems: "center", justifyContent: "center", opacity: leave(frame, page - 8) }}
      >
        <Rise at={12} style={{ marginTop: v ? 200 : 150, padding: "0 60px" }}>
          <div
            style={{
              fontSize: v ? 50 : 56,
              fontWeight: 600,
              lineHeight: 1.25,
              textAlign: "center",
              maxWidth: 1300,
            }}
          >
            A public record of what followed reported medical breakthroughs.
          </div>
        </Rise>
      </AbsoluteFill>

      <Stage v={v}>
        <Rise at={page}>
          <span
            style={{
              display: "inline-block",
              fontSize: 26,
              fontWeight: 600,
              color: C.blue,
              background: C.tint,
              borderRadius: 999,
              padding: "6px 24px",
            }}
          >
            {USAG1.topic}
          </span>
          <div style={{ fontSize: v ? 56 : 64, fontWeight: 700, lineHeight: 1.12, marginTop: 18 }}>
            {USAG1.headline}
          </div>
          <div style={{ fontSize: v ? 28 : 30, color: C.muted, marginTop: 12 }}>
            A record of what followed this reported breakthrough.
          </div>
        </Rise>

        <Rise at={page + 8} style={{ marginTop: v ? 36 : 22 }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: v ? "1fr 1fr" : "1.25fr 1.25fr 1fr 1fr",
              gap: v ? "12px 36px" : "0 44px",
              paddingLeft: 20,
            }}
          >
            <Fact label="Intervention" lit={between(at("one treatment"), top)} v={v}>
              {USAG1.intervention}
            </Fact>
            <Fact label="Claimed for" lit={between(at("for one condition"), top)} v={v}>
              {USAG1.indication}
            </Fact>
            <Fact label="First reported" lit={between(at("this one"), reached)} v={v}>
              {USAG1.firstReported}
            </Fact>
            <Fact label="Evidence when first reported" lit={0} v={v}>
              {USAG1.evidenceAtFirst}
            </Fact>
          </div>
        </Rise>

        <Rise at={top - 6} style={{ marginTop: v ? 40 : 26 }}>
          <Panel
            style={{
              display: "grid",
              gridTemplateColumns: v ? "1fr" : "1fr 1.25fr",
              gap: v ? 36 : 64,
              alignItems: "center",
              padding: v ? "44px 44px" : "36px 48px",
            }}
          >
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.muted }}>Where it stands</div>
              <Rise at={reached} dy={0}>
                <div style={{ fontSize: v ? 64 : 60, fontWeight: 700, lineHeight: 1.15, color: C.blue }}>
                  {USAG1.status}
                </div>
              </Rise>
              <Rise at={at("an early trial")} dy={0}>
                <div style={{ fontSize: 32, color: C.muted, marginTop: 4 }}>{USAG1.gloss}</div>
              </Rise>
              <div style={{ marginTop: 20 }}>
                <StageTrack place={USAG1.place} landAt={reached + 6} width={v ? 520 : 440} words />
              </div>
            </div>
            <Rise at={reached + 14}>
              <div style={{ fontSize: v ? 36 : 38, fontWeight: 600, lineHeight: 1.3 }}>{USAG1.meaning}</div>
              <div style={{ fontSize: 28, color: C.muted, marginTop: 16 }}>
                Latest record <strong style={{ color: C.ink }}>{USAG1.latestRecord}</strong>
              </div>
            </Rise>
          </Panel>
        </Rise>
      </Stage>
    </>
  );
};
