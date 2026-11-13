# Design

## Context

See proposal.md for motivation. What shapes the approach:

- The site owns all wording; the export carries codes. `site/src/lib/status.ts` already holds `STATUS_LABELS` and `STATUS_MEANINGS`, each a `Record<StatusCode, string>`, and runs `assertNeutral` over them at module load, so verdict wording stops the build.
- `STATUS_MEANINGS` is precise and written for a careful reader ("The furthest trial that has started is a Phase 1 trial."). It is shown on the claim page, the method page and in `lookup.json`.
- `ClaimTable.astro` renders every claim list (topic, year, source, approved claims, "other claims" on the claim page). `StatusCell.astro` renders the status in each row.
- `intervention.name` is already in the export and is entered as a name alone, with no maker, mechanism or description.
- Tests in `site/tests/site.test.mjs` are named after spec scenarios and run against a built site.

## Goals / Non-Goals

**Goals:**

- A lay reader can scan a list by name and read each status without knowing trial phases.
- An expert loses nothing: labels, precise meanings and the stage track stay as they are.
- All new wording is fixed text keyed by status code, checked at build.

**Non-Goals:**

- No change to the export, the schema, the pipeline, `lookup.json` or the extension. The extension keeps the label and precise meaning it already receives.
- No summary sentence on year, source or approved-claims pages.
- No text filter, grouping toggle or row expansion.

## Decisions

### A gloss is a third wording table, not a rewrite of the meanings

Add `STATUS_GLOSSES: Record<StatusCode, string>` beside the labels and meanings. The type makes a missing code a type error and the module-load check covers the build failure the spec asks for.

Rewriting `STATUS_MEANINGS` in plain words was considered and rejected: the meanings are the accurate statement of the rule ("in the registries checked", "furthest trial that has started") and `lookup.json` serves them to the extension.

A gloss must not claim more than the status rule knows. "Not yet tested in people" would be wrong for `preclinical_only`, because the rule knows only that no trial was found and the first reports were not recorded as a study in people. Glosses, confirmed by the operator on 2026-11-13 ("Apply it" with the wording as proposed):

| Code | Gloss |
| --- | --- |
| `preclinical_only` | No trial in people on record |
| `no_trial_found` | Studied in people, no registered trial found |
| `trial_registered` | A trial in people is registered |
| `phase_1` | Early trial in people, checking safety |
| `phase_2` | Mid-stage trial in people |
| `phase_3` | Large late-stage trial in people |
| `approved` | Approved by a regulator |
| `failed` | A trial did not meet its main goal |
| `terminated` | Its trials were stopped early |
| `retracted` | The original paper was retracted |

### The summary sentence is a pure function over counts

`topicSummary(counts: Map<StatusCode, number>): string | null` in `status.ts`, with a fourth table of clause forms per code, singular and plural (for example `preclinical_only`: "has no trial in people on record" / "have no trial in people on record"). A phase clause says "has reached", not "is in": the status is the furthest trial that has started, and that trial may have ended. It takes no claims, dates or clock, so it is tested directly and at the built page.

Rules:

1. Zero claims: `null`. The page keeps its count line ("0 reported breakthroughs tracked.") and its existing empty message, and shows no summary.
2. Opening: "Of N reported breakthroughs tracked," then one clause per status present, as "K clause". One claim: "1 reported breakthrough tracked: it clause."
3. Order: `STAGE_PATH` order, then off-path codes in the order of `STATUS_LABELS`.
4. More than four statuses present: name the four with the most claims (ties broken by the order in rule 3), still printed in rule 3 order, then "and M are at other statuses".
5. The lede keeps "Newest first." as a separate short sentence when there is more than one claim, since the table order is unchanged.

Deriving clauses from the glosses by string surgery was rejected: verb agreement would need per-code exceptions, and a table of fixed clauses can be read and checked whole. Every clause, both forms, goes through `assertNeutral`.

### The row link is the name; the headline is plain text under it

The link text becomes `claim.intervention.name`; the headline is a `<span>` below it in the muted text colour at body size, not bold, not underlined. The link is stretched over the cell so the whole row cell stays a tap target on a phone.

The same row is used by the home page's "Statuses set most recently" list, which lists claims. Its "Headlines reported most recently" list is a list of news reports and keeps the outlet's headline as the link.

Putting both name and headline inside the link was rejected: a screen reader's link list would again read twenty words per claim, which is the problem being removed.

### The gloss sits under the status label, in the same cell

`StatusCell` gains one line under the label, in the muted colour and small size already used for `quiet-note`. On the claim page the gloss goes directly under the label in the digest, above the precise meaning. The stage filter above the table keeps labels only; its buttons are too narrow for a second line.

## Risks / Trade-offs

- [An intervention name is long or reads as a description for some claims] → The headline is still in the row. Found during apply: 31 of the 84 published claims have a name over 40 characters, the longest 97, mostly descriptions of interventions that have no product name. They still read shorter than their headlines. Shortening a name is a data change outside this change.
- [A gloss overstates what the rule knows] → Glosses are worded against `STATUS_MEANINGS` one by one and confirmed by the operator before merge.
- [The row gets taller with name, headline and gloss] → The headline is clamped to two lines in lists at desktop width; the full headline is one click away on the claim page.
- [The verdict word list is short, so a gloss could carry a soft verdict it does not catch] → Same exposure as labels today; the wording is fixed text reviewed in the diff.
- [Rows change on five pages at once] → One component renders them all; scenario tests run against the built topic page and the existing row tests cover the rest.
