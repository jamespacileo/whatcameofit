# Proposal

## Why

The tracker is article-first: a news article drafts a claim, and registry trials are matched to the claim. On 2026-11-16 every interventional study on ClinicalTrials.gov was stored (467,064 registry trials), but a trial reaches the site only through a claim. 708 claims are published and they cite 3,073 trials: under 1% of what is stored.

The operator's ambition is every clinical trial tracked, and three things were decided that day:

- A trial that no article links to gets a plain registry page: state, phase, dates, a link to the registry, and that no report is linked yet.
- "Successful" is never a word on the site. A trial shows registry facts only.
- All trials are kept current by a daily load of what the registry changed.

Three measurements taken for this proposal shape what follows (`design.md`, Context):

1. **A headline does not identify a trial.** Screening's name link was judged on 40 sampled links. None of 20 drawn at random was a report of the trial it was linked to, and 12 of them matched on an ordinary word or a class of treatments ("protein", "diet", "test"). Among 20 links whose name few trials carry, 4 named the right treatment for the right condition, and each of those names was a development code or an invented drug name. A headline names, at best, a treatment and a condition. That is a claim, not a trial.
2. **The stored record cannot yet fill the page.** The bulk load keeps ten fields. It has no completion date, no posting of results, no date of last change and no sponsor name, so "recently completed" cannot be chosen from stored data today.
3. **Money is not the limit.** Every stored lead that triage passed or held and that is still unread is 8,643 reads: about 23 US dollars. The limits are the page reader, the audit of each batch, and how few trials the news ever reports. After every stored lead is worked, at most about 4% of stored trials would be cited by a claim.

So the route is not "search the news for each trial". It is: give every trial a page of registry facts, and let stored leads find their trials offline, in an order the operator chooses, through the reading and audit path that exists.

## What Changes

- **A trial has a page whether or not a claim cites it.** One address for each trial. It states what the registry record states, by fixed rules, with the date the record was read. It carries no status, no gloss, no score and no word about how the trial turned out. When no published claim cites the trial it says so in one fixed line. **BREAKING** for `registry-corpus`: a registry trial is no longer kept off the site.
- **The trial page words a trial's state as the rest of the site does.** Under way, never "recruiting". **BREAKING** for `trial-records`: the page that exists today shows the registry's own status words, which include "Recruiting".
- **The bulk load keeps more of each record**: sponsor name, completion dates, enrolment, the reason a trial stopped, whether and when results were posted, and when the registry last changed the record. About 0.9 KB a trial in place of 0.6 KB.
- **The daily load of changes is the change `daily-trial-refresh`'s** (pull request 268), not this one's: about 500 to 950 trials a day, one or two requests. This change adds what a changed trial makes due, and what a load never starts: no read, no page fetch, no news search, no new claim. A load starts no step at all.
- **A link from a lead to a trial is strong only on a telling name.** A development code, or a name a substance registry lists and headlines rarely hold, together with a word of the condition. Only a strong link changes what is read. The link screening makes today stays, as the weak signal it is.
- **Reads are worked in sets the operator names**: trials under way in phase 3 first, then under way in phase 2, then recently completed. A set only orders the reading. It says nothing of how any trial turned out.
- **A trial-first read is an ordinary read.** It drafts a claim or joins one, is prepared, and waits for its audit (`docs/adr/0007`). A link attaches nothing to a trial by itself: a lead is never shown on a trial page.
- **One record for each trial serves both pages.** A claim page and the trial page state a trial's facts from the same stored record. When the daily load changes a trial a claim cites, the daily run's existing refresh takes that claim first, and no export is written until it has.
- **Before pages can be served from the store**, a listing of a chosen set of trials is built into the static site, and the trial page that exists today, which reads the registry on request, may open for trials in that listing. Whether it does is the operator's decision.

- **From the trial's end** (added 2026-11-17 at the operator's request): for a trial with recent registry activity and no linked article, a fingerprint is built by rule (number, acronym, codes, telling names, sponsor) and coverage is looked for by routes in a fixed order, free and exact first: the papers the registry record names; papers that carry the trial's number; stored leads matched on the fingerprint; a news search that carries about ten trials a request. Wires, paid search and a mentions index are specified, off, and wait for the operator.
- **An experiment decided the shape of the news search.** In 19 requests: about ten trials fit one request before the index times out, not fifty; about one hit in twenty can be given back to a trial; of 28 tied hits judged, 10 named the right drug and none the right trial.
- **Papers on a trial page.** The papers a registry record names, and papers whose own record carries the trial's number, are listed as papers. They say nothing of how a trial turned out and are never a news report.
- **Every article any route finds goes through the path that exists**, unchanged: triage, the page reader, the same-claim decision, drafting, preparation, the audit hold.

Not in this change:

- A news search for each trial, one request a trial. The source allows 4,000 requests a week, and 209,439 trials are due.
- Any new status, verdict or summary of how a trial turned out. "Results posted" is a registry fact. "Successful" is not a word.
- Lighter publishing for claims this route drafts. The audit hold stands.
- Claim pages served on request. They stay built (`cloudflare-source-of-truth`, decision 8).
- Registries other than ClinicalTrials.gov, and regulators' decisions for a trial no claim cites.
- Searching a press-release wire's own site, which their terms forbid, and an encyclopedia route, which 17 trials would use.
- Readings by a model of a trial no claim cites.

## Capabilities

### New Capabilities

- `trial-pages`: what a trial is on the site without a claim: the record, the page, what it states and never states, its fixed wording, how it differs from a claim page, the listing built into the static site, and that both pages read one record.
- `trial-report-links`: how stored leads are linked to trials with no request and no model: telling names, strong links, named sets, what a strong link may change, and what a read on this route becomes.
- `trial-coverage`: looking for papers and news from a trial's own end: the fingerprint, which terms may be sent to a source, the two sets, the routes and their order, how a hit is tied to a trial, that a source is checked before it is asked, and that every article found goes through the existing path.

### Modified Capabilities

- `registry-corpus`: the stored record gains fields; what a change makes due; a load reports which cited trials changed and starts nothing; a registry trial may be shown on its own page and in the trial listing, and is still not evidence.
- `daily-run`: its existing refresh takes first the claims that cite a changed trial, and its summary counts them. This capability is created by `daily-trial-refresh`, not yet synced; the requirements here are added beside that change's and apply after it.
- `trial-records`: which identifiers the trial page answers for, and the words it uses for a trial's state.

`lead-screening` and `lead-reading` are specified in `openspec/changes/archive/2026-11-18-social-link-backfill`, not yet synced. This change adds to them through `trial-report-links` and changes none of their requirements; the two places they meet are named in `design.md`, decision 5.

## Impact

- **Decision to record (ADR 0010):** a registry trial has a public page of registry facts without a claim; the facts a page may state; "successful" is never a word. It amends the glossary's "Registry trial" ("never exported") and `CLAUDE.md`'s layout notes.
- **Depends on:** `daily-trial-refresh` for the daily load; `cloudflare-source-of-truth` for a page for every stored trial (the store is what answers for 467,064 trials). The wider load, strong links, the phased reading and the listing of a chosen set need nothing from it.
- **Affects `cloudflare-source-of-truth`:** its size criterion was measured with 43,320 registry trials. The store now has to hold 467,064, with wider records. Estimated 0.6 to 0.9 GB more; to be measured there before the migration.
- **Code:** `pipeline/src/thenwhat/sources/clinicaltrials.py` and `backfill/registry_load.py` (fields, what a change makes due), `scripts/daily-run.sh` (refresh order, summary), `export/` (the hold), `backfill/link_screen.py` (strong links), `backfill/link_read.py` (order), `export/` (the trial listing), `site/worker/trials.mjs` and `site/src/lib/trial-links.mjs` (the page and the listing), the site's wording module (state phrases).
- **Spend:** at most about 27 US dollars to triage and read every stored lead that could be read today; each set is a few dollars. A load starts no spend; the daily run's refresh spends as it does today, within its own limit.
- **Guardrails restated:** no verdicts, no medical advice, no article text, no model decides a status, a lead is never published, the site owns all wording.
- **Sources:** the registry's terms were checked on 2026-11-15 (`docs/sources.md`); the field list of the bulk load changes and is noted there before the client is changed. PubMed's E-utilities, the wires' feeds, the paid news searches and Altmetric are not in `docs/sources.md`: what public pages said on 2026-11-16 is cited in `design.md`, decision 13, and each needs its dated entry before any client.
