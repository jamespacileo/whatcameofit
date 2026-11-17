// The trial listing, as the pipeline wrote it: registry facts of one named set of stored
// trials. The search box fetches it only when a reader searches for words or for a
// registry number no claim cites. Behaviour: openspec trial-pages.
import type { APIRoute } from "astro";
import { listing } from "../lib/trials-listing";

export const GET: APIRoute = () => Response.json(listing);
