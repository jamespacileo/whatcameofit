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

const INK = "#231f33";
const INDIGO = "#3d2f7a";
const MUTED = "#5d5677";
const PANEL = "#f6f4fb";
const PAPER = "#ffffff";

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

function fact(label: string, value: string): Node {
  return box({ flexDirection: "column", marginRight: 64 }, [
    box({ fontSize: 26, fontWeight: 400, color: MUTED }, label),
    box({ fontSize: 44, fontWeight: 700, lineHeight: 1.1, color: INDIGO }, value),
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
      width: "100%",
      height: "100%",
      flexDirection: "column",
      justifyContent: "space-between",
      background: PAPER,
      color: INK,
      fontFamily: "Figtree",
      padding: "52px 64px 56px",
    },
    [
      box({ flexDirection: "column" }, [
        box({ fontSize: 34, fontWeight: 700, color: INDIGO }, SITE.name),
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
