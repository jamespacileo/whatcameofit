// The site's own card, shared by a page that has no claim to show. See lib/card-image.ts.
import type { APIRoute } from "astro";
import { sitePng } from "../lib/card-image";

export const GET: APIRoute = async () =>
  new Response(await sitePng(), { headers: { "Content-Type": "image/png" } });
