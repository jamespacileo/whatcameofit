// A topic's card as a wide image, drawn at build time. See lib/card-image.ts.
// Only a topic with a published claim has one: an empty topic has nothing to say yet.
import type { APIRoute } from "astro";
import { topicPng } from "../../../lib/card-image";
import { data, listedTopics, type ExportedClaim, type ExportedVertical } from "../../../lib/export";

export function getStaticPaths() {
  return listedTopics.map((vertical) => ({
    params: { vertical: vertical.slug },
    props: { vertical, claims: data.claims.filter((claim) => claim.vertical === vertical.slug) },
  }));
}

export const GET: APIRoute = async ({ props }) =>
  new Response(
    await topicPng(props.vertical as ExportedVertical, props.claims as ExportedClaim[]),
    { headers: { "Content-Type": "image/png" } },
  );
