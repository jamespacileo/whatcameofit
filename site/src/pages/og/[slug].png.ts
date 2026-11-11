// The status card as a wide image, drawn at build time. See lib/card-image.ts.
import type { APIRoute } from "astro";
import { cardPaths, cardPng } from "../../lib/card-image";
import type { ExportedClaim } from "../../lib/export";

export const getStaticPaths = cardPaths;

export const GET: APIRoute = async ({ props }) =>
  new Response(await cardPng(props.claim as ExportedClaim, "wide"), {
    headers: { "Content-Type": "image/png" },
  });
