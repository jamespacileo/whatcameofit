# Design

## Context

See proposal.md for motivation. What shapes the approach:

- `site/src/pages/[slug].astro` opens with the topic chip and Share, then an `h1` holding `claim.headline`, a "what this is" line with the link to the method page, the dashed `UNCHECKED_NOTE` box when `checked_by_person` is false, then the digest panel (label, gloss, stage track, latest record, precise meaning, summary) and a facts row (Intervention, Claimed for, First reported, Evidence when first reported).
- 83 of the 84 published claims are not checked by a person, so the dashed box is on nearly every page. A checked page says nothing about provenance.
- `UNCHECKED_NOTE` is also served in `lookup.json` and shown by the extension. The test "Scenario: Preview build" asserts that a checked claim's page does not contain "not yet been checked by a person".
- The footer of every page already says "Registries last checked <date>" from `data.last_checked_at`.
- `site/src/lib/status.ts` holds labels, meanings, glosses and summary clauses per status code, all run through `assertNeutral` at module load.
- The site counts an approval as `status.code === "approved"` on the home and approved-claims pages.
- DESIGN.md principle 5 is "Say it once": a fact is stated once on a page.

## Goals / Non-Goals

**Goals:**

- A reader arriving from a list sees the same name at the top of the page that they clicked.
- Provenance is a calm, constant fact of every page, not an alarm on most of them.

**Non-Goals:**

- No change to the page's `<title>`, description, share sentence, card images, structured data, `lookup.json`, embed or extension.
- No `FAQPage` structured data.

## Decisions

### The heading is the name; the headline is a paragraph under it

`h1` holds `claim.intervention.name` (with the existing no-break handling for short hyphenated names). The headline becomes a `p` directly under it, at lede size in ink. The page's `<title>` stays `claim.headline`.

The search index titles a result by the page's `h1` by default. To keep search results reading as they do now, the headline paragraph carries `data-pagefind-meta="title"`. Changing what search shows is a separate decision.

Adding "for <indication>" to the heading was rejected: indications are stored capitalised ("Prevention of Alzheimer's disease") and lower-casing them by rule breaks proper names. The indication is already in the facts row and in the headline.

### One provenance line replaces the conditional box

A `p.provenance` directly under the headline, three items separated by a middle dot, in the muted colour at small size:

1. "Put together from the public records it links to" (fixed; true for claims decided by rule, seed, assistant or person).
2. "Not yet checked by a person" or "Checked by a person".
3. "Registries last checked <date>", omitted when `last_checked_at` is null.

The existing "what this is" sentence and its link to the method page stay above it. The dashed `.unchecked` box and its styles are removed from the claim page. `UNCHECKED_NOTE` is kept for `lookup.json`.

The wording for an unchecked claim is "Not yet checked by a person", which does not match the phrase the preview test forbids on checked pages and is absent from them in any case.

Keeping the box and adding a line for checked claims was rejected: two weights for one fact, and the heavier one on 99% of pages, teaches readers to ignore it.

### The three questions moved to another change

The section "In plain words" is not built here. Change `claim-at-a-glance` answers "tested in people" and "approved" in its section "The record in brief", read from the records themselves, and does not carry "what comes next" over.

## Risks / Trade-offs

- [A long intervention name makes a heavy heading: 31 published names exceed 40 characters, the longest 97] → The heading keeps the existing rule that shrinks a long title; the name is still shorter than the headline it replaces. Shortening names is a data change outside this change.
- [Removing the dashed box makes an unchecked page look more settled than it is] → The fact is still stated in words at the top of every page, and every matched record still shows its confidence score.
- [The verdict word list is short] → Same exposure as labels and glosses today; the wording is fixed text reviewed in the diff.
