// A pair's status card as a wide image, drawn at build time (openspec pairs-site). See
// lib/card-image.ts.
import type { APIRoute } from "astro";
import { pairCardPng } from "../lib/card-image";
import { pairPages } from "../lib/pairs";

export function getStaticPaths() {
  return Object.entries(pairPages()).map(([address, page]) => ({ params: { address }, props: { page } }));
}

export const GET: APIRoute = async ({ props }) =>
  new Response(await pairCardPng(props.page, "wide"), { headers: { "Content-Type": "image/png" } });
