// One status card image per claim, drawn at build time and used as the link preview.
// It shows the promise as a date, never a count of days, so it does not go stale overnight.
import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";
import type { APIRoute } from "astro";
import satori from "satori";
import { SITE } from "../../../site.config.mjs";
import { cardFacts } from "../../lib/card";
import { data, type ExportedClaim } from "../../lib/export";
import { STATUS_LABELS, latestPromise } from "../../lib/status";

const INK = "#172534";
const BLUE = "#0b5cad";
const MUTED = "#4d5d6e";
const PANEL = "#f3f7fb";
const PAPER = "#ffffff";
const TINT = "#eaf2fa";
const RING = "#7f90a3";

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

// The site's icon: a magnifying glass over lines of print, one dot picked out.
// The same drawing as public/favicon.svg.
function stamp(size: number): Node {
  const shape = (type: string, props: Record<string, unknown>): Node => ({ type, props });
  return shape("svg", {
    width: size,
    height: size,
    viewBox: "0 0 64 64",
    children: [
      shape("rect", { width: 64, height: 64, rx: 14, fill: TINT }),
      shape("circle", { cx: 27, cy: 27, r: 17, fill: PAPER, stroke: INK, "stroke-width": 5 }),
      shape("path", { d: "M40 40l13 13", stroke: INK, "stroke-width": 6.5, "stroke-linecap": "round" }),
      shape("rect", { x: 16.5, y: 19.5, width: 21, height: 5, rx: 2.5, fill: INK }),
      shape("rect", { x: 16.5, y: 28.5, width: 11, height: 4, rx: 2, fill: RING }),
      shape("circle", { cx: 33.5, cy: 30.5, r: 3.6, fill: BLUE }),
    ],
  });
}

// The wordmark's question mark, whose dot is the blue marker. The same drawing as
// the masthead's.
function ask(height: number): Node {
  return {
    type: "svg",
    props: {
      width: (height * 20) / 30,
      height,
      viewBox: "0 0 20 30",
      style: { marginLeft: 2, marginTop: 3 },
      children: [
        {
          type: "path",
          props: {
            d: "M4.2 8.8a5.9 5.9 0 1 1 9 5c-2.1 1.3-3.2 2.4-3.2 4.7",
            fill: "none",
            stroke: INK,
            "stroke-width": 4.8,
            "stroke-linecap": "round",
          },
        },
        { type: "circle", props: { cx: 10, cy: 26, r: 3.6, fill: BLUE } },
      ],
    },
  };
}

function fact(label: string, value: string): Node {
  return box({ flexDirection: "column", marginRight: 64 }, [
    box({ fontSize: 26, fontWeight: 400, color: MUTED }, label),
    box({ fontSize: 44, fontWeight: 700, lineHeight: 1.1, color: BLUE }, value),
  ]);
}

function card(claim: ExportedClaim): Node {
  const promise = latestPromise(claim);
  const facts = cardFacts(
    claim,
    STATUS_LABELS[claim.status.code],
    promise?.parsed_date ?? null,
  ).map(({ label, value }) => fact(label, value));

  return box(
    {
      // The padding is counted inside the card's size. Without this the card was laid
      // out wider and taller than the image, and its right and bottom edges were cut off.
      boxSizing: "border-box",
      width: 1200,
      height: 630,
      flexDirection: "column",
      justifyContent: "space-between",
      background: PAPER,
      color: INK,
      fontFamily: "Figtree",
      padding: "52px 64px 56px",
    },
    [
      box({ flexDirection: "column" }, [
        box({ alignItems: "center", fontSize: 34, color: INK }, [
          stamp(46),
          box({ fontWeight: 400, marginLeft: 16 }, SITE.wordmark[0]),
          box({ fontWeight: 700, marginLeft: 9 }, SITE.wordmark[1]),
          ask(31),
        ]),
        box(
          {
            fontSize: claim.headline.length > 70 ? 60 : 76,
            fontWeight: 700,
            lineHeight: 1.08,
            letterSpacing: -1,
            marginTop: 30,
          },
          claim.headline,
        ),
      ]),
      box({ background: PANEL, borderRadius: 28, padding: "30px 40px 34px" }, facts),
    ],
  );
}

export function getStaticPaths() {
  return data.claims.map((claim) => ({ params: { slug: claim.slug }, props: { claim } }));
}

export const GET: APIRoute = async ({ props }) => {
  const svg = await satori(card(props.claim as ExportedClaim) as never, {
    width: 1200,
    height: 630,
    fonts,
  });
  const png = new Resvg(svg, { fitTo: { mode: "width", value: 1200 } }).render().asPng();
  return new Response(new Uint8Array(png), { headers: { "Content-Type": "image/png" } });
};
