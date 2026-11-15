# Proposal

## Why

On 2026-11-15 the operator found that words typed in the home page's box were answered with a plain list of links and grey text under the box, unlike the rest of the page and hard to read. They asked for the answer to use the layout and parts of the "Latest" list, and chose "best match first" from three mocks (`.impeccable/mocks/search-results/`, mock C). They then asked that a search still match on report headlines, posts and trial identifiers while every result stays a claim, and chose mock D with F from a second round.

## What Changes

- A search answer opens on its best match drawn as the tracked-article digest: "Best match · on record now", the status in words, the stage track, the headline with the searched words marked, what the status means, first reported, and the link to the records.
- On the home page the answer stands in the "Latest" list's place, in the same white sheet. Under the best match is the report row the list draws for that claim, without its status block. Under the box one line says how many claims match, that the best match leads the list below, and offers "Clear". "Back to Latest" beside the answer's heading does the same.
- Every other match is one line: the status in blue with its stage track, the headline as a link, the treatment and what it is claimed for, the topic in a tint pill, and when it was first reported.
- The answer ends with a link to each matching topic's page, with how many claims it holds.
- On a wide screen, where the matches span two topics or more, the side column's topics give way to "Results by topic": "All results" and each topic with its count of matches, each narrowing the answer.
- On other pages with the box, the same answer stands under the box, without a report row or topic choice.
- The lookup file carries each claim's topic and each listed topic's name and claim count.

- Under the best match and each other match, a "found in" line for each report headline or trial title holding the searched words, at most three under the best match and two under each other: a drawing for the kind, "Report headline" or "Trial", the headline in quotation marks or the trial's title with the words marked, and where it is from: the outlet's own icon over its letter tile, its name and the date, or the registry and identifier with the phase. A report drawn in full under the best match is not named again inside it. The operator chose this on 2026-11-15 (mock D), with outlet icons wherever a report is named.
- Words that are a tracked report's whole headline put its claim first, said so: "A tracked report has this headline", the claim labelled "Its claim", and the other matches under "Other claims with these words" (mock F).
- A trial registry identifier (NCT, jRCT, ISRCTN, ACTRN, ChiCTR, DRKS, CTRI, EU CT) is answered with that trial alone: the registry record (registry, identifier, phase, title) on the panel blue, then each claim it is matched to, and "A trial on record is not a treatment option." An identifier with no trial on record says so. It never goes to the word search, which matches every identifier sharing the prefix (mock F).
- A search detail file, `/search-detail.json`, holds each published claim's reports (title, outlet, domain, the site's address of the outlet icon, address, date) and trials (identifier, title, registry, address, phases). It is read only when words are searched. The extension does not read it.

- After a critique on 2026-11-15 (25/40, `.impeccable/critique/`), the operator chose to fix all five issues it found:
  - Matches are ordered by a fixed rule over the words they hold (side by side, then all, in the claim's headline, then a report's headline, then the treatment and condition), the search index's order breaking a tie. A word search leads with its closest match as a row labelled "Closest match"; the digest is kept for an exact headline and a trial identifier, where the site knows the claim.
  - In an answer the unchecked notice is one grey line; a phone gets a link to the other claims.
  - The report shown with an exact headline is built from the search detail with the words marked, the same on every page, instead of being copied from the day list.
  - One way out, "Clear search", 44px tall, beside the count; the count is said once; the line under the box says only where the answer is. The topic pick is kept in the address as `topic`, and topics are offered as buttons under the heading where the side column is not.
  - "Nothing tracked here matches “…”." replaces "No record found for … We say that a lot.", and points to pasting the article's link. An identifier not matched to a tracked claim links to its registry's record where the address is built from the identifier alone. "A trial on record is not a treatment option." stands inside the record it qualifies.

Out of scope: pasted article addresses and their answers, a search with no result, the search index's ranking. Posts on social sites are not in the export yet; once they are, they are named as reports by their platform.

## Capabilities

### Modified Capabilities

- `site-publishing`: how a search typed in the lookup box is answered.

## Impact

`site/src/components/Lookup.astro`, `site/src/components/DayList.astro`, `site/src/pages/lookup.json.ts`, `site/src/pages/search-detail.json.ts`, `site/src/styles/global.css`, `site/tests/home-search.test.mjs`, `DESIGN.md`. No change to the export or the extension.
