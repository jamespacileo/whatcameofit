# Proposal

## Why

A claim page holds the facts a skimming reader wants, but not where a skimming reader looks. On the page for the wrist-worn device for Tourette syndrome, the reader passes the digest, the facts row and a timetable of nine near-identical registry lines before reaching the trials, and has to open a fold on each trial to learn that the largest enrolled 135 people, had a sham comparison and has posted results. Nothing says what the records do not cover, such as that no trial is under way or that nothing was measured past four weeks. A lay reader with a short attention span leaves with the status label and little else.

The operator reviewed mockups on 2026-11-14 (https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE). A first design, two lists headed "On record" and "Not on record" plus notes headed "strengthens" and "limits", was critiqued the same day (`.impeccable/critique/2026-11-14T20-23-42Z__claude-ai-artifact-ypjvb4nta7uhypih9e2hue.md`): two valenced columns grade the treatment, three summaries said the same facts, and large result figures outranked the status. The operator chose the rework on boards F, G and H: one summary, grouped by kind of fact, each answer opening to its source. The operator also asked for a model to read what rules cannot, with the process as deterministic as it can be.

A second critique that day, of the rework (`.impeccable/critique/2026-11-14T20-40-55Z__claude-ai-artifact-ypjvb4nta7uhypih9e2hue.md`, 27/40), found that a third group, "What the records do not cover", was defined by its answers being "None" and so still read as a list of faults; that result values could not be read without a scale the records do not give in a usable field; that the digest's "No trial with a phase has started" contradicted "Yes, in 3 trials"; and that ten rows was too many. The operator chose: fixed places in two groups, no result values, a bridging sentence in the digest, and six rows (boards F, G and H, second versions).

## What Changes

- Every claim page gains one section under the digest panel, "The record in brief": at most six short questions with short answers, in two groups, "How it was tested" and "Where the records stand now". An answer states its fact and never begins with "Yes". Each question has one fixed place whatever its answer; "None on record" is said where its question sits. No group, heading, mark or order says whether an answer is good or bad for the treatment.
- Each answer opens to the record it was read from: the trial or regulator record, linked, what was read, whether it was read by rule or by a model, and the date the record was read.
- Most answers are read by rule on the site from fields the export already carries.
- Two answers are read by a model from a trial's stored registry record, as a new pipeline step: how long after the start a trial's main measure was taken, and what kind of thing that measure is. The model returns a code from a fixed list and the exact words it read; a rule checks those words are in the record; an answer that fails is not stored. The site words every answer; the model writes no sentence a reader sees.
- The section shows no posted result values. The answer about what the largest trial measured links to that trial's entry, where its results already are.
- When the status is Trial registered and trials are on record, the digest panel adds how many trials are on record, how many have finished, and that the registry gives none a phase.
- The facts row no longer counts trials or gives the largest size; the section says both.
- The neutral-wording build check covers every question, answer and group name.
- **Supersedes** the "A claim page answers three fixed questions by rule" requirement of the unstarted change `plain-claim-page`: its "tested in people" and "approved" answers are rows here. That change keeps its title and provenance-line requirements.

Out of scope:

- Two sides, columns or tags for "notable" and "not notable", in any wording, and any group defined by its answers being absences.
- Questions about papers and about who ran the trials; both sections remain lower on the page.
- The scale a measure runs on (its lowest and highest value). A registry record gives it only in a free-text description, which `trial-facts` does not carry because it can state a conclusion.
- Anything read from a paper's abstract or a news article's text. Neither is stored.
- A row of links to the page's sections, trial highlight cards (board B), home page claim cards (board D), cards, the embed, `lookup.json` and the extension.

## Capabilities

### New Capabilities

- `record-readings`: answers a model reads from a trial's stored registry record into fixed codes, each kept with the words it was read from, checked by rule before it is stored, scored, and exported.

### Modified Capabilities

- `site-publishing`: a claim page shows "The record in brief": fixed questions in fixed places answered from its records, each answer showing the record it was read from; the digest says when trials state no phase; the trial count moves from the facts row to the section.

## Impact

- `docs/adr/0003-*.md` (new): a model may read a stored record into a fixed code; it never decides a status and never writes a sentence a reader sees.
- `pipeline/src/thenwhat/readings/` (new package): `rules.py` (pure checks), `service.py` (propose, check, store); a CLI command in `pipeline/src/thenwhat/cli/`; a step in `thenwhat prepare`. Uses the configured provider and the usage ledger of `llm-usage`.
- Database: a new table for readings (a new migration, not an edit of the initial one, if any database holds real claims by then).
- Export: each exported trial gains its readings. `site/export.schema.json` and `site/data/seed-export.json` are regenerated.
- `site/src/lib/record-brief.ts` (new): a pure function from an exported claim to the rows. Wording per question and answer code beside the status wording, under `assertNeutral`.
- `site/src/components/RecordBrief.astro` (new), rendered from `site/src/pages/[slug].astro`.
- `site/src/styles/global.css`, `DESIGN.md`, `GLOSSARY.md`, `site/tests/site.test.mjs`, pipeline tests with recorded fixtures and a recorded model response; no live calls in tests.
- `openspec/changes/plain-claim-page`: its third requirement and task group 3 are removed there.
