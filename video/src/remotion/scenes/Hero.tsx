// Opening: three reports as their outlets titled them, the years since, then the question.
import type { FC } from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Frame, Outlet, Wordmark } from "../brand/marks";
import { arrive, leave, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { GERM_SPLITTING, PULP_GERM, USAG1 } from "./claim-data";

const FROM = 2015;
const TO = 2027;
const NOW = 2026.87; // November 2026, when the registries were checked
const place = (year: number) => `${((year - FROM) / (TO - FROM)) * 100}%`;

/** The wordmark, centred: where the opening ends and the next scene begins. */
export const BrandMoment: FC<{ v: boolean; drawAt?: number; lift?: number; opacity?: number }> = ({
  v,
  drawAt,
  lift = 0,
  opacity = 1,
}) => (
  <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", opacity }}>
    <div style={{ transform: `translateY(${-lift}px)` }}>
      <Wordmark size={v ? 108 : 150} drawAt={drawAt} />
    </div>
  </AbsoluteFill>
);

export const Hero: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const reports = [
    { ...USAG1.article, cue: at("new drug"), year: 2021.25 },
    { ...GERM_SPLITTING.article, cue: at("multiplying"), year: 2015.96 },
    { ...PULP_GERM.article, cue: at("regrowing"), year: 2019.56 },
  ];
  const quiet = at("the follow-up");
  const later = at("so years later");
  const ask = at("what came of it");
  const dim = 1 - 0.5 * arrive(frame, quiet, 24);
  const since = arrive(frame, quiet, 45);

  return (
    <>
      <Stage v={v} style={{ opacity: leave(frame, ask - 14, 10) }}>
        <div style={{ display: "flex", flexDirection: "column", gap: v ? 28 : 20 }}>
          {reports.map((report, index) => (
            <Rise
              key={report.title}
              at={report.cue - 4}
              style={{ alignSelf: "flex-start", marginLeft: v ? 0 : index * 190, maxWidth: "100%" }}
            >
              <Frame style={{ padding: v ? "30px 36px" : "24px 40px", opacity: dim }}>
                <div style={{ fontSize: v ? 54 : 60, fontWeight: 700, lineHeight: 1.15 }}>
                  “{report.title}”
                </div>
                <div style={{ marginTop: 12 }}>
                  <Outlet name={report.outlet} date={report.date} size={v ? 26 : 28} />
                </div>
              </Frame>
            </Rise>
          ))}
        </div>

        {/* The years since: each report where it was made, then a dashed line to now. */}
        <div style={{ position: "relative", height: 120, marginTop: v ? 72 : 44 }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 40, height: 3, background: C.rule }} />
          <div
            style={{
              position: "absolute",
              left: place(2021.25),
              width: `${((NOW - 2021.25) / (TO - FROM)) * 100 * since}%`,
              top: 40,
              height: 0,
              borderTop: `3px dashed ${C.blue}`,
            }}
          />
          {Array.from({ length: TO - FROM }, (_, index) => FROM + index).map((year) => (
            <div
              key={year}
              style={{
                position: "absolute",
                left: place(year),
                top: 62,
                fontSize: 24,
                color: C.muted,
                transform: "translateX(-50%)",
                display: v && year % 2 === 0 ? "none" : "block",
              }}
            >
              {year}
            </div>
          ))}
          {reports.map((report) => (
            <div
              key={report.title}
              style={{
                position: "absolute",
                left: place(report.year),
                top: 41.5,
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: C.ink,
                transform: `translate(-50%, -50%) scale(${arrive(frame, report.cue, 14)})`,
              }}
            />
          ))}
          <div
            style={{
              position: "absolute",
              left: place(NOW),
              top: 41.5,
              width: 30,
              height: 30,
              borderRadius: "50%",
              background: C.paper,
              border: `4px solid ${C.blue}`,
              transform: `translate(-50%, -50%) scale(${arrive(frame, later, 16)})`,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: place(NOW),
              top: -14,
              fontSize: 26,
              fontWeight: 700,
              color: C.blue,
              transform: "translateX(-50%)",
              opacity: arrive(frame, later, 16),
            }}
          >
            Now
          </div>
        </div>
      </Stage>

      <BrandMoment v={v} drawAt={ask - 2} opacity={arrive(frame, ask - 6, 8)} />
    </>
  );
};
