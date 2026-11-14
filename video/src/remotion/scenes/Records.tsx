// The dated records under a status, each with its source, and the promise beside them.
import { ArrowUpRight, ClipboardCheck, ClipboardList, Newspaper } from "lucide-react";
import type { FC, ReactNode } from "react";
import { interpolateColors, useCurrentFrame } from "remotion";
import { Basis, Frame } from "../brand/marks";
import { arrive, Rise, Stage } from "../brand/motion";
import { C, type SceneProps } from "../brand/tokens";
import { USAG1 } from "./claim-data";

/** A link to the source that holds a record. When spoken of it shows, then settles. */
const Source: FC<{ name: string; litAt: number }> = ({ name, litAt }) => {
  const frame = useCurrentFrame();
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 30,
        fontWeight: 600,
        color: C.blue,
        whiteSpace: "nowrap",
        borderRadius: 10,
        padding: "4px 12px",
        background: interpolateColors(
          arrive(frame, litAt, 8) - 0.5 * arrive(frame, litAt + 30, 30),
          [0, 0.5, 1],
          ["rgba(230,238,248,0)", C.tint, C.tag],
        ),
      }}
    >
      <span style={{ textDecoration: "underline", textUnderlineOffset: 5 }}>{name}</span>
      <ArrowUpRight size={30} strokeWidth={2} />
    </span>
  );
};

const Row: FC<{
  year: string;
  icon: ReactNode;
  day: string;
  what: ReactNode;
  detail: string;
  basis?: boolean;
  source: ReactNode;
  v: boolean;
}> = ({ year, icon, day, what, detail, basis, source, v }) => (
  <div
    style={{
      display: "grid",
      gridTemplateColumns: v ? "100px 1fr" : "120px 1fr auto",
      alignItems: "center",
      gap: v ? "10px 0" : "0 24px",
      padding: v ? "26px 30px" : "24px 36px",
      borderTop: `2px solid ${C.ruleSoft}`,
    }}
  >
    <div style={{ fontSize: 34, fontWeight: 700 }}>{year}</div>
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: v ? 32 : 34, fontWeight: 700 }}>
        <span style={{ color: C.muted, display: "inline-flex" }}>{icon}</span>
        <span>{what}</span>
        {basis && <Basis />}
      </div>
      <div style={{ fontSize: 28, color: C.muted, marginTop: 4 }}>
        <span style={{ color: C.ink, fontWeight: 600 }}>{day}</span> · {detail}
      </div>
    </div>
    <div style={{ gridColumn: v ? 2 : "auto" }}>{source}</div>
  </div>
);

export const Records: FC<SceneProps> = ({ at, v }) => {
  const links = at("every record links");
  const [registered, completed] = USAG1.records;
  return (
    <Stage v={v}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: v ? "1fr" : "470px 1fr",
          gap: v ? 40 : 64,
          alignItems: "center",
        }}
      >
        <div>
          <Rise at={2}>
            <div style={{ fontSize: v ? 60 : 72, fontWeight: 700, lineHeight: 1.1 }}>The records</div>
            <div style={{ fontSize: 32, color: C.muted, marginTop: 12, lineHeight: 1.35 }}>
              Each with its date and its source.
            </div>
          </Rise>
          {!v && <Promised at={at("and what was promised") - 4} />}
        </div>

        <Rise at={8}>
          <Frame style={{ overflow: "hidden" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: v ? "18px 30px" : "18px 36px",
                fontSize: 26,
                fontWeight: 700,
                color: C.muted,
              }}
            >
              <span>Recorded</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 12, fontWeight: 500, fontSize: 24 }}>
                <Basis size={14} /> Basis of status
              </span>
            </div>
            <Row
              v={v}
              year="2021"
              icon={<Newspaper size={34} strokeWidth={1.8} />}
              day="31 Mar"
              what={<>“{USAG1.article.title}”</>}
              detail="News report"
              source={<Source name={USAG1.article.outlet} litAt={links} />}
            />
            <div
              style={{
                padding: v ? "14px 30px" : "14px 36px",
                borderTop: `2px solid ${C.ruleSoft}`,
                fontSize: 26,
                color: C.muted,
              }}
            >
              2022 to 2023 · No record
            </div>
            <Rise at={at("a trial registered") - 4}>
              <Row
                v={v}
                year={registered.year}
                icon={<ClipboardList size={34} strokeWidth={1.8} />}
                day={registered.day}
                what={registered.what}
                detail={registered.detail}
                basis
                source={<Source name={registered.source} litAt={links + 6} />}
              />
            </Rise>
            <Rise at={at("the same trial") - 4}>
              <Row
                v={v}
                year={completed.year}
                icon={<ClipboardCheck size={34} strokeWidth={1.8} />}
                day={completed.day}
                what={completed.what}
                detail={completed.detail}
                basis
                source={<Source name={completed.source} litAt={links + 12} />}
              />
            </Rise>
          </Frame>
        </Rise>

        {v && <Promised at={at("and what was promised") - 4} />}
      </div>
    </Stage>
  );
};

/** Pale amber means "promised" and nothing else, with dashed rules. */
const Promised: FC<{ at: number }> = ({ at }) => (
  <Rise at={at} style={{ marginTop: 40 }}>
    <div
      style={{
        background: C.promise,
        border: `2.5px dashed ${C.promiseRule}`,
        borderRadius: 24,
        padding: "28px 34px",
      }}
    >
      <div style={{ fontSize: 26, fontWeight: 700 }}>Promised</div>
      <div style={{ fontSize: 32, fontWeight: 500, lineHeight: 1.3, marginTop: 8 }}>{USAG1.promise}</div>
      <div style={{ fontSize: 24, color: C.muted, marginTop: 10 }}>
        No date given · {USAG1.article.outlet}, 2021
      </div>
    </div>
  </Rise>
);
