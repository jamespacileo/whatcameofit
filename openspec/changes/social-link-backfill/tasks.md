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

- [x] 3.1 Add migration `0018` (written as `0016`, renumbered when main was merged) with the link lead, share, link and label tables (`design.md` decision 1); verify `alembic upgrade head` then `alembic downgrade -1` both succeed on the test database
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

- [x] 6.6 Count an assistant's label where no person has labelled, in the figures, the sample and the gate, and say in the report how many labels are a person's, how many an assistant's, and where both exist on how many they agree (operator's decision, 2026-11-14); verify tests cover an assistant's label counting, a person's label overriding it, and the agreement figures
- [x] 6.7 Add `thenwhat backfill spot-check-leads` and `thenwhat backfill label-leads`; verify tests cover the disagreements and the random draw without scores, the same seed drawing again, a lead leaving the list once the operator labels it, a file recorded as an assistant's, and a bad line recording nothing and being named

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
- [x] 7.7 (the recording, its reason code and the site's wording were written by the session on branch `claude/link-read-candidates` as `resolve/named.py`, reviewed and taken as one commit; this branch wires it into the reading step. A paper the page gives only by its PubMed number is not recorded: the literature source is asked by DOI, and reading by PubMed number needs a client change with a recorded fixture) Record registry numbers and paper identifiers from the page as candidates with their reason, scored for the claim's indication; verify a test shows such a candidate is pending until scored and is not approved by having been named
- [x] 7.8 Verify with a test that after a read the article's text is in no table, log or cache, and that a second run does not read the lead again
- [x] 7.9 Add `thenwhat backfill funnel`; verify one test of its counts and costs on a seeded database and that it sends no request
- [x] 7.10 Document triage, evaluation and reading in the README's pipeline section and add the new settings to `.env.example`; verify `make check` passes

## 8. First runs

- [x] 8.1 Load the Hacker News file and run screening on a separate database, as the ledger change's first run did; verify the report's counts are recorded in this change, with the unlisted domains shown to the operator
- [x] 8.2 Run `backfill plan` for triage and record the estimated cost beside the month's remaining ceiling; verify the operator has seen the figure before triage runs
- [x] 8.3 (the sample was labelled by an assistant, under the operator's decision of 2026-11-14, not by the operator; figures below) Run triage, draw a sample of 200 and give it to the operator to label; verify the evaluation report's figures are recorded in this change
- [ ] 8.4 If the operator asks for it, reword the triage question, raise the version, run again and evaluate again; verify each round's figures are recorded here with what was changed
- [ ] 8.5 Load, screen and triage the chosen Reddit communities, and have the operator label a further sample; verify the report's platform split holds figures for both platforms
- [ ] 8.6 After the operator sets the thresholds, read 200 leads and record the funnel here; verify the operator is shown the funnel and the claims made, and that no further reading runs before their decision

## 9. One story, one claim; no claim published unsearched

- [x] 9.1 Add `claims_sharing_a_name`: claims whose intervention name or synonym equals one of the read's names or sits whole inside it, or the reverse; verify with tests that "esketamine nasal spray" finds an esketamine claim and not a ketamine one, that equal names come first, and that no more than the fixed number come back
- [x] 9.2 Add the `same_claim` decision step, shown treatments and conditions only; verify with a test that what it is shown holds no word of the article
- [x] 9.3 In `link_read`, ask the decision when no claim is equal as written, with the claims screening linked by title as further candidates, and join only at or above `SAME_CLAIM_ACCEPT_ABOVE`; verify with tests of four synthetic reads shaped like the esketamine story (one claim, four articles, the first wording kept), of "none of these", of an unsure decision, of a read that shares no name, and of a title-linked claim
- [x] 9.4 Take an advisory lock before the claim is settled and hold it to the end of the read's transaction; verify with a test that another connection cannot take it while a read's transaction is open
- [x] 9.5 Leave a named claim pending at the read and reject a description at once; have `thenwhat prepare` decide a read's claim by the rule for drafts once every step succeeded; verify with tests of a prepared claim, a failed step, and a pending claim no read drafted
- [x] 9.6 Count claims awaiting preparation in `thenwhat backfill funnel`; update the README and `.env.example`; verify `make check` passes

- [x] 9.7 Join by the probability that the article reports one of the candidates (one minus "none of these"), at 0.6 unless set, with more than half for the claim joined; verify with tests of a fairly sure same story, a vote split with a clear leader, a near tie between two conditions, and a decision leaning to none
- [x] 9.8 Leave rejected claims out of the candidates; verify with a test that a read sharing a name only with a rejected draft asks no decision

- [x] 9.9 Add the `new_treatment_report` decision and the read outcome `not_a_new_treatment` (migration `0019`), asked before any claim is joined or drafted, at `NEW_TREATMENT_ACCEPT_ABOVE` (0.5 unless set); count it in the funnel; verify with tests that such an article drafts no claim, joins no claim, and that the decision is shown none of the article's text
- [x] 9.10 Measure the decision on the 141 drafts of the reread before switching it on; verify the figures and what the low group holds are recorded in the design

- [x] 9.11 Replace the yes-or-no check with the three-way `treatment_kind` decision, so that an established treatment joins or drafts a claim as a new one does and only "neither" refuses; rename the outcome to `not_one_treatment` (migration `0020`) and the setting to `TREATMENT_ACCEPT_ABOVE`; verify with tests of an established treatment drafting a claim, joining its claim, an unsure split between new and established, and "neither" drafting and joining nothing
- [ ] 9.12 Measure the three-way decision on the leads the first check refused, by rereading them, and record the figures here before any of them is prepared
- [x] 9.13 Add `resolve --redo-rule`: score again the trial matches a rule approved, as the question is asked now, and let the rule decide again; a match no longer approved loses its events and the status is derived again. Verify with tests of an approval that no longer stands, one that stands, one a person decided, and a scoring that fails
- [x] 9.15 Give the trial question a fourth answer, in the trial but not what is tested, never approved by rule; verify with tests of the rule, the review note and the site's wording, and measure it on the claims the audit named
- [ ] 9.14 Run it over the claims the audit held for a trial that does not test the claim's treatment, and record how many approvals and statuses moved
- [x] 9.16 Mirror the fourth answer in the site worker's copy of the trial question (`site/worker/model.mjs`). The `corpus-match-accuracy` change accounts for all 258 rows and replays 2,023 candidates from 93 applicable saved readings, with direct-card/negative/empty/unavailable paths and remaining identity limitations recorded separately. It also fixes omitted search fields and truncated setting/role evidence. This is candidate validation; released/native checks remain in that change's tasks.

## 10. Targets and topics

- [x] 10.1 Add `backfill/topics.py` with the GLP-1 topic's words, and the rule for a title naming one; verify with tests that a word is matched whole and in any letter case, and that an unknown topic is refused by name
- [x] 10.2 In `link_read`, read leads that name a topic first, and read held leads that name one; verify with tests of a held lead on a topic, a held lead on none, a rejected lead on a topic, a topic lead ahead of a much-shared lead, and no topics listed
- [x] 10.3 Add `thenwhat backfill topics`; verify one test of the leads' standings, one of a claim's articles, trials, papers and cards, and one success and one refusal of the command
- [x] 10.7 Give the decision after the read a fourth answer, business news about a treatment, and for a lead that names a topic join or draft a claim only when the article is about what the treatment does; add the outcome `business_news` (migration `0021`) and count it in the funnel; business news never starts a claim for any lead, and joins an existing one only off a topic; verify with tests of a shortage story on a topic, a trial result on a topic, business news with no claim to join, business news joining a tracked claim off a topic, and a lead whose title names nothing while its read names a topic's drug
- [x] 10.8 Score the leads that name a topic first in triage, since triage works oldest first and a topic's news is recent; verify with a test that a topic lead among twenty-five older ones is in the first call
- [x] 10.9 End a lead whose read names a class of treatments as not one treatment, by a checked-in rule on the name and before any decision; verify with tests of class names with and without a code, of single treatments, and of a read that asks no decision
- [x] 10.10 Ask the read for one condition by the name a registry files it under, never an aim or an outcome
- [x] 10.12 Tighten the class rule after the reread let four class names through ("GLP-1s", "GLP-1 drugs for obesity", "GLP-1 metabolic therapy", "GLP-1 and/or GIP receptor agonist prescriptions"): a class word anywhere, the plural of a code, a trailing "for", and a topic's class word with no drug and no name left
- [ ] 10.11 Take the GLP-1 claims no one has prepared back out, read their leads again, and record how many claims the topic then has
- [ ] 10.4 Add the news outlets that carry topic leads and are on no list; set the outlet kind again on stored leads and screen them again
- [ ] 10.5 Have background cards made for every claim a read drafted, as part of preparing it, and verify the coverage report shows cards for them
- [ ] 10.6 Report progress against the two targets after each batch: articles on published claims with trials, papers and cards; coverage of each topic

## 11. Two bands for the evidence stage

- [x] 11.1 Record the operator's decision as ADR 0004 and in the guardrail of `CLAUDE.md`
- [x] 11.2 Export a lower-band stage reading as `evidence_stage_reading`, behind `STAGE_SHOW_ABOVE`; verify with tests of a shown reading that leaves the status alone, a reading under the band and a confirmed stage; regenerate the export schema and the seed export
- [x] 11.3 Show the reading on the claim page, marked low confidence with its score and the other stages weighed; verify the wording with a site test
- [ ] 11.4 Re-score the stored trial matches of the first batch on current main, after the auditing session's first publish, and record how many statuses moved

## Reread: what the 200 showed on 2026-11-15 (8.6, read but not yet prepared)

- **The run:** `link_read --limit 200` with the same-claim check: 141 new claims (103 awaiting preparation, 38 rejected by the name rule), 14 articles joined to a claim, 3 needed a vertical, 55 could not be read. Model cost $0.23. Nothing is approved and nothing is exportable: `thenwhat prepare` has not been run for this batch.
- **Could not be read (55):** robots.txt refused 31 (npr.org 16, wsj.com 5, eurekalert.org 2, reuters.com 2, cbc.ca 2, three others 1 each), the page gave no date 20, the outlet had no display name 2, no page or snapshot 2.
- **Joins:** all 14 are right as far as intervention and condition show, one of them to a claim already published (`dentine-repair-tideglusib`). Five same-story articles still became new claims; the design section above gives the 34 decisions and the rule that follows from them (9.7, 9.8).
- **Rejected by the name rule (38 of 141, 27%):** descriptions and names that end in a kind of thing, among them "HPV vaccine", "MMR vaccine", "VSV-EBOV vaccine", "bariatric surgery", "LASIK surgery", "gene therapy" for haemophilia A, "bacteriophage therapy", "CAR-T cell therapy". Several are the accepted name of the intervention. The rule is the operator's; whether to loosen it is open.
- **Not what the tracker is for (the reviewing session's list, about 20 of the 103):** established drugs in the news for safety or marketing ("OxyContin", "proton pump inhibitors", "paroxetine"), advice and public health ("water fluoridation", "Heimlich manoeuvre", "mindfulness meditation"), an approach for "cancer" with no one indication ("CRISPR gene editing", "CTLA-4 blockade"), and a predictor that is not an intervention ("gut microbiome composition"). Triage passes these as it was measured to: it asks whether a headline reports a treatment for a condition, not whether the report is of something new. Open for the operator.
- **Also open:** indications that hold two conditions ("depression and bipolar disorder"), and three verticals the reviewing session questions.

## First reads: what happened on 2026-11-15 (8.6, begun and taken back)

- **Before reading:** PR 113 merged; the real database migrated to `0018` after a dump. The leads loaded so far (971,734, with the 2019 scores, labels, triage ledger entries, decision records and usage) were copied in once from the separate database, and screening was run again there against the real claims. The operator set the thresholds, pass at 0.7 and reject below 0.1, and raised the month's ceiling to $100.
- **The run:** `link_read --limit 200` was stopped after 52 leads. 39 new claims (27 approved by rule, 12 rejected by rule), none joined to an existing claim, 13 could not be read (11 refused by robots.txt, 1 with no page or snapshot, 1 with no date). Model cost $0.04.
- **What was wrong:** four esketamine claims and three ketamine claims from one story's articles, and every approved claim exportable as "preclinical only" before any registry search. Found by the reviewing session's early audit.
- **What was done:** after a dump, the 39 claims and everything hanging off them were deleted in one transaction and their leads set back to unread; the 13 unreadable outcomes, the decision records and the usage stay. 84 claims, as before. None of the 39 had been exported. Section 9 is the fix; 8.6 stays open until the reread.
- **Also found:** on a busy machine a statement sent from the host to the Compose database's published port took about 19 ms against 0.02 ms inside the Compose network. The loader sends two or three statements a post, so a load from the host fell from about 1,700 posts a second to 34. Loads, screening, triage and reads were run from a container on the Compose network instead. Batching the loader's statements would remove the dependence; not done here.

## First run: what was done on 2026-11-14 (8.1, 8.2, and the triage of 8.3)

- **Where:** a database of its own, `thenwhat_links`, on the Compose Postgres server, with the 43,320 registry trials copied read-only from `thenwhat_backfill`. It holds no claims, so no lead could be already tracked or linked to a claim. The operator's `thenwhat` database was not touched.
- **Files:** the twelve monthly Hacker News files of 2019, 819 MB, downloaded with the operator's go-ahead to `~/Library/Caches/thenwhat/datasets/hackernews/data/2019/`. No Reddit file.
- **Load (8.1):** 371,331 stories read; 242,705 link leads, about 20,000 a month; a month loads in about 21 seconds. About 6,000 stories a month are skipped as removed or deleted and 1,500 as having no link.
- **Screening (8.1):** 35,158 leads in scope (14%): 34,803 general news, 65 health or clinical trade press, 290 press release. 207,547 are on unlisted outlets. The unlisted domains with the most leads are medium.com (12,227), github.com (10,796), youtube.com (6,038), en.wikipedia.org (4,025), twitter.com (3,391), techcrunch.com, theverge.com, arstechnica.com, arxiv.org (2,173), dev.to, nature.com (1,324), reddit.com, zdnet.com and phys.org (1,036). Of these, phys.org and nature.com's news pages are the candidates for the outlet list. Screening every lead takes about six minutes.
- **Two faults the run found, both fixed with a test:** a run kept every processed record in the list it excludes from each query and stopped at 66,000 leads on the database's limit of 65,535 parameters; and a trial named by its own disease was linked to any headline holding that one word. With the second fixed (`link_screen` version 2), leads linked to a registry trial fell from 157 to 35. A look at those 35 shows mostly sound links (ketamine and esketamine for depression, GV-971, MDMA for PTSD, psilocybin) and a few wrong ones from trials the registry names with a common word ("cell", "Diet", "Test", "Weight loss").
- **Plan (8.2):** the plan estimated triage at 0.12 US dollars. A live run of 200 leads showed about 300 input tokens a lead where the estimate assumed 35, so the true figure was about 1.06 US dollars. The operator was told the corrected figure as the full run began, not before deciding on it. The estimate is corrected in the code.
- **Triage (8.3, first half):** all 35,158 leads in scope scored through the Decisions API in about four minutes with four workers: 1,821 calls, 10,619,023 input tokens, 1.06 US dollars. A minute without a connection failed 2,839 questions and, because each of four workers retried the same leads, used up all three attempts of 449 leads; they were scored on a further run with a higher attempt limit. A model that cannot be reached now stops the run with its leads still due.
- **Scores:** 34,460 leads (98%) are under 0.1. The other tenths hold 112, 74, 55, 45, 52, 43, 40, 42 and, from 0.9, 235. So 317 leads are at or above 0.7. Every tenth holds at least 20 leads, so a sample of 200 can take 20 from each.
- **Not measured:** nothing is labelled, so precision and recall are unknown. A look at a few dozen titles suggests the high scores are treatment reports and that low-scored titles holding a word such as "drug" or "trial" are mostly pricing, policy and court stories, with a few arguable misses. That is an impression, not a figure.

## First evaluation: what was done on 2026-11-14 (the rest of 8.3)

- **Labels:** 200 leads, 20 from each tenth of the score range, labelled by an assistant in another session that did not write the triage and saw no score, from the title, outlet and date alone. 87 treatment reports, 92 other health news, 21 not about health. The operator has checked none of them yet; `spot-check-leads` lists 20 disagreements and a random 30. The labeller named 31 leads it was unsure of, about one in six, mostly lifestyle findings, safety findings about a treatment, and enabling technology with no condition named, and wrote down the rule it applied to each group for the operator to accept or change.
- **Treatment reports among the 20 labelled in each tenth, lowest first:** 0, 1, 6, 7, 9, 10, 7, 12, 16, 19. The score does order the leads.

| Pass at or above | Precision | Recall, as reported | Leads passed |
| --- | --- | --- | --- |
| 0.5 | 78% | 83% | 422 |
| 0.6 | 82% | 76% | 364 |
| 0.7 | 89% | 72% | 320 |
| 0.8 | 93% | 66% | 280 |
| 0.9 | 95% | 57% | 237 |

- **What the recall figures do not show:** 34,441 of the 35,158 scored leads are under 0.1, and 20 of them were labelled. None was a treatment report, so the report counts none there. But 0 of 20 only shows that fewer than about 14 in 100 are, which over 34,441 leads allows for several thousand, against about 390 estimated above 0.1. So the recall column is an upper bound that could be far too high. Precision does not depend on this. Equal numbers from each tenth was the wrong plan for scores this lopsided.
- **What was done about it:** `sample-leads --tenth` draws a whole sample from one tenth. A second batch of 360 leads, 300 from the lowest tenth and 60 from across the range, shuffled together so that the batch says nothing of a lead's score, is with the same labeller. With 300 labelled and none a report, the lowest tenth would hold fewer than about 1 in 100.
- **Precision by the labeller's rules:** the strongest disagreements are mostly about where a treatment report ends: a safety recall of a drug, a first-of-its-kind operation, a headline that names an approach and a disease without a result. They are differences of definition between the triage question and the labeller's rules more than errors of either, and the operator's spot-check is where that is settled.

## Second batch of labels: what the lowest tenth holds (2026-11-14)

- **Labels:** a further 360 leads, 306 of them under 0.1 and 54 from the nine tenths above, shuffled together and labelled by the same assistant under the same rules, without being told how the batch was drawn. 560 leads are now labelled, all by an assistant; the operator has checked none.
- **The lowest tenth:** 326 labelled, none a treatment report. That shows fewer than about 1 in 100 of its 34,441 leads is one, so at most about 315, where 20 labels had allowed for several thousand.
- **Treatment reports among the 26 labelled in each tenth from 0.1 up:** 1, 6, 8, 11, 13, 9, 17, 20, 25. Weighted by how many leads each tenth holds, that is about 388 treatment reports at or above 0.1.

| Pass at or above | Precision | Recall, as reported | Recall if the lowest tenth hid 315 | Leads passed |
| --- | --- | --- | --- | --- |
| 0.3 | 71% | 94% | 52% | 517 |
| 0.5 | 79% | 85% | 47% | 422 |
| 0.7 | 90% | 74% | 41% | 320 |
| 0.8 | 93% | 67% | 37% | 280 |
| 0.9 | 96% | 59% | 33% | 237 |

- **How to read it:** precision is measured where it matters and is steady across both batches. The best estimate of recall is the reported column, since no report was found under 0.1; the next column is the worst case the labels still allow, not an expectation. Each tenth above 0.1 rests on 26 labels, so its own share is rough: one label is four points.
- **Not settled by this:** every label is an assistant's and follows that assistant's rules for the borderline groups. The thresholds are not set. Whether a passed lead that is not a treatment report can still become a published claim when read is not measured here; the first reading run and its audit are where that shows.

## 12. A prepared batch waits for its audit

- [x] 12.1 Add migration `0024` with `claim.awaiting_audit_at`; `thenwhat prepare` sets it on every read's claim it approves (ADR 0007, chosen by the operator on 2026-11-16).
- [x] 12.2 Leave held claims out of every export and give them no published time; the export command counts what it left out.
- [x] 12.3 Add `thenwhat audit list` and `thenwhat audit clear`, which releases all the named claims or none; unarchive says when a claim is still held.
- [x] 12.4 Verify with tests: prepare marks the claim, the export skips it until cleared, and the command refuses a claim not held while clearing nothing.
- [x] 12.5 Raise the export's schema version to 2 and have the site read only 2, so an export from pipeline code older than the hold stops the build; verify with a site test.

## 13. Batch 1 audit faults: search names and cards

Batch 1's audit (2026-11-16) archived 10 claims for missed or wrong trials. None had another name, and only 2 had GSRS codes; four were combinations the registry cannot find by their name as written ("aspirin plus avelumab" finds nothing, "(aspirin) AND (avelumab)" finds NCT04188119).

- [x] 13.1 Search a combination's treatments together, joined by AND, besides its name as written; verify with a test that the joined search runs and its trial becomes a candidate.
- [x] 13.2 Have `thenwhat prepare` run `terms` after `readings`, so every prepared claim gets its subject terms and background cards (part of 10.5); a terms failure is reported and does not keep the claim waiting.
## 14. Batch 1 audit faults: duplicates by dose or form

Batch 1's audit (2026-11-16) archived 7 claims as duplicates of live ones, drafted because a dose, a schedule or "-assisted psychotherapy" kept the names from matching. Measured on 336 claims, the rule below pairs 13, every one a duplicate the audit archived or would archive, and none for another condition once "in", "with" and the like stop a match.

- [x] 14.1 Offer the same-claim decision the claims sharing a read's core name, and refuse a new claim whose core name and condition are a claim's; record the lead as identity unresolved. Verify with tests: the claim is offered, the duplicate is refused, and a condition about other people is not matched.
- [x] 14.2 List in `thenwhat audit list` the reads left identity unresolved because they overlap an archived claim, so a claim archived for a fault can be fixed, unarchived and its leads read again (review of PR 216); verify with a test that only reads naming an archived claim are listed.
## 15. Outlets that refuse the reader

Batch 1 (2026-11-16) spent 83 of its 300 reader requests on two outlets that answered 401 to every page: reuters.com (44) and wsj.com (39). By batch 2 they stood at 50 and 43, with no page served.

- [x] 15.1 Finish a lead without asking the reader when its outlet answered 401 to at least five pages and served none; verify with tests that such a lead makes no request and that an outlet which served a page is still asked.
- [x] 15.2 Count only 401 answers from the last 30 days, and add `thenwhat backfill retry-outlet <outlet>` to ask an outlet's refused and unasked leads again; verify with tests that lapsed refusals do not stop a read, and one success and one refusal of the command.

## 16. Batch 2 audit faults

Batch 2's audit (2026-11-16) archived 39 of 132 claims: 14 established drugs read "no trial found" though the registry holds hundreds of their trials (buprenorphine for opioid use disorder: 316 within the condition), brand names missed their registry names (Mosquirix finds 1 malaria trial, RTS,S finds 36), and class names and a bare "Cancer" got through. The operator approved three fixes the same day.

- [x] 16.1 Keep the registry's first page (its 100 most relevant trials) for a name still broad within the condition, scored like any candidate, instead of nothing; a search phrase still gives none. Verify with a test against a recorded broad search.
- [x] 16.2 Search the substance's name from the registry of substances as a name, and reject by rule a read's claim filed under the same substance, form and condition as a claim that is neither rejected nor archived, moving its articles to that claim so none is lost. Measured on the database: 8 pairs, all duplicates (semaglutide / Wegovy, BNT162b2 / Pfizer vaccine, ChAdOx1 / AZD1222, daraxonrasib, MDMA, fluvoxamine). Verify with tests.


## 16. Batch 2 audit faults

Batch 2's audit (2026-11-16) archived 39 of 132 claims; batch 3's archived 54 of 137, 24 of them COVID-19 vaccine classes or brand and code names of live claims. The operator approved three fixes on 2026-11-16.

- [x] 16.3 Refuse at the read a class named by its plural, a vaccine or schedule name with no product, a condition that is no one condition ("Cancer") and an animal's condition. Measured on the database: of 619 claims these refuse 1 live ("COVID-19 vaccination" for cardiovascular events) and 28 archived. A target-and-kind rule ("anti-PD-1 immunotherapy") was dropped: it also refused anti-USAG-1 antibody and CAR-T for stiff person syndrome. Verify with tests.

## 17. Backfill of 2026-11-16: stopped outlets and second claims

The backfill of 2026-11-16 read about 800 pages and drafted 257 claims; the audit archived 152. The page reader now stops an outlet that refuses it and answers `NOT_NOW` on HTTP 429 with a wait of minutes to hours; the read step left such an outlet after three answers in a run and asked it again in the next. 39 of the archives were second claims for a treatment that already had one, drafted because the article used a brand, a code or a description and the claim another name.

- [x] 17.1 Keep the time a "not now" wait ends for the lead's outlet beside the sources' pauses, leave the outlet's due leads without a request until then, across runs, and say in `thenwhat backfill plan` how many leads are held; read a `NOT_NOW` on a 429 as the outlet's answer however long its wait. Verify with tests on a synthetic reader: a stopped outlet is not asked in the next run, is asked after the wait, and another outlet is read meanwhile. Not verified against the live reader.
- [x] 17.2 Offer the same-claim decision the claims whose substance record, kept from the registry of substances, lists one of the read's names whole: the substance's name, a brand or other name not withdrawn, or a development code. The decision and its thresholds are unchanged. Verify with tests on synthetic articles: a read naming a brand joins the claim entered under the generic, and another treatment for the same condition still drafts its own claim. A claim with no substance record (a product the registry does not list, or a claim not yet prepared) is found as before, by its name, synonyms and title only.
- [x] 17.3 Review of PR 258: give one worker at a time an outlet's turn, across processes, from the look at its hold to the reader's answer, so no request is in flight for an outlet another request is about to stop. Verify with a test that the turn is not free while a request is in flight and is free after.
- [x] 17.4 Review of PR 258: read a stated wait longer than 24 hours as 24 hours. Verify with tests that a wait in milliseconds and one no time can hold give a hold of a day and end no run.
- [x] 17.5 Review of PR 258: add the claims found by their substance's names after the candidates offered before, up to eight more, so none takes a place. Verify with a test that a claim found by name is still offered beside eight found by substance.
- [x] 17.6 Apply the hold to `thenwhat statements` and `thenwhat outlets` (the operator, 2026-11-16), from one module the read step shares. Verify with tests: each asks a stopped outlet once, keeps the hold, and asks nothing more of it within the wait. `thenwhat lookup` and `thenwhat extract` read one address the operator gives and are left as they were.

## Workflow follow-up

- Archive `backfill-work-ledger` before this change is archived, so that `work-ledger` exists in the main specs.
- Propose as their own changes: answering `resolve` from stored registry trials after measuring it against approved matches; further platforms (Bluesky, the Crossref Event Data archive, Wikipedia's external links) once their terms are read.
