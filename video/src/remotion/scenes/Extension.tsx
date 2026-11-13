// The browser extension: the tracked claim's status on the article itself, and for any
// other article a live registry search, marked automatic and unreviewed.
//
// The tracked popup shows a real claim. The search result is a drawing of the layout:
// its record titles are bars, because the video names no record it did not look up.
import { Activity, ChevronDown, FlaskConical, Search } from "lucide-react";
import type { CSSProperties, FC, ReactNode } from "react";
import { useCurrentFrame } from "remotion";
import { Frame, Lockup, Mark, Outlet, StageTrack } from "../brand/marks";
import { arrive, leave, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { USAG1 } from "./claim-data";

/** A grey bar where text would be. Article text is never shown, here or on the site. */
const Bar: FC<{ w: number | string; h?: number; style?: CSSProperties }> = ({ w, h = 18, style }) => (
  <div style={{ width: w, height: h, borderRadius: h / 2, background: C.ruleSoft, ...style }} />
);

const Step: FC<{ at: number; label: string; children: ReactNode }> = ({ at, label, children }) => (
  <Rise at={at} style={{ marginTop: 34 }}>
    <div style={{ fontSize: 26, fontWeight: 700, color: C.blue }}>{label}</div>
    <div style={{ fontSize: 32, lineHeight: 1.3, marginTop: 4 }}>{children}</div>
  </Rise>
);

/** One candidate record of a registry search: a white card with its match confidence. */
const Candidate: FC<{ match: string; lit: number; bars: [string, string] }> = ({ match, lit, bars }) => (
  <div style={{ border: `2px solid ${C.rule}`, borderRadius: 16, padding: "16px 22px", marginTop: 14 }}>
    <Bar w={bars[0]} h={18} style={{ background: C.rule }} />
    <Bar w={bars[1]} h={18} style={{ background: C.rule, marginTop: 10 }} />
    <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
      {[FlaskConical, Activity].map((Icon, index) => (
        <span
          key={index}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            border: `2px solid ${C.rule}`,
            borderRadius: 999,
            padding: "6px 14px",
            color: C.muted,
          }}
        >
          <Icon size={22} strokeWidth={1.9} />
          <Bar w={index ? 96 : 64} h={14} />
        </span>
      ))}
    </div>
    <div
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        marginTop: 10,
        marginLeft: -10,
        padding: "4px 10px",
        borderRadius: 10,
        fontSize: 26,
        fontWeight: 700,
        color: C.blue,
        background: `rgba(214, 226, 242, ${lit})`,
      }}
    >
      {match}
      <ChevronDown size={26} strokeWidth={2.2} />
    </div>
  </div>
);

export const Extension: FC<SceneProps> = ({ at, v }) => {
  const frame = useCurrentFrame();
  const open = at("open it");
  const popup = open + 14;
  const other = at("if the article") - 6;
  const tracked = leave(frame, other, 8);
  const untracked = arrive(frame, other + 6, 12);
  const marked = arrive(frame, at("those results"), 12);
  const scored = arrive(frame, at("and every match"), 12);
  const ring = arrive(frame, open, 26);
  const popupWidth = v ? 600 : 560;

  return (
    <Stage v={v}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: v ? "1fr" : "500px 1fr",
          gap: v ? 36 : 72,
          alignItems: "center",
        }}
      >
        <div>
          <Rise at={2}>
            <div style={{ fontSize: v ? 60 : 72, fontWeight: 700, lineHeight: 1.08 }}>Browser extension</div>
          </Rise>
          <Rise at={at("for chrome") - 4}>
            <div style={{ fontSize: 34, color: C.muted, marginTop: 10 }}>Chrome and Safari</div>
          </Rise>
          {!v && (
            <>
              <Step at={open - 4} label="On a tracked article">
                The claim’s status, where you are reading.
              </Step>
              <Step at={other} label="On any other article">
                A live search of the trial registries.
                <div style={{ fontSize: 24, color: C.muted, marginTop: 8 }}>
                  Reads the report with OpenAI. Off until you allow it.
                </div>
              </Step>
            </>
          )}
        </div>

        <Rise at={6}>
          <div style={{ position: "relative", height: v ? 800 : 760 }}>
            {/* A browser window, with the article as bars. */}
            <Frame style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
              <div
                style={{
                  height: 88,
                  background: C.panel,
                  borderBottom: `2px solid ${C.rule}`,
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "0 26px",
                }}
              >
                {[0, 1, 2].map((dot) => (
                  <div key={dot} style={{ width: 18, height: 18, borderRadius: "50%", background: C.tag }} />
                ))}
                <div
                  style={{
                    flex: 1,
                    marginLeft: 14,
                    height: 52,
                    borderRadius: 26,
                    background: C.paper,
                    border: `2px solid ${C.rule}`,
                    display: "flex",
                    alignItems: "center",
                    padding: "0 24px",
                    fontSize: 24,
                    color: C.muted,
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    position: "relative",
                  }}
                >
                  <span style={{ opacity: tracked }}>{USAG1.article.address}</span>
                  <Bar w={300} h={16} style={{ position: "absolute", left: 24, opacity: untracked }} />
                </div>
                <div style={{ position: "relative", width: 56, height: 56, marginLeft: 6 }}>
                  <div
                    style={{
                      position: "absolute",
                      inset: -4,
                      borderRadius: 18,
                      border: `3px solid ${C.blue}`,
                      opacity: ring > 0 && ring < 1 ? 1 - ring : 0,
                      transform: `scale(${1 + ring * 0.5})`,
                    }}
                  />
                  <div style={{ borderRadius: 14, border: `2px solid ${C.rule}`, overflow: "hidden", width: 56, height: 56 }}>
                    <Mark size={52} />
                  </div>
                </div>
              </div>
              <div style={{ position: "relative", padding: v ? "40px 40px" : "44px 52px" }}>
                <div style={{ opacity: tracked }}>
                  <Outlet name={USAG1.article.outlet} date={v ? undefined : USAG1.article.date} size={26} />
                  <div style={{ fontSize: v ? 38 : 48, fontWeight: 700, lineHeight: 1.15, marginTop: 16, maxWidth: v ? 270 : 440 }}>
                    {USAG1.article.title}
                  </div>
                </div>
                <div style={{ position: "absolute", top: v ? 40 : 44, left: v ? 40 : 52, opacity: untracked }}>
                  <Bar w={v ? 200 : 260} h={22} />
                  <Bar w={v ? 270 : 400} h={40} style={{ marginTop: 26, background: C.rule }} />
                  <Bar w={v ? 220 : 320} h={40} style={{ marginTop: 14, background: C.rule }} />
                </div>
                <div style={{ marginTop: 44, maxWidth: v ? 270 : 440 }}>
                  {["100%", "92%", "97%", "64%", "0", "95%", "100%", "88%", "71%"].map((width, index) =>
                    width === "0" ? <div key={index} style={{ height: 22 }} /> : <Bar key={index} w={width} style={{ marginTop: 16 }} />,
                  )}
                </div>
              </div>
            </Frame>

            {/* The popup, under its toolbar button. One soft shadow: it is a popover. */}
            <div
              style={{
                position: "absolute",
                top: 100,
                right: 22,
                width: popupWidth,
                opacity: arrive(frame, popup, 14),
                transform: `translateY(${(1 - arrive(frame, popup, 14)) * -14}px)`,
              }}
            >
              <div
                style={{
                  position: "relative",
                  background: C.paper,
                  border: `2px solid ${C.rule}`,
                  borderRadius: 22,
                  boxShadow: "0 18px 48px rgba(15, 31, 56, 0.16)",
                  padding: "24px 28px 26px",
                  minHeight: 650,
                }}
              >
                <div style={{ paddingBottom: 16, borderBottom: `2px solid ${C.rule}` }}>
                  <Lockup size={26} />
                </div>

                <div style={{ opacity: tracked }}>
                  <div style={{ fontSize: 30, fontWeight: 700, lineHeight: 1.22, marginTop: 18 }}>{USAG1.headline}</div>
                  <div style={{ background: C.panel, borderRadius: 16, padding: "18px 22px", marginTop: 16 }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: C.muted }}>Where it stands</div>
                    <div style={{ fontSize: 40, fontWeight: 700, color: C.blue, lineHeight: 1.2 }}>{USAG1.status}</div>
                    <div style={{ margin: "12px 0 10px" }}>
                      <StageTrack place={USAG1.place} landAt={popup + 10} width={320} dot={14} />
                    </div>
                    <div style={{ fontSize: 24, lineHeight: 1.35 }}>{USAG1.meaning}</div>
                  </div>
                  <div style={{ fontSize: 24, color: C.muted, marginTop: 14 }}>
                    First reported <strong style={{ color: C.ink }}>{USAG1.firstReported}</strong>
                  </div>
                  <div
                    style={{
                      marginTop: 16,
                      background: C.blue,
                      color: C.paper,
                      borderRadius: 14,
                      fontSize: 28,
                      fontWeight: 700,
                      textAlign: "center",
                      padding: "16px 0",
                    }}
                  >
                    See the evidence
                  </div>
                  <div style={{ fontSize: 24, color: C.muted, marginTop: 14 }}>Not medical advice.</div>
                </div>

                <div style={{ position: "absolute", left: 28, right: 28, top: 92, opacity: untracked }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 10,
                      fontSize: 24,
                      fontWeight: 700,
                      background: C.tint,
                      borderRadius: 10,
                      padding: "6px 14px",
                      outline: `3px solid rgba(20, 66, 127, ${marked})`,
                    }}
                  >
                    <Search size={24} strokeWidth={2.2} />
                    Automatic · Unreviewed
                  </span>
                  <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "8px 18px", alignItems: "center", marginTop: 16, fontSize: 24, color: C.muted }}>
                    <span>Treatment</span>
                    <Bar w={230} h={18} style={{ background: C.rule }} />
                    <span>Condition</span>
                    <Bar w={170} h={18} style={{ background: C.rule }} />
                  </div>
                  <Candidate match="High match · 92%" lit={scored} bars={["94%", "58%"]} />
                  <Candidate match="Medium match · 61%" lit={scored} bars={["82%", "70%"]} />
                </div>
              </div>
            </div>
          </div>
        </Rise>

        {v && (
          <div style={{ marginTop: -24 }}>
            <Rise at={other}>
              <div style={{ fontSize: 34, fontWeight: 600, lineHeight: 1.3 }}>
                On any other article: a live search of the trial registries.
              </div>
              <div style={{ fontSize: 26, color: C.muted, marginTop: 8 }}>
                Reads the report with OpenAI. Off until you allow it.
              </div>
            </Rise>
          </div>
        )}
      </div>
    </Stage>
  );
};
