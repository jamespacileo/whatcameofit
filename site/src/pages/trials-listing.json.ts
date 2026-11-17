// The trial listing's manifest: the set listed, when its records were read, and which
// part holds which registry numbers. The listing itself is in the parts
// (/trials-listing/<part>.json), so no file a reader fetches holds all of it. The search
// box fetches this only when a reader searches for words or for a registry number no
// claim cites. Behaviour: openspec trial-pages.
import type { APIRoute } from "astro";
import { manifest } from "../lib/trials-listing";

export const GET: APIRoute = () => Response.json(manifest);
