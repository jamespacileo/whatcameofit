// The narration's clock: section times, word times, and the captions drawn from them.
// Both files are written by scripts/narrate.py into the video's own folder.
import type { FC } from "react";
import { staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { C } from "./tokens";

export type Section = {
  name: string;
  start_time: number;
  end_time: number;
  start_frame: number;
  duration_frames: number;
};

export type Timing = { total_frames: number; fps: number; sections: Section[] };

export type Captions = {
  cues: { text: string; start: number; end: number; section: string }[];
  words: { text: string; start: number; end: number }[];
};

export const loadNarration = async (): Promise<{ timing: Timing; captions: Captions }> => {
  const [timing, captions] = await Promise.all(
    ["timing.json", "captions.json"].map(async (file) => {
      const response = await fetch(staticFile(file));
      if (!response.ok) throw new Error(`${file} is missing: run scripts/narrate.py first`);
      return response.json();
    }),
  );
  return { timing, captions };
};

const norm = (word: string) => word.toLowerCase().replace(/[^a-z0-9]/g, "");

/**
 * Where a phrase is spoken inside a section, in frames from the section's start.
 * Scenes time themselves by the words, so a new narration needs no new numbers.
 */
export const cueFinder =
  (captions: Captions, section: Section, fps: number) =>
  (phrase: string): number => {
    const wanted = phrase.split(/\s+/).map(norm);
    const { words } = captions;
    for (let index = 0; index < words.length; index++) {
      const { start } = words[index];
      if (start < section.start_time - 0.01 || start >= section.end_time) continue;
      if (wanted.every((word, offset) => norm(words[index + offset]?.text ?? "") === word)) {
        return Math.round((start - section.start_time) * fps);
      }
    }
    throw new Error(`"${phrase}" is not spoken in the section "${section.name}"`);
  };

/** The caption for the current moment, in the site's plain box. */
export const CaptionBar: FC<{ captions: Captions; v: boolean }> = ({ captions, v }) => {
  const { fps } = useVideoConfig();
  const time = useCurrentFrame() / fps;
  const { cues } = captions;
  const index = cues.findIndex(
    (cue, n) => time >= cue.start - 0.05 && time < Math.min(cue.end + 0.45, cues[n + 1]?.start ?? Infinity),
  );
  if (index < 0) return null;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: v ? 300 : 52,
        display: "flex",
        justifyContent: "center",
        padding: v ? "0 60px" : 0,
      }}
    >
      <div
        style={{
          background: C.paper,
          border: `2px solid ${C.rule}`,
          borderRadius: 16,
          padding: v ? "16px 30px" : "12px 28px",
          fontSize: v ? 44 : 34,
          fontWeight: 600,
          lineHeight: 1.25,
          textAlign: "center",
          color: C.ink,
        }}
      >
        {cues[index].text}
      </div>
    </div>
  );
};
