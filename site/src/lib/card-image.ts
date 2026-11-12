// The status card as an image, in three shapes drawn from one description.
// Wide is the link preview; square and tall are for image-led networks.
import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";
import satori from "satori";
import { SITE } from "../../site.config.mjs";
import {
  CARD_NOTICE,
  PROMISED_LABEL,
  cardContent,
  clip,
  type CardContent,
  type CardFact,
} from "./card";
import { data, type ExportedClaim } from "./export";
import { STATUS_LABELS, latestPromise, overlayText } from "./status";

const INK = "#0f1f38";
const BLUE = "#14427f";
const MUTED = "#46566b";
const PANEL = "#f1f5fb";
const PAPER = "#ffffff";
const TINT = "#e6eef8";
const RULE = "#d9e2ee";
// The icon's own two: its outline, and the amber of the capsule's promised half.
const DEEP = "#0b2545";
const CAPSULE_PROMISE = "#f4c95d";
// Pale amber: everything promised, here as on the pages.
const PROMISE = "#fff7df";
const PROMISE_RULE = "#d9c88a";

export type Shape = "wide" | "square" | "tall";

interface Layout {
  width: number;
  height: number;
  pad: number;
  /** Size of the wordmark's type; the icon and the notice follow from it. */
  brand: number;
  /** Sizes for the quoted title, by how long it is, and where a very long one is cut. */
  quote: (length: number) => number;
  quoteMax: number;
  outlet: number;
  status: number;
  factLabel: number;
  factValue: number;
  /** Facts in a row beside the status, or stacked beneath it. */
  factsBelow: boolean;
}

const LAYOUTS: Record<Shape, Layout> = {
  wide: {
    width: 1200,
    height: 630,
    pad: 56,
    brand: 30,
    quote: (length) => (length > 110 ? 38 : length > 70 ? 46 : 58),
    quoteMax: 150,
    outlet: 26,
    status: 50,
    factLabel: 22,
    factValue: 32,
    factsBelow: false,
  },
  square: {
    width: 1080,
    height: 1080,
    pad: 72,
    brand: 36,
    quote: (length) => (length > 110 ? 52 : length > 70 ? 62 : 76),
    quoteMax: 170,
    outlet: 32,
    status: 68,
    factLabel: 26,
    factValue: 40,
    factsBelow: true,
  },
  tall: {
    width: 1080,
    height: 1920,
    pad: 88,
    brand: 42,
    quote: (length) => (length > 110 ? 68 : length > 70 ? 80 : 96),
    quoteMax: 200,
    outlet: 38,
    status: 88,
    factLabel: 30,
    factValue: 48,
    factsBelow: true,
  },
};

// The site's face, as static files the image renderer can read.
const font = (weight: number) =>
  fs.readFileSync(
    path.resolve(`node_modules/@fontsource/figtree/files/figtree-latin-${weight}-normal.woff`),
  );
const fonts = [
  { name: "Figtree", data: font(400), weight: 400 as const, style: "normal" as const },
  { name: "Figtree", data: font(700), weight: 700 as const, style: "normal" as const },
];

type Node = { type: string; props: Record<string, unknown> };
const box = (style: Record<string, unknown>, children: unknown): Node => ({
  type: "div",
  props: { style: { display: "flex", ...style }, children },
});
const shape = (type: string, props: Record<string, unknown>): Node => ({ type, props });

// The site's icon: a magnifying glass over a capsule in two halves.
// The same drawing as public/favicon.svg.
function stamp(size: number): Node {
  return shape("svg", {
    width: size,
    height: size,
    viewBox: "0 0 64 64",
    children: [
      shape("rect", { width: 64, height: 64, rx: 14, fill: TINT }),
      shape("circle", { cx: 27, cy: 27, r: 17, fill: PAPER, stroke: DEEP, "stroke-width": 5 }),
      shape("path", { d: "M40 40l13 13", stroke: DEEP, "stroke-width": 6.5, "stroke-linecap": "round" }),
      // The capsule under the lens: the promised half in amber, the recorded half in blue.
      shape("rect", { x: 14, y: 21, width: 26, height: 12, rx: 6, fill: BLUE }),
      shape("path", { d: "M27 21h-7a6 6 0 0 0 0 12h7z", fill: CAPSULE_PROMISE }),
      shape("path", { d: "M27 21v12", stroke: PAPER, "stroke-width": 2.2 }),
    ],
  });
}

// The wordmark's question mark, whose dot is the blue marker. The same drawing as
// the masthead's.
function ask(height: number): Node {
  return shape("svg", {
    width: (height * 20) / 30,
    height,
    viewBox: "0 0 20 30",
    style: { marginLeft: height * 0.06, marginTop: height * 0.1 },
    children: [
      shape("path", {
        d: "M4.2 8.8a5.9 5.9 0 1 1 9 5c-2.1 1.3-3.2 2.4-3.2 4.7",
        fill: "none",
        stroke: INK,
        "stroke-width": 4.8,
        "stroke-linecap": "round",
      }),
      shape("circle", { cx: 10, cy: 26, r: 3.6, fill: BLUE }),
    ],
  });
}

function brand(layout: Layout): Node {
  const size = layout.brand;
  return box({ alignItems: "center", justifyContent: "space-between" }, [
    box({ alignItems: "center", fontSize: size, color: INK }, [
      stamp(size * 1.4),
      box({ fontWeight: 400, marginLeft: size * 0.5 }, SITE.wordmark[0]),
      box({ fontWeight: 700, marginLeft: size * 0.27 }, SITE.wordmark[1]),
      ask(size * 0.92),
    ]),
    box({ fontSize: size * 0.72, color: MUTED }, CARD_NOTICE),
  ]);
}

// What was announced: the outlet's own words, marked as a quotation and attributed.
// The site adds nothing between this and the status below it.
function announced(card: CardContent, layout: Layout): Node {
  const text = clip(card.quote ?? card.headline, layout.quoteMax);
  const size = layout.quote(text.length);
  return box({ flexDirection: "column" }, [
    box(
      { fontSize: size, fontWeight: 700, lineHeight: 1.12, letterSpacing: -size / 70 },
      card.quote ? `“${text}”` : text,
    ),
    card.outlet &&
      box({ fontSize: layout.outlet, color: MUTED, marginTop: layout.outlet * 0.55 }, card.outlet),
  ]);
}

function fact({ label, value }: CardFact, layout: Layout): Node {
  // A promise sits on pale amber with a dashed rule, as it does in the timetable, so
  // the promised year and the status are told apart before either is read.
  const promised = label === PROMISED_LABEL;
  const inset = layout.factLabel * 0.5;
  return box(
    {
      flexDirection: "column",
      marginLeft: layout.factsBelow ? 0 : 48 - (promised ? inset : 0),
      marginRight: layout.factsBelow ? 56 - (promised ? inset : 0) : 0,
      ...(promised && {
        background: PROMISE,
        border: `2px dashed ${PROMISE_RULE}`,
        borderRadius: 12,
        padding: `${inset * 0.5}px ${inset}px`,
        // The amber box is taller than a bare fact; it grows up and down equally.
        marginTop: -inset * 0.5 - 2,
        marginBottom: -inset * 0.5 - 2,
      }),
    },
    [
      box({ fontSize: layout.factLabel, color: MUTED }, label),
      box({ fontSize: layout.factValue, fontWeight: 700, lineHeight: 1.15, color: INK }, value),
    ],
  );
}

// What the records show: the status in the site's wording, and the dates that keep
// the card true after it has been saved and passed on.
function recorded(card: CardContent, layout: Layout): Node {
  const status = box({ flexDirection: "column" }, [
    box({ fontSize: layout.factLabel, color: MUTED }, "Status now"),
    box({ fontSize: layout.status, fontWeight: 700, lineHeight: 1.1, color: BLUE }, card.status),
    card.note &&
      box(
        {
          alignSelf: "flex-start",
          fontSize: layout.factLabel,
          fontWeight: 700,
          color: INK,
          border: `2px dashed ${BLUE}`,
          borderRadius: 8,
          padding: `${layout.factLabel * 0.15}px ${layout.factLabel * 0.5}px`,
          marginTop: layout.factLabel * 0.5,
        },
        card.note,
      ),
  ]);
  const others = card.facts
    .filter(({ label }) => label !== "Status now")
    .map((entry) => fact(entry, layout));
  const padding = `${layout.pad * 0.5}px ${layout.pad * 0.62}px ${layout.pad * 0.56}px`;

  return layout.factsBelow
    ? box({ flexDirection: "column", background: PANEL, borderRadius: 32, padding }, [
        status,
        box(
          {
            marginTop: layout.pad * 0.45,
            paddingTop: layout.pad * 0.4,
            borderTop: `2px solid ${RULE}`,
          },
          others,
        ),
      ])
    : box(
        {
          alignItems: "flex-end",
          justifyContent: "space-between",
          background: PANEL,
          borderRadius: 28,
          padding,
        },
        [status, box({}, others)],
      );
}

function draw(card: CardContent, layout: Layout): Node {
  return box(
    {
      // The padding is counted inside the card's size. Without this the card is laid
      // out wider and taller than the image, and its right and bottom edges are cut off.
      boxSizing: "border-box",
      width: layout.width,
      height: layout.height,
      flexDirection: "column",
      justifyContent: "space-between",
      background: PAPER,
      color: INK,
      fontFamily: "Figtree",
      padding: layout.pad,
    },
    [brand(layout), announced(card, layout), recorded(card, layout)],
  );
}

export function cardFor(claim: ExportedClaim): CardContent {
  return cardContent(
    claim,
    STATUS_LABELS[claim.status.code],
    overlayText(claim.status.overlay_years),
    latestPromise(claim)?.parsed_date ?? null,
    data.last_checked_at,
  );
}

export const CARD_SIZES: Record<Shape, { width: number; height: number }> = {
  wide: { width: LAYOUTS.wide.width, height: LAYOUTS.wide.height },
  square: { width: LAYOUTS.square.width, height: LAYOUTS.square.height },
  tall: { width: LAYOUTS.tall.width, height: LAYOUTS.tall.height },
};

export async function cardPng(claim: ExportedClaim, which: Shape): Promise<Uint8Array> {
  const layout = LAYOUTS[which];
  const svg = await satori(draw(cardFor(claim), layout) as never, {
    width: layout.width,
    height: layout.height,
    fonts,
  });
  return new Uint8Array(
    new Resvg(svg, { fitTo: { mode: "width", value: layout.width } }).render().asPng(),
  );
}

export function cardPaths() {
  return data.claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));
}
