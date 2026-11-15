# Proposal

## Why

On 2026-11-15 the operator found that words typed in the home page's box were answered with a plain list of links and grey text under the box, unlike the rest of the page and hard to read. They asked for the answer to use the layout and parts of the "Latest" list, and chose "best match first" from three mocks (`.impeccable/mocks/search-results/`, mock C).

## What Changes

- A search answer opens on its best match drawn as the tracked-article digest: "Best match · on record now", the status in words, the stage track, the headline with the searched words marked, what the status means, first reported, and the link to the records.
- On the home page the answer stands in the "Latest" list's place, in the same white sheet. Under the best match is the report row the list draws for that claim, without its status block. Under the box one line says how many claims match, that the best match leads the list below, and offers "Clear". "Back to Latest" beside the answer's heading does the same.
- Every other match is one line: the status in blue with its stage track, the headline as a link, the treatment and what it is claimed for, the topic in a tint pill, and when it was first reported.
- The answer ends with a link to each matching topic's page, with how many claims it holds.
- On a wide screen, where the matches span two topics or more, the side column's topics give way to "Results by topic": "All results" and each topic with its count of matches, each narrowing the answer.
- On other pages with the box, the same answer stands under the box, without a report row or topic choice.
- The lookup file carries each claim's topic and each listed topic's name and claim count.

Out of scope: pasted article addresses and their answers, a search with no result, the search index.

## Capabilities

### Modified Capabilities

- `site-publishing`: how a search typed in the lookup box is answered.

## Impact

`site/src/components/Lookup.astro`, `site/src/components/DayList.astro`, `site/src/pages/lookup.json.ts`, `site/src/styles/global.css`, `site/tests/home-search.test.mjs`, `DESIGN.md`. No change to the export or the extension.
