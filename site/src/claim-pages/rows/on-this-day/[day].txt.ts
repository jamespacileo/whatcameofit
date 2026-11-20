// The claims first reported on one day of the calendar (openspec
// landing-rows-on-demand): one file for each day that has a first report. The home
// page fetches the day its reader's own date picks. Not a page: served as text, and
// search engines are asked not to index it (public/_headers).
import type { APIRoute } from "astro";
import AnniversaryDay from "../../../components/AnniversaryDay.astro";
import { calendarDays } from "../../../lib/home-lists";
import { exportVersion } from "../../../lib/export";
import { rowFile } from "../../../lib/row-file";

export function getStaticPaths() {
  return calendarDays.map((day) => ({ params: { day: `${day.id}.${exportVersion}` }, props: { day } }));
}

export const GET: APIRoute = ({ props }) => rowFile(AnniversaryDay, { day: props.day });
