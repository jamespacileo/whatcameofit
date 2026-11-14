// How a status is set, and what "no signal" says and does not say.
import { Ban } from "lucide-react";
import type { FC } from "react";
import { useCurrentFrame } from "remotion";
import { Frame, Note, Outlet, Panel, StageTrack } from "../brand/marks";
import { arrive, leave, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { CHECKED, GERM_SPLITTING as CLAIM, SOURCES, USAG1 } from "./claim-data";

/** An arrow from one step to the next, drawn as it arrives. */
const Arrow: FC<{ at: number; v: boolean }> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const drawn = arrive(frame, at, 16);
  return (
    <svg
      viewBox="0 0 70 40"
      style={{ width: 70, height: 40, alignSelf: "center", justifySelf: "center", transform: v ? "rotate(90deg)" : "none" }}
    >
      <path d={`M4 20H${4 + 52 * drawn}`} stroke={C.muted} strokeWidth={4} strokeLinecap="round" />
      <path
        d="M48 8 62 20 48 32"
        fill="none"
        stroke={C.muted}
        strokeWidth={4}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity={arrive(frame, at + 10, 8)}
      />
    </svg>
  );
};

const Nobody: FC<{ at: number; children: string }> = ({ at, children }) => (
  <Rise at={at}>
    <span style={{ display: "inline-flex", alignItems: "center", gap: 16, fontSize: 40, fontWeight: 700 }}>
      <Ban size={40} strokeWidth={2} color={C.muted} />
      {children}
    </span>
  </Rise>
);

export const Rules: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const second = at("when nothing new") - 10;
  const rules = at("fixed rules") - 4;
  const records = at("from public registry") - 4;
  const years = Array.from({ length: CLAIM.lastYear - CLAIM.firstYear + 1 }, (_, n) => CLAIM.firstYear + n);
  const perYear = (at("the page says") - at("when nothing new")) / (years.length - 1);

  return (
    <>
      <Stage v={v} style={{ opacity: leave(frame, second - 2) }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: v ? "1fr" : "1fr 70px 1fr 70px 1fr",
            gridAutoRows: v ? "auto" : "1fr",
            gap: v ? 14 : 0,
          }}
        >
          <Rise at={records} style={{ display: "flex" }}>
            <Frame style={{ padding: "30px 36px", flex: 1 }}>
              <div style={{ fontSize: 36, fontWeight: 700, lineHeight: 1.2 }}>Public registry records</div>
              <div style={{ fontSize: 28, color: C.muted, marginTop: 12, lineHeight: 1.5 }}>
                {SOURCES.map((source) => (
                  <div key={source}>{source}</div>
                ))}
              </div>
            </Frame>
          </Rise>
          <Arrow at={records + 8} v={v} />
          <Rise at={rules} style={{ display: "flex" }}>
            <Panel style={{ padding: "30px 36px", flex: 1 }}>
              <div style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.2 }}>Fixed rules</div>
              <div style={{ fontSize: 28, color: C.muted, marginTop: 12, lineHeight: 1.4 }}>
                Applied in order. The first one that fits sets the status.
              </div>
            </Panel>
          </Rise>
          <Arrow at={rules + 8} v={v} />
          <Rise at={4} style={{ display: "flex" }}>
            <Frame style={{ padding: "30px 36px", flex: 1 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.muted }}>Status</div>
              <div style={{ fontSize: 44, fontWeight: 700, color: C.blue, lineHeight: 1.2, marginTop: 4 }}>
                {USAG1.status}
              </div>
              <div style={{ marginTop: 22 }}>
                <StageTrack place={USAG1.place} width={v ? 420 : 340} dot={14} />
              </div>
            </Frame>
          </Rise>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: v ? "column" : "row",
            gap: v ? 20 : 72,
            marginTop: v ? 56 : 60,
          }}
        >
          <Nobody at={at("no editor") - 4}>No editor decides it.</Nobody>
          <Nobody at={at("and no ai model") - 4}>No AI model decides it.</Nobody>
        </div>
        <Rise at={at("and no ai model") + 26} style={{ marginTop: 22 }}>
          <div style={{ fontSize: 30, color: C.muted }}>Every status lists the records that produced it.</div>
        </Rise>
      </Stage>

      <Stage v={v}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: v ? "1fr" : "1fr 1fr",
            gap: v ? 48 : 72,
            alignItems: "center",
          }}
        >
          <Rise at={second + 6}>
            <Frame style={{ padding: v ? "36px 40px" : "36px 44px" }}>
              <Outlet name={CLAIM.article.outlet} date={CLAIM.article.date} />
              <div style={{ fontSize: v ? 60 : 64, fontWeight: 700, lineHeight: 1.15, marginTop: 10 }}>
                “{CLAIM.article.title}”
              </div>
              <div style={{ borderTop: `2px solid ${C.rule}`, margin: "24px 0 20px" }} />
              <div style={{ fontSize: 24, fontWeight: 700, color: C.muted }}>Where it stands</div>
              <div style={{ fontSize: 52, fontWeight: 700, color: C.blue, lineHeight: 1.2 }}>{CLAIM.status}</div>
              <div style={{ fontSize: 30, color: C.muted, marginTop: 2 }}>{CLAIM.gloss}</div>
              <div style={{ marginTop: 20 }}>
                <StageTrack place={CLAIM.place} width={v ? 480 : 400} />
              </div>
              <Rise at={at("no signal") - 2} dy={0} style={{ marginTop: 22 }}>
                <Note>{CLAIM.note}</Note>
              </Rise>
            </Frame>
          </Rise>

          <div>
            <Rise at={second + 12}>
              <div style={{ fontSize: 26, fontWeight: 700, color: C.muted }}>New records, by year</div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
                {years.map((year, index) => {
                  const shown = index === 0 ? 1 : arrive(frame, at("when nothing new") + index * perYear, 10);
                  return (
                    <div key={year} style={{ textAlign: "center", opacity: shown, width: 60 }}>
                      <div
                        style={{
                          width: 30,
                          height: 30,
                          margin: "0 auto",
                          borderRadius: "50%",
                          background: index === 0 ? C.ink : C.paper,
                          border: `3px solid ${index === 0 ? C.ink : C.ring}`,
                        }}
                      />
                      <div style={{ fontSize: 24, color: index === 0 ? C.ink : C.muted, marginTop: 8, fontWeight: index === 0 ? 700 : 400 }}>
                        {v ? `’${String(year).slice(2)}` : year}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{ fontSize: 30, fontWeight: 600, marginTop: 24, lineHeight: 1.3 }}>{CLAIM.meaning}</div>
              <div style={{ fontSize: 24, color: C.muted, marginTop: 6 }}>{CHECKED}</div>
            </Rise>

            <div style={{ borderTop: `2px solid ${C.rule}`, margin: "30px 0 26px", opacity: arrive(frame, at("that describes") - 2, 12) }} />
            <Rise at={at("that describes") - 2}>
              <div style={{ fontSize: v ? 42 : 44, fontWeight: 700, lineHeight: 1.25 }}>It describes the records.</div>
            </Rise>
            <Rise at={at("it is not") - 2}>
              <div style={{ fontSize: v ? 42 : 44, fontWeight: 700, lineHeight: 1.25 }}>
                It is not a verdict on the treatment.
              </div>
            </Rise>
            <Rise at={at("it is not") + 22} style={{ marginTop: 14 }}>
              <div style={{ fontSize: 26, color: C.muted, lineHeight: 1.35 }}>
                It says nothing about work that has not been published or registered.
              </div>
            </Rise>
          </div>
        </div>
      </Stage>
    </>
  );
};
