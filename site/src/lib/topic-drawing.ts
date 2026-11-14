// Which drawing a topic is shown with. A topic takes the drawing of its group, or its
// own when it has no group; one with no drawing gets a plain ring. The chip
// (components/TopicChip.astro) draws the same list, and a test holds the two together.
import type { ExportedVertical } from "./export";

/** Icons from the set the rest of the site draws with, by name in `@lucide/astro`. */
export const LIBRARY_ICONS: Record<string, string> = {
  ageing: "hourglass",
  "bones-joints-and-muscles": "bone",
  "brain-and-nerves": "brain",
  cancer: "ribbon",
  "diabetes-and-hormones": "droplet",
  "eyes-and-ears": "eye",
  "heart-and-circulation": "heart-pulse",
  "immune-system-and-allergies": "shield-plus",
  infections: "microscope",
  "kidneys-and-bladder": "bean",
  "lungs-and-breathing": "wind",
  "pregnancy-and-fertility": "baby",
};

// Drawn for this site where the set has nothing that fits, on the same 24-unit
// grid with the same round line.
export const DRAWN: Record<string, string[]> = {
  // A tooth.
  "mouth-and-teeth": [
    "M7.5 3.5c-2.4 0-4 1.8-4 4.3 0 2.2.9 3.6 1.5 5.4.7 2.1.6 7.3 2.6 7.3 1.8 0 1.4-5 4.4-5s2.6 5 4.4 5c2 0 1.9-5.2 2.6-7.3.6-1.8 1.5-3.2 1.5-5.4 0-2.5-1.6-4.3-4-4.3-1.9 0-2.8 1-4.5 1s-2.6-1-4.5-1z",
  ],
  // A stomach: the gullet in at the top, the pouch, the way out at the lower left.
  "gut-and-liver": [
    "M10 3v4.5c0 1.6-.9 2.6-2.3 3.2C5.3 11.7 4 13.6 4 16v4.5",
    "M14 3v1.5c0 1.3.8 2.2 2 2.7 2.6 1.1 4.5 3.6 4.5 6.6A6.7 6.7 0 0 1 13.8 20.5c-2.2 0-3.8-.9-4.8-2.3-.4-.6-.7-.9-1-.7v3",
  ],
  // A head in profile.
  "mental-health": [
    "M9 21v-3.3A7.5 7.5 0 1 1 19.5 10.8l1.4 2.5a.6.6 0 0 1-.4.9l-1.5.3V17a2 2 0 0 1-2 2h-2v2",
  ],
  // A face under a fringe of hair.
  "skin-and-hair": [
    "M5 12.5a7 7 0 0 0 14 0",
    "M5 12.5V11a7 7 0 0 1 14 0v1.5",
    "M5.2 10.5c3.2.3 6-1.2 7.3-3.8 1.1 2.2 3.4 3.6 6.3 3.8",
  ],
};

export type TopicDrawing = { icon: string } | { paths: string[] } | null;

/** The topic's drawing: its group's, else its own, else null for the plain ring. */
export function topicDrawing(vertical: Pick<ExportedVertical, "slug" | "group">): TopicDrawing {
  const slug = [vertical.group?.slug ?? vertical.slug, vertical.slug].find(
    (entry) => entry in LIBRARY_ICONS || entry in DRAWN,
  );
  if (!slug) return null;
  return slug in LIBRARY_ICONS ? { icon: LIBRARY_ICONS[slug] } : { paths: DRAWN[slug] };
}
