// One status card image per claim, drawn at build time and used as the link preview.
// It shows the promise as a date, never a count of days, so it does not go stale overnight.
import fs from "node:fs";
import path from "node:path";
import { Resvg } from "@resvg/resvg-js";
import type { APIRoute } from "astro";
import satori from "satori";
import { SITE } from "../../../site.config.mjs";
import { data, type ExportedClaim } from "../../lib/export";
import { STATUS_LABELS, latestPromise } from "../../lib/status";

const INK = "#14161a";
const YELLOW = "#ffd21e";
const PAPER = "#ffffff";

const font = (weight: number) =>
  fs.readFileSync(
    path.resolve(`node_modules/@fontsource/archivo/files/archivo-latin-${weight}-normal.woff`),
  );
const fonts = [
  { name: "Archivo", data: font(500), weight: 500 as const, style: "normal" as const },
  { name: "Archivo", data: font(800), weight: 800 as const, style: "normal" as const },
];

type Node = { type: string; props: Record<string, unknown> };
const box = (style: Record<string, unknown>, children: unknown): Node => ({
  type: "div",
  props: { style: { display: "flex", ...style }, children },
});

function fact(label: string, value: string): Node {
  return box({ flexDirection: "column", marginRight: 56 }, [
    box({ fontSize: 24, fontWeight: 500 }, label),
    box({ fontSize: 40, fontWeight: 800, lineHeight: 1.1 }, value),
  ]);
}

function card(claim: ExportedClaim): Node {
  const promise = latestPromise(claim);
  const facts = [
    claim.first_reported_date ? fact("First reported", claim.first_reported_date.slice(0, 4)) : null,
    promise ? fact("Promised by", promise.parsed_date!.slice(0, 4)) : null,
    fact("Status now", STATUS_LABELS[claim.status.code]),
  ].filter(Boolean);

  return box(
    {
      width: "100%",
      height: "100%",
      flexDirection: "column",
      justifyContent: "space-between",
      background: YELLOW,
      color: INK,
      fontFamily: "Archivo",
    },
    [
      box({ flexDirection: "column", padding: "48px 64px 0" }, [
        box({ fontSize: 30, fontWeight: 800 }, SITE.name),
        box(
          { fontSize: claim.headline.length > 70 ? 56 : 70, fontWeight: 800, lineHeight: 1.04, marginTop: 28 },
          claim.headline,
        ),
      ]),
      box(
        {
          background: PAPER,
          borderTop: `6px solid ${INK}`,
          padding: "30px 64px 40px",
          alignItems: "flex-start",
        },
        facts,
      ),
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
