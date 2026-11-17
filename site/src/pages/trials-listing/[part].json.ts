// One part of the trial listing, as the pipeline wrote its rows: registry facts of the
// trials whose registry numbers fall in the part. A part is a listing in itself, by the
// same schema, so a reader's search reads one part or all of them the same way.
import type { APIRoute, GetStaticPaths } from "astro";
import { listing, parts } from "../../lib/trials-listing";

export const getStaticPaths: GetStaticPaths = () =>
  parts.map((part) => ({ params: { part: part.name }, props: { trials: part.trials } }));

export const GET: APIRoute = ({ props }) => Response.json({ ...listing, trials: props.trials });
