# Tasks

## 1. Sources and files

- [x] 1.1 Read the current terms, authentication, size and field list of the Hacker News bulk candidates (the public parquet archive, the BigQuery public dataset, the search interface queried by domain) and write an entry for each in `docs/sources.md` with the date checked; verify each entry states whether bulk download is permitted and what the operator must set up. Done 2026-11-14 for the parquet archive in full. The BigQuery entry records that its terms were not read (it needs a Google Cloud project of the operator's and was not needed for the choice), and the search interface's rate limit is recorded as unconfirmed
- [x] 1.2 Pick one Hacker News file source in `design.md` decision 3 and tell the operator; verify the decision names the source, how the operator obtains the file and its size, or states plainly that none qualifies and Hacker News is not loaded
- [ ] 1.3 (waits on the operator: no Reddit file is on this machine yet; the reader is written against the field names in `design.md` and tested on synthetic lines) Have the operator download one Reddit per-community submissions file and check its field names against `design.md` decision 3 without printing any line; verify the fields for address, community, time, score, title, self post and removal are recorded in `docs/sources.md`, with the release the file came from
- [x] 1.4 Correct the Reddit entry's limits in `docs/sources.md`: the title is kept with the lead, privately, and why (`design.md` decision 4); verify the entry and `specs/link-leads/spec.md` say the same thing about what is kept
- [x] 1.5 Add link lead, screening, triage and lead label to `GLOSSARY.md`, stating that a link lead is neither an article lead nor a source article; verify the terms match the words in the specs

## 2. Ledger additions

- [x] 2.1 Let a step declare that it asks no source, and make the plan and the run skip the allowance for it; verify a test plans and runs such a step with no allowance configured and no request counted
- [x] 2.2 Let a step declare model spend with estimated tokens per record, and add the estimated cost, the ceiling remaining and the records it covers to `backfill plan`; verify a test checks the figures against seeded `llm_usage` rows, and one checks the refusal when prices are not configured
- [x] 2.3 Stop a model step's run when the ceiling is reached, leaving records due with attempts unchanged; verify a test reaches the ceiling part way and a restart in the same month processes nothing
- [x] 2.4 Let a step declare a batch size: lock a batch with skip-locked, run it in one transaction, and on failure process its records one at a time; verify tests cover five batches over 100 records, one bad record in a batch of twenty, and two sessions over 200 records with each processed once
- [x] 2.5 Verify the existing ledger tests and the news search step pass unchanged

## 3. Link leads

- [x] 3.1 Add migration `0016` with the link lead, share, link and label tables (`design.md` decision 1); verify `alembic upgrade head` then `alembic downgrade -1` both succeed on the test database
- [x] 3.2 Move the site's address comparison cases to a fixture both sides read, and write the pipeline's address key; verify the pipeline's test and the site's test pass on the same cases file
- [x] 3.3 Write the Hacker News reader and the Reddit reader, each turning one line into a lead's fields or a skip reason; verify tests use synthetic lines only and cover a link post, a text post, a removed post, a link to the platform itself, an unusable address and, for Reddit, a community that is not configured
- [x] 3.4 Verify with a test that a Reddit line carrying an author, an id, a permalink and text stores none of them, and that no log line holds them
- [x] 3.5 Add `thenwhat backfill load-links` with its report; verify one test of a load that reports its counts and sends no request, one of the same file loaded twice adding nothing, and one of the refusal for an unknown platform
- [x] 3.6 Add `LINK_LEAD_SUBREDDITS` to the configuration and `.env.example`; verify a Reddit load refuses and names the setting while it is empty
- [x] 3.7 Verify with a test that the export is byte-for-byte the same before and after a load

## 4. Screening

- [x] 4.1 Implement the `link_screen` step with the outlet rule and the already-tracked check through the address key; verify tests cover a listed outlet, an unlisted domain, and an address that is a claim's source article with a tracking parameter added
- [x] 4.2 Implement the links to stored records with their reasons and the cap per lead; verify tests cover an address stored as an article lead, a title naming a claim's intervention, a name inside a longer word, and a trial's name without a word of its indication
- [x] 4.3 Verify with a test that a screening run sends no request, calls no model and records no spend
- [x] 4.4 Add `thenwhat backfill links`, the screening report with the top unlisted domains; verify one test of its counts on seeded leads and one of its message when nothing is screened
- [x] 4.5 Describe loading and screening in the README's pipeline section; verify the documented commands run as written against the Compose stack. Run on 2026-11-14 with synthetic files against a throwaway database on the Compose Postgres server, through `uv`, then dropped. The pipeline image was not rebuilt and the operator's `thenwhat` database was not migrated: other worktrees share it

## 5. Triage

- [x] 5.1 Add the triage decision (options, question, what it is shown) to the decision steps and implement the `link_triage` step in batches of twenty, storing the score and its version; verify tests with a fake backend cover a scored batch, a lead out of scope never asked, and a refusal for one lead leaving it without a score while the others are scored
- [x] 5.2 Add `LEAD_PASS_ABOVE` and `LEAD_REJECT_BELOW` with no defaults to the configuration and `.env.example`, and compute passed, held and rejected from them; verify tests cover thresholds unset (nothing passed), and a lowered threshold passing more leads with no new decision logged
- [x] 5.3 Verify with a test that raising the step's version makes every lead in scope due and keeps the earlier decision log entries
- [ ] 5.4 (waits on the operator: recording needs one live call with the OpenAI key, which was not used) Record a fixture of one Decisions API answer for a batch of synthetic titles; verify the fixture holds no real title and the backend test reads it with no live call

## 6. Evaluation

- [x] 6.1 Add `thenwhat backfill sample-leads` drawing equal numbers per tenth of the score range across platforms, by seed, without showing scores; verify tests cover a full sample, a thin tenth reported as short, the same seed giving the same sample, and labelled leads left out
- [x] 6.2 Add `thenwhat backfill label-lead` with `--as-assistant`; verify one test of a person's label, one of an assistant's label stored as an assistant's, and one of the refusal for a label that is not an option
- [x] 6.3 Add `thenwhat backfill evaluate-leads` with precision, recall and leads passed per threshold, weighted by each tenth's population, overall and by platform, and the strongest disagreements; verify a test checks the weighted figures by hand for a small seeded set, and one checks that assistants' labels do not enter them
- [x] 6.4 Add the gate to the reading step's start (labels at the current triage version, both thresholds set) with `LEAD_EVALUATION_MIN_LABELS`; verify tests cover too few labels, a threshold unset, and labels counting again after a version is raised and the leads rescored
- [x] 6.5 Verify with a test that the export is the same before and after labelling

## 7. Reading

The article's date is decided: from the page only (`specs/lead-reading/spec.md`, "The article's date"). The outlet's name is decided: from a checked-in list of display names ("The outlet's name", "The article's title").

- [x] 7.00 Name every listed outlet in `OUTLET_NAMES`; verify a test fails when a listed domain has no name or a name is for an unlisted one, and one covers a subdomain, a domain listed by its ending and an unlisted domain
- [x] 7.0 Read a date that a page shows in words in an element known to hold it, and the day from a date as a page gives it; verify tests with synthetic pages cover a date in a tag, a date in words, the tag preferred, and a date that cannot be read

- [x] 7.1 Split drafting so the model call comes first and returns the draft, keeping `thenwhat extract new` and `extract article` behaving as before; verify the existing extraction tests pass unchanged
- [x] 7.2 Add the slug rule from intervention and indication; verify tests cover a long name cut at 60 characters, characters outside the allowed set, and a slug already taken by another claim
- [x] 7.3 Add the vertical decision among the configured verticals with `VERTICAL_ACCEPT_ABOVE`; verify tests cover a confident choice, a choice below the setting creating no claim, and a retired vertical never offered
- [x] 7.4 Add outlet spacing through the allowance table under `outlet:<domain>` with `OUTLET_INTERVAL_SECONDS` and the robots.txt delay; verify a test with two sessions and a fake clock shows two fetches of one outlet are never closer than the interval, and a longer robots.txt delay is used
- [x] 7.5 Implement the `link_read` step: scope and order, the already-tracked check, fetch or snapshot, one read, and the outcomes cannot be read, added to a claim, new claim, and needs a vertical; verify tests with a fake model and fake outlets cover each outcome, a lead held because its claim has enough articles, and an earlier article read despite that
- [x] 7.6 Verify with a test that adding an article to an approved claim leaves its headline, summary, intervention, indication, vertical and review state unchanged and moves its first reported date when the article is earlier
- [ ] 7.7 (not done: a match's reason is a code the site words, and an unknown code fails the site build, so "the article names it" needs a new code, its wording on the site and the export schema regenerated; a claim made from a lead is still searched for in the registry by `thenwhat prepare` as any claim is) Record registry numbers and paper identifiers from the page as candidates with their reason, scored for the claim's indication; verify a test shows such a candidate is pending until scored and is not approved by having been named
- [x] 7.8 Verify with a test that after a read the article's text is in no table, log or cache, and that a second run does not read the lead again
- [x] 7.9 Add `thenwhat backfill funnel`; verify one test of its counts and costs on a seeded database and that it sends no request
- [x] 7.10 Document triage, evaluation and reading in the README's pipeline section and add the new settings to `.env.example`; verify `make check` passes

## 8. First runs

- [x] 8.1 Load the Hacker News file and run screening on a separate database, as the ledger change's first run did; verify the report's counts are recorded in this change, with the unlisted domains shown to the operator
- [x] 8.2 Run `backfill plan` for triage and record the estimated cost beside the month's remaining ceiling; verify the operator has seen the figure before triage runs
- [ ] 8.3 (triage has run on every lead in scope; the sample of 200 has not been drawn for the operator and nothing is labelled) Run triage, draw a sample of 200 and give it to the operator to label; verify the evaluation report's figures are recorded in this change
- [ ] 8.4 If the operator asks for it, reword the triage question, raise the version, run again and evaluate again; verify each round's figures are recorded here with what was changed
- [ ] 8.5 Load, screen and triage the chosen Reddit communities, and have the operator label a further sample; verify the report's platform split holds figures for both platforms
- [ ] 8.6 After the operator sets the thresholds, read 200 leads and record the funnel here; verify the operator is shown the funnel and the claims made, and that no further reading runs before their decision

## First run: what was done on 2026-11-14 (8.1, 8.2, and the triage of 8.3)

- **Where:** a database of its own, `thenwhat_links`, on the Compose Postgres server, with the 43,320 registry trials copied read-only from `thenwhat_backfill`. It holds no claims, so no lead could be already tracked or linked to a claim. The operator's `thenwhat` database was not touched.
- **Files:** the twelve monthly Hacker News files of 2019, 819 MB, downloaded with the operator's go-ahead to `~/Library/Caches/thenwhat/datasets/hackernews/data/2019/`. No Reddit file.
- **Load (8.1):** 370,531 stories read; 242,705 link leads, about 20,000 a month; a month loads in about 21 seconds. About 6,000 stories a month are skipped as removed or deleted and 1,500 as having no link.
- **Screening (8.1):** 35,158 leads in scope (14%): 34,803 general news, 65 health or clinical trade press, 290 press release. 207,547 are on unlisted outlets. The unlisted domains with the most leads are medium.com (12,227), github.com (10,796), youtube.com (6,038), en.wikipedia.org (4,025), twitter.com (3,391), techcrunch.com, theverge.com, arstechnica.com, arxiv.org (2,173), dev.to, nature.com (1,324), reddit.com, zdnet.com and phys.org (1,036). Of these, phys.org and nature.com's news pages are the candidates for the outlet list. Screening every lead takes about six minutes.
- **Two faults the run found, both fixed with a test:** a run kept every processed record in the list it excludes from each query and stopped at 66,000 leads on the database's limit of 65,535 parameters; and a trial named by its own disease was linked to any headline holding that one word. With the second fixed (`link_screen` version 2), leads linked to a registry trial fell from 157 to 35. A look at those 35 shows mostly sound links (ketamine and esketamine for depression, GV-971, MDMA for PTSD, psilocybin) and a few wrong ones from trials the registry names with a common word ("cell", "Diet", "Test", "Weight loss").
- **Plan (8.2):** the plan estimated triage at 0.12 US dollars. A live run of 200 leads showed about 300 input tokens a lead where the estimate assumed 35, so the true figure was about 1.06 US dollars. The operator was told the corrected figure as the full run began, not before deciding on it. The estimate is corrected in the code.
- **Triage (8.3, first half):** all 35,158 leads in scope scored through the Decisions API in about four minutes with four workers: 1,821 calls, 10,619,023 input tokens, 1.06 US dollars. A minute without a connection failed 2,839 questions and, because each of four workers retried the same leads, used up all three attempts of 449 leads; they were scored on a further run with a higher attempt limit. A model that cannot be reached now stops the run with its leads still due.
- **Scores:** 34,460 leads (98%) are under 0.1. The other tenths hold 112, 74, 55, 45, 52, 43, 40, 42 and, from 0.9, 235. So 317 leads are at or above 0.7. Every tenth holds at least 20 leads, so a sample of 200 can take 20 from each.
- **Not measured:** nothing is labelled, so precision and recall are unknown. A look at a few dozen titles suggests the high scores are treatment reports and that low-scored titles holding a word such as "drug" or "trial" are mostly pricing, policy and court stories, with a few arguable misses. That is an impression, not a figure.

## Workflow follow-up

- Archive `backfill-work-ledger` before this change is archived, so that `work-ledger` exists in the main specs.
- Propose as their own changes: answering `resolve` from stored registry trials after measuring it against approved matches; further platforms (Bluesky, the Crossref Event Data archive, Wikipedia's external links) once their terms are read.
