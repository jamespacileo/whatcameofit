# Design

## What a merge moves, and what it leaves to be found again

A claim holds two kinds of thing.

**What articles reported.** Source articles, the promises and reported statements read from them, the link leads that led to them, the names the intervention goes by, and the papers, organisations and people an article named. None of this depends on which of two duplicate claims an article was filed under. It moves.

**What a registry was found to say about this claim.** A match on the intervention is a scored judgement that a registry record tests *this claim's* intervention for *this claim's* indication: its score and reason codes were worked out from the merged claim's names and indication, and its review decision (by rule, assistant or person) was a decision about that pairing. An evidence event belongs to one claim and one match (`uq_evidence_event_claim_dedupe`), and a status lists the events that produced it.

**Decision: matches on the intervention and all evidence events stay with the merged claim. The kept claim's registry search is marked due, and `prepare` finds the records again under every name the kept claim now has.**

Why not move them:

- **A copied approval is a decision nobody made.** A match approved by a person for the merged claim would arrive on the kept claim as `human`-approved, for a claim (and, with `--different-indication-accepted`, an indication) that person never looked at. CLAUDE.md: never record a script's decision as `human`; never approve by score alone a candidate scored without the indication. The score itself would be for other names.
- **The status must be explained by events found for the claim.** After the search, every event behind the kept claim's status was fetched for the kept claim from a match scored for the kept claim. No status ever rests on a row whose provenance is "moved from another claim".
- **Collisions have no right answer.** Both claims usually hold the same trial. One match would have to win, with its score, reasons, decider and events; the loser's events and failure flags would be dropped or re-pointed. Finding again has no such case.
- **It is cheap.** Registry answers are in the HTTP cache, and the kept claim gains the merged claim's names as synonyms, so the same searches are sent.

What this costs: a match a person approved on the merged claim is decided again by the rule on the kept claim, and may come back as a candidate in the lower band. So the command lists the merged claim's approved records the kept claim does not hold approved ("to look for after the search"), and the operator checks those after `prepare`. Until `prepare` runs the kept claim keeps the status it had; it can only gain events. Nothing is deleted: the merged claim keeps its matches, events and failure flags as history.

**Papers, organisations and people move with their matches.** A match on a paper or an organisation says *which paper or organisation the name is* (a DOI, a ROR record). That does not depend on the claim's indication, so the entity row moves and its matches come with it. Three limits:

- One the kept claim already has (same type and name or synonym, or the same DOI) is not moved: the kept claim's entity gains its other names.
- One that only a registry record named (a trial's lead sponsor) stays: it follows from a trial match, and comes back when the kept claim's search finds that trial. An entity an article *and* a registry named moves marked as named by the article alone.
- The kept claim keeps its own origin paper; a moved origin paper becomes an ordinary paper.

Follow-up-paper events already fetched for the merged claim stay there, like every event. `fetch` makes them for the kept claim from the moved, approved paper matches.

**An article both claims have** (same address as written) is not doubled: the merged claim keeps its copy, and that copy's promises, statements, entity links and link leads move to the kept claim's copy where it lacks them.

**Names.** The merged intervention's name and synonyms become synonyms of the kept intervention; search phrases are joined. Every synonym is sent to the registries, so a name that breaks an entry rule is refused as a synonym: the operator gives `--drop-name` for a duplicate named by a description. A name a third claim stands for, for the kept indication, refuses the merge and names that claim.

## The pointer, and why a merged claim stands for nothing

`claim.merged_into_id` points at the kept claim; a check constraint makes a merged claim archived. The archive reason is `merged into <slug>: <reason>`. `unarchive` refuses a merged claim: its articles are elsewhere.

The merged claim keeps its intervention entity and names. Left alone, every duplicate check (`slug_of_claim_covering`, `slug_of_claim_close_to`, `claims_sharing_a_name`, `claims_of_a_named_substance`, `named_claims`) would find the merged, archived claim first and send the operator or a link lead's read to it. Each now leaves merged claims out, so the kept claim answers for every name.

Merging A into B when C was merged into A re-points C at B, so an address never leads through two claims.

## One mechanism for an address that moved

Two things leave a published address without a page: a merge (the claim row and its slug remain) and a rename with `--reslug` (the slug is replaced). Storage differs with the case: `claim.merged_into_id` for the first, `claim_change.former_slug` (unique) for the second. `moved_addresses()` joins them into one list, and from there on there is one mechanism:

- the export's `moved: [{slug, to}]`, listed only when the claim it leads to is published in that export; otherwise the address is listed in `archived` when that claim is archived, as before;
- `site/scripts/redirects.mjs` writes moved entries into `dist/gone.json` beside archived ones;
- the Worker, which already runs first for every page address, answers `{slug, to}` with `301` to `/<to>`.

A redirect was chosen over a "now at" page: it needs no wording, search engines carry the old address's standing to the new one, and shared links keep working. The redirect is answered by the Worker, not `dist/_redirects`, because the Worker is already where an archived address is decided and its behaviour is tested (`site/tests/worker.test.mjs`).

A former slug stays taken: `slug_in_use` refuses it to a new claim. A claim renamed back takes its own former slug again.

`rename-slug` is unchanged: still refused once published. Only `entity rename --reslug` changes a published slug, because only it leaves the old address leading somewhere.

## Who decided

`claim_change` keeps one row per merge or rename: the claim, the kind, the kept claim or the old and new names, the former slug, the reason (private, like an archive reason) and `decided_by`, constrained to `human` or `assistant` as link-lead labels are. Both commands take `--as-assistant`.

## A registry search that is due

`resolve` is not in the work ledger: `prepare <slug>` always runs it, and `prepare --pending` picks claims awaiting review only. A renamed, published claim would never be picked. So `claim.registry_search_due_at` is set by a rename and on the kept claim of a merge; `prepare --due` plans every claim that has it; and `thenwhat resolve`, when it succeeds, clears it. The development codes kept for the intervention are replaced by that same `resolve`, which asks the substance registry under the new name.

## Entry rules for a name

`name_refusal` names the rule a new name breaks: brackets; a dose, schedule or form (`_DOSE`, `_HOW_GIVEN`, the same patterns `core_name` strips); a description or class (`is_a_name`, `is_a_class`, or words saying what it is for); a maker (a company the claim names sitting beside other words, or a possessive first word such as "Pfizer's"). The maker rule knows only the claim's own companies: a maker the claim does not name is not caught.

## Seams

Functions taking a session against the test database: `merge_claims`, `rename_intervention`, `moved_addresses`, `plan_claims(due=True)`, `build_export`. One success and one refusal for `claim merge` and for `entity rename`. The pure `name_refusal` is tested by table.

## After the review of pull request 275

**A hold for audit is never dropped by a merge.** The first version cleared the merged claim's hold and moved its articles into the kept claim, which, when published, would have carried unaudited content to the site (ADR 0007). Now the merged claim keeps its hold, and when it was held and the kept claim was not, the kept claim is held from the same time. It leaves the site at the next export until `thenwhat audit clear`. `--awaiting-audit-accepted` is still required, and the command says in capitals that the kept claim is off the site.

**A lead's read is left as the read wrote it.** Only `claim_id` and `source_article_id` move. `read_outcome` and `read_detail` are untouched, so the funnel report, which groups on `read_detail`, and the question "which lead drafted this claim" keep their answers. The merge's record lists each lead with the claim and article it pointed at. Known consequence: `decide_prepared_lead_claim` decides by rule any *pending* claim a `new_claim` lead points at, so a merge into a pending, operator-entered claim makes `prepare` decide that claim. The outcome of that rule is approval held for audit, or rejection; nothing reaches the site unheld. Listed in tasks 5.3.

**Two treatments for one indication are not merged.** Equal indications say nothing about the interventions. A merge now needs a stored sign that the two are one treatment: a shared name or synonym, the same substance record, or a development code of one that the other has or is known by. Without one the decider must give `--same-treatment-accepted`, and the record says `stated_by_the_decider`. The three pairs found on 2026-11-16 are of that kind: their names share nothing.

**A merge can be undone.** `claim_change.record` holds, by id, every article, promise, statement, lead pointer, screening link, entity, entity-article link and match the merge moved, the names and search phrases it added, the claims it re-pointed, whether the merged claim was already archived and whether the kept claim took a hold. `thenwhat claim unmerge <slug> --reason` puts back exactly those rows, and only where they are still where the merge left them. It does not touch what either claim gained since: in particular, registry matches found for the kept claim under the names it now loses stay with it, and the command tells the operator to look at them. The change row is kept, marked undone with who and why. A merge made through a later merge (A into B, then B into C) is undone from the outside in.

**Smaller corrections.** A claim archived before its merge keeps that date and reason. A moved entity keeps its `registry` mark. When the kept claim already has the paper or organisation, the matches saying which one it is move to the kept claim's entity where it lacks them. A synonym of the merged intervention that breaks an entry rule is left out and reported. Two person entities are never joined on a name: the merged claim keeps its own. A claim that takes a former slug back leaves the earlier change row as written; the export skips a former slug that is the claim's current one. The redirect is cached for five minutes, not an hour.

**Migration.** `0032`, additive: two nullable columns and a new empty table, nothing backfilled. The pipeline image runs `alembic upgrade head` when it starts, so it is applied by the next `docker compose up` after merge.
