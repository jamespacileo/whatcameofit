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
- A lay reader's three questions are answered without reading the timetable.

**Non-Goals:**

- No change to the page's `<title>`, description, share sentence, card images, structured data, `lookup.json`, embed or extension.
- No `FAQPage` structured data.
- No fourth question about getting the treatment: the footer notices already answer it on every page.

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

### Three questions, fixed answers keyed by status code

A section "In plain words" between the facts row and the timetable: a description list, questions as terms, answers always open. Three short answers do not need folding, and DESIGN.md puts the answer first.

To respect "Say it once", the first answer does not repeat the precise meaning in the digest. It gives a plain yes-or-no reading, and for a status that rests on trials it adds how many trials are counted, linking to the matched records. The count is of distinct trials among the claim's approved events, which the page already computes for the timetable key.

Wording lives in `status.ts` as `STATUS_ANSWERS: Record<StatusCode, { tested: string; approved: string; next: string }>`, so a missing code or question is a type error, and every string goes through `assertNeutral`. The shared sentence "This site does not predict whether or when that will happen." follows every `next` answer except the approved one.

Proposed wording, to be confirmed by the operator line by line during apply:

| Code | Has it been tested in people? | What would come next? |
| --- | --- | --- |
| `preclinical_only` | No trial in people is on record. | The next record on the path would be a registered trial in people. |
| `no_trial_found` | The first reports described a study in people. No registered trial was found. | The next record on the path would be a registered trial in people. |
| `trial_registered` | A trial in people is registered. None with a phase has started. | The next record on the path would be a trial starting. |
| `phase_1` | Yes. The furthest trial that has started is an early one, which mainly checks safety. | The next record on the path would be a mid-stage (Phase 2) trial starting. |
| `phase_2` | Yes. The furthest trial that has started is a mid-stage one. | The next record on the path would be a large late-stage (Phase 3) trial starting. |
| `phase_3` | Yes. The furthest trial that has started is a large late-stage one. | The next record on the path would be a regulator's decision. |
| `approved` | Yes. A regulator has recorded an approval. | The path on this site ends at approval. Later records are still added. |
| `failed` | Yes. A trial reported that it did not meet its main goal, and no other trial stands. | A new registered trial would be recorded here. |
| `terminated` | Trials were registered. Every one was stopped early or withdrawn. | A new registered trial would be recorded here. |
| `retracted` | The paper the first reports were about has been retracted. Any trial on record is listed below. | A new registered trial would be recorded here. |

"Is it approved?" has two answers. For `approved`: "A regulator has recorded an approval; the record below names it. An approval is not advice to take a treatment." For every other code: "No approval is on record." This matches how the site already counts approvals.

Deriving the answers from the events instead of the status code was rejected: status is the one place the rules are applied, and a second reading of the events could disagree with it.

## Risks / Trade-offs

- [A long intervention name makes a heavy heading: 31 published names exceed 40 characters, the longest 97] → The heading keeps the existing rule that shrinks a long title; the name is still shorter than the headline it replaces. Shortening names is a data change outside this change.
- [The questions repeat what the digest says] → The first answer is a yes-or-no reading plus a trial count, not the meaning sentence; the second and third are not stated anywhere else on the page.
- [A "what comes next" answer is read as a forecast] → Every such answer is followed by the fixed sentence that the site does not predict it, and a scenario tests for that sentence.
- [An answer is read as advice] → Answers describe records only; the approved answer says an approval is not advice; the footer notices are unchanged. The wording is confirmed by the operator before merge.
- [Removing the dashed box makes an unchecked page look more settled than it is] → The fact is still stated in words at the top of every page, and every matched record still shows its confidence score.
- [The verdict word list is short] → Same exposure as labels and glosses today; the wording is fixed text reviewed in the diff.
