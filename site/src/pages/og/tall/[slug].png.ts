// The status card as a tall image, drawn at build time. See lib/card-image.ts.
import type { APIRoute } from "astro";
import { cardPng } from "../../../lib/card-image";
import { claimPaths, type ExportedClaim } from "../../../lib/export";

export const getStaticPaths = claimPaths;

export const GET: APIRoute = async ({ props }) =>
  new Response(await cardPng(props.claim as ExportedClaim, "tall"), {
    headers: { "Content-Type": "image/png" },
  });
