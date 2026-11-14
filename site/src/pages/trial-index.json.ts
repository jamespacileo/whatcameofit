import type { APIRoute } from "astro";
import { data } from "../lib/export";
import { buildTrialIndex } from "../lib/trial-links.mjs";

export const GET: APIRoute = () => Response.json(buildTrialIndex(data));
