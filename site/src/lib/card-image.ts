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
import { STAGE_PATH, STATUS_LABELS, latestPromise, overlayText } from "./status";

const INK = "#0f1f38";
const BLUE = "#14427f";
const MUTED = "#46566b";
const PANEL = "#f1f5fb";
const PAPER = "#ffffff";
const RULE = "#d9e2ee";
const RING = "#7f90a3";
// Pale amber: everything promised, here as on the pages.
const PROMISE = "#fff7df";
const PROMISE_RULE = "#d9c88a";
// The masthead's deep navy, and what is set on it: white, a pale blue for the
// quieter line, and the lifted blue of the name's dot.
const NAVY = "#0b2545";
const ON_NAVY_QUIET = "#c9d9ee";
const ON_NAVY_DOT = "#8ec1f5";

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

// Use the canonical vector artwork rather than maintaining another drawing.
const markData = `data:image/svg+xml;base64,${fs.readFileSync(path.resolve("public/mark.svg")).toString("base64")}`;
function stamp(size: number): Node {
  return shape("img", { src: markData, width: size, height: size });
}

// The wordmark's question mark, whose dot is the blue marker. The same drawing as
// the masthead's, and on navy the same colours as the masthead's.
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
        stroke: PAPER,
        "stroke-width": 4.8,
        "stroke-linecap": "round",
      }),
      shape("circle", { cx: 10, cy: 26, r: 3.6, fill: ON_NAVY_DOT }),
    ],
  });
}

// The head of the card is the site's masthead: the name in white on deep navy, from
// edge to edge, with the notice opposite.
function brand(layout: Layout): Node {
  const size = layout.brand;
  return box(
    {
      alignItems: "center",
      justifyContent: "space-between",
      background: NAVY,
      padding: `${layout.pad * 0.42}px ${layout.pad}px`,
    },
    [
    box({ alignItems: "center", fontSize: size, color: PAPER }, [
      stamp(size * 1.4),
      box({ fontWeight: 400, marginLeft: size * 0.5 }, SITE.wordmark[0]),
      box({ fontWeight: 700, marginLeft: size * 0.27 }, SITE.wordmark[1]),
      ask(size * 0.92),
    ]),
    box({ fontSize: size * (layout.factsBelow ? 0.86 : 0.72), color: ON_NAVY_QUIET }, CARD_NOTICE),
    ],
  );
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

// The status's place on the path from preclinical to approved: six places on a line,
// one marked. A position, never a bar that fills, and always under the status in words.
function stagePath(place: number, layout: Layout): Node {
  const dot = Math.round(layout.status * 0.17);
  const here = Math.round(dot * 1.9);
  const line = Math.max(3, Math.round(dot * 0.22));
  const places = STAGE_PATH.map((_, index) => {
    const marked = index + 1 === place;
    const size = marked ? here : dot;
    return box(
      {
        width: size,
        height: size,
        borderRadius: size,
        background: marked ? BLUE : PAPER,
        border: `${line}px solid ${marked ? BLUE : RING}`,
        boxSizing: "border-box",
      },
      [],
    );
  });
  const drawn: Node[] = [];
  places.forEach((spot, index) => {
    if (index > 0) drawn.push(box({ flexGrow: 1, height: line, background: RULE }, []));
    drawn.push(spot);
  });
  return box(
    {
      alignItems: "center",
      width: layout.factsBelow ? "100%" : layout.status * 6.4,
      marginTop: layout.status * 0.32,
    },
    drawn,
  );
}

// What the records show: the status in the site's wording, and the dates that keep
// the card true after it has been saved and passed on.
function recorded(card: CardContent, layout: Layout): Node {
  const status = box({ flexDirection: "column" }, [
    box({ fontSize: layout.factLabel, color: MUTED }, "Status now"),
    box({ fontSize: layout.status, fontWeight: 700, lineHeight: 1.1, color: BLUE }, card.status),
    card.place ? stagePath(card.place, layout) : null,
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
      width: layout.width,
      height: layout.height,
      flexDirection: "column",
      background: PAPER,
      color: INK,
      fontFamily: "Figtree",
    },
    [
      brand(layout),
      box(
        {
          // The padding is counted inside the body's size. Without this it is laid out
          // wider and taller than the image, and its right and bottom edges are cut off.
          boxSizing: "border-box",
          flexGrow: 1,
          flexDirection: "column",
          justifyContent: "space-between",
          padding: `${layout.pad * 0.8}px ${layout.pad}px ${layout.pad}px`,
        },
        [announced(card, layout), recorded(card, layout)],
      ),
    ],
  );
}

export function cardFor(claim: ExportedClaim): CardContent {
  return { ...content(claim), place: STAGE_PATH.indexOf(claim.status.code) + 1 || null };
}

function content(claim: ExportedClaim): CardContent {
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

/**
 * The site's own card, for a page that has no claim to show: the mark, the name, what
 * the site is, and the notice that goes wherever the mark goes.
 */
export async function sitePng(): Promise<Uint8Array> {
  const { width, height } = LAYOUTS.wide;
  const name = 96;
  const card = box(
    {
      boxSizing: "border-box",
      width,
      height,
      flexDirection: "column",
      justifyContent: "space-between",
      // The site's own card is its masthead at full size: white on deep navy.
      background: NAVY,
      color: PAPER,
      fontFamily: "Figtree",
      padding: 72,
    },
    [
      stamp(176),
      box({ flexDirection: "column" }, [
        box({ alignItems: "center", fontSize: name, letterSpacing: -name / 48 }, [
          box({ fontWeight: 400 }, SITE.wordmark[0]),
          box({ fontWeight: 700, marginLeft: name * 0.27 }, SITE.wordmark[1]),
          ask(name * 0.92),
        ]),
        box({ fontSize: 40, color: ON_NAVY_QUIET, marginTop: 14 }, SITE.tagline),
      ]),
      box({ justifyContent: "space-between", fontSize: 26, color: ON_NAVY_QUIET }, [
        box({}, new URL(SITE.url).host),
        box({}, CARD_NOTICE),
      ]),
    ],
  );
  const svg = await satori(card as never, { width, height, fonts });
  return new Uint8Array(new Resvg(svg, { fitTo: { mode: "width", value: width } }).render().asPng());
}

export function cardPaths() {
  return data.claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));
}
