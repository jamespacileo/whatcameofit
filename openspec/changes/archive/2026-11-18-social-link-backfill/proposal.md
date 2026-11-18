# Proposal

## Why

The tracker holds about a hundred claims, each entered from an article someone picked. The registry-first backfill (`backfill-work-ledger`) starts from trials and finds that most coverage it reaches is trade press, with no check that a found article reports the trial. The other direction is missing: starting from the articles readers were actually shown and shared. Public link archives hold those addresses with their dates. A count on 2026-11-14 found Hacker News stories linking to statnews.com (1,091), sciencedaily.com (4,339), medicalxpress.com (2,725) and eurekalert.org (1,450) alone.

Reading an article costs a fetch from its outlet and a model call under a monthly ceiling of 13 US dollars. Most shared links are not about a treatment. So the work has to be ordered cheapest first: rules and stored data before any model, a cheap decision on the title before any article is fetched, and a measured sample before anything is read at volume.

## What Changes

- Add **link leads**: article addresses shared on Hacker News and in chosen Reddit communities, loaded from bulk files, one per article address, with where and when each was shared. Never the author, the post or its comments.
- Add **screening**, by rule and from stored data only: a lead on an outlet the project lists goes on; a lead whose address is already a source article is finished; a lead is linked to the registry trials, claims and article leads the database already holds for it, so that later steps do not search for what is already known.
- Add **triage**: a decision step that scores, from the title alone, whether a lead reports a specific treatment for a specific condition. Rules on that score pass, hold or reject the lead. No article is fetched.
- Add **evaluation**: the operator labels a sample drawn across the score range without seeing the scores, and a report gives precision and recall at each threshold. No article is read from a lead until enough labels exist for the current triage and the operator has set the thresholds.
- Add **reading**: a passed lead's article is read once, with the existing extraction. It becomes a source article of the claim it reports, or a new claim, which is decided and published by the rules that already apply. Trials and papers the screening or the article's own page already identified become candidates without a search.
- Extend the **work ledger** so a step may ask no source, may spend model budget in place of source requests, and may take several records in one call. `backfill plan` reports the model spend a step's due records need against what is left this month.
- Reddit's dumps are used on the operator's decision of 2026-11-14 (`docs/sources.md`, "Reddit submission dumps"), within the limits written there.

Not in this change:

- Changing where `thenwhat resolve` searches. It keeps asking the registry once per claim. Whether the stored registry trials can answer in its place needs its own measurement against approved matches.
- Bluesky, the Crossref Event Data archive and Wikipedia's external links. Each needs its terms read first; the loader is built so that a new platform is one more reader of one more file format.
- Showing on the site where an article was shared, or how often.
- Links to papers, registries and preprints. A claim needs a news article; a shared paper link is counted in the screening report and goes no further.

## Capabilities

### New Capabilities

- `link-leads`: article addresses shared on social platforms, loaded from bulk files and kept once per address with platform, community, date and score; what is never kept; that a lead is never published.
- `lead-screening`: the rule checks and joins against stored data that decide whether a lead goes on, and which stored trials, claims and article leads it is linked to.
- `lead-triage`: the decision step that scores a lead from its title, and the rules that pass, hold or reject it.
- `lead-evaluation`: sampling, labelling and reporting on triage quality, and the gate that keeps leads from being read before the operator has measured it.
- `lead-reading`: reading a passed lead's article once and making it a source article of an existing claim or a new claim, reusing what is already identified.
- `work-ledger`: steps that ask no source, steps that spend model budget, and steps that process several records in one call. This capability is introduced by `backfill-work-ledger`, which is complete and not yet archived; this change adds requirements to it and must be archived after it.

### Modified Capabilities

None. A claim drafted from a lead is created, decided and published exactly as one drafted with `thenwhat extract new`. Decision steps, model usage and claim rules are used as they are.

## Impact

- **Database:** new tables for link leads, their links to stored records and their labels, in one new migration. `decision_log` and `llm_usage` gain rows, not columns.
- **Pipeline code:** new modules in `thenwhat/backfill` for loading, screening, triage, evaluation and reading; new `backfill` subcommands; the runner and the plan gain batch and model-spend handling. An address comparison in Python that agrees with the site's (`site/src/lib/article-key.mjs`).
- **External services:** none new for Hacker News beyond the file the loader reads; its entry in `docs/sources.md` is extended with the bulk file's origin and terms before the loader is written. Reddit is asked nothing: files are downloaded by the operator. Outlets are asked for articles as today, with robots.txt, plus a shared interval per outlet. The decision backend and the model are the configured ones.
- **Cost:** triage sends titles only. At the Decisions API's price in `docs/sources.md` (0.10 US dollars per million input tokens) a million titles is about 30 US dollars, measured on the first live run at about 300 input tokens a title; the plan command gives the figure before a run. Reading is the expensive stage and is bounded by the existing monthly ceiling.
- **Site and export:** no new field. The export grows only by the claims and source articles that reading produces, through the existing rules. A link lead, its score and its label never reach the export.
- **Documentation:** `GLOSSARY.md` gains link lead, screening, triage and lead label. `docs/sources.md` gains the Hacker News bulk file, and the limit on Reddit titles is corrected: a title is kept with its lead, privately, because the operator labels from it.
