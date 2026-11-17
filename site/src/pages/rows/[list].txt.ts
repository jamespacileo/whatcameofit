// The rows of a home page list that are not in the page as built (openspec
// landing-rows-on-demand): one file a list, which the page fetches the first time a
// reader asks for more than its first rows. A file holds rows and nothing else. It is
// not a page: it is served as text, and search engines are asked not to index it
// (public/_headers).
import type { APIRoute } from "astro";
import DayGroups from "../../components/DayGroups.astro";
import FeedRows from "../../components/FeedRows.astro";
import { FEED_VIEWS, PAGE_SIZE, daysLater, restOf, topicChoices } from "../../lib/home-lists";
import { exportVersion } from "../../lib/export";
import { rowFile } from "../../lib/row-file";

const LISTS = [...FEED_VIEWS, "latest"] as const;

// A list that is whole in the page has no file.
export function getStaticPaths() {
  return LISTS.filter((list) => restOf(list)).map((list) => ({ params: { list: `${list}.${exportVersion}` }, props: { list } }));
}

export const GET: APIRoute = ({ props: { list } }) => {
  return list === "latest"
    ? rowFile(DayGroups, { headings: daysLater.headings, toCome: daysLater.toCome, topics: topicChoices })
    : rowFile(FeedRows, { view: list, from: PAGE_SIZE });
};
