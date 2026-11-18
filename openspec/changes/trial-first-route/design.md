# Design

## Context

Measured on 2026-11-16 on the working database (Postgres 16 in Compose, database `thenwhat`, Alembic revision `0026`, 2,882 MB), with read-only transactions through `psql`. Other sessions were writing while this was read, so counts moved slightly between queries. Two figures come from the registry itself, asked that day for counts and two pages of 1,000 records with a generic client name.

### What is stored

- **Registry trials:** 467,064, all loaded in one hour that day. The registry's own count of interventional studies was 467,064 when asked.
- **By state, as the registry writes it:** completed 262,322; unknown 68,146; recruiting 47,478; terminated 30,155; not yet recruiting 22,831; active, not recruiting 17,262; withdrawn 14,003; enrolling by invitation 3,432; suspended 1,435.
- **By phase:** none given ("NA") 241,524; phase 2 66,179; phase 1 49,113; phase 3 42,574; phase 4 36,122; phase 1 and 2 17,213; phase 2 and 3 7,664; early phase 1 6,545; empty 130.
- **With a name and an indication worked out by rule on load** (`search_name`, `search_indication`): 213,123. Those carry 58,791 distinct names.
- **Claims:** 1,711 in the database, 708 approved, unarchived and not awaiting audit. Their approved events cite 3,073 distinct trials. Across all claims, 4,529 trials are cited by an approved event, 8.2 for a claim on average.
- **Link leads:** 682,022. On a listed outlet and in scope: 559,092. Of those, triage passed 6,446, held 5,961, and has not yet scored 144,715. 3,786 have been read: 1,616 drafted a claim, 567 joined one, 878 (23%) could not be read, 413 were not one treatment, 312 ended otherwise.
- **Unread today:** 2,933 passed and 5,710 held.
- **Spend to date:** 22.27 US dollars, 12.62 of it triage. Everything but triage is 9.65 dollars over the 3,687 leads read when spend was counted (reads were running; the count above was taken minutes later): 2.62 dollars for 1,000 reads, all later steps included. Triage is 0.030 dollars for 1,000 headlines.

### What the stored record holds, and does not

The bulk load asks the registry for ten fields (`LIST_FIELDS` in `sources/clinicaltrials.py`): identifier, title, conditions, intervention types, names and other names, phase, overall status, start date, lead sponsor class. Checked on the stored payloads: every one holds those and nothing else. So none of 467,064 stored records has a completion date, a date results were posted, a date of last change, an enrolment figure, a sponsor's name or a reason for stopping. 2,889 have no start date.

Asked of the registry, 1,000 records each:

| Fields | Bytes a trial |
| --- | --- |
| The ten kept today | 601 |
| Those, with sponsor name, both completion dates, first posted, last changed, results first posted, whether results exist, enrolment and why stopped | 909 |
| Those, with the planned primary outcomes and their time frames | 1,224 |

For 467,064 trials that is about 281 MB, 425 MB and 572 MB of text. In that page of 1,000, 159 had posted results and 96 stated a reason for stopping; the page is the registry's first, not a sample.

`registry_trial` with its indexes is 637 MB in Postgres today. The largest stored payload is 12,367 bytes.

### How many trials change

Interventional studies the registry changed, by its date of last change, asked on 2026-11-16: 935 that day; 4,237 since 10 November; 16,023 since 17 October. That is 500 to 950 a day and about 3.4% of the corpus a month. At 1,000 records a page, the daily load is one or two requests.

### How precise the name link is

Screening links a lead to a trial when the lead's title holds the trial's `search_name` as whole words together with a word of its indication that is not a word of the name (`backfill/link_screen.py`, version 2).

All 682,022 leads have been screened, but only 72,374 of them after the full load: 609,648 were screened while the corpus held about 43,000 trials. So the link table mixes two corpora, and the figures below are for the 72,374 screened against all 467,064 trials. That run took 1 minute 42.

- 30,471 of them are in scope. 1,083 (3.6%) are linked to a trial by title: 2,766 links to 1,343 trials. Across all leads, 177 hold ten trial links, which is the most a lead may keep.
- Of the 1,083, triage passed 368 (34%), held 162 and rejected 553. Triage passes 1.6% of the leads it scores, so a link is a strong sign that a headline is about a treatment. That is the use it has.
- The names most often linked: "cancer" 85 leads, "test" 80, "blood" 51, "protein" 33, "diet" 31, "more" 30, "cell" 27.
- By how many trials carry the linked name: 1 trial, 215 leads; 2 to 5, 178; 6 to 20, 236; 21 to 100, 426; more than 100, 171.

**Twenty links drawn at random** (seeded) and judged by the assistant from the lead's title and the trial's title, name and indication:

| Judged | Of 20 |
| --- | --- |
| The headline reports that trial | 0 |
| Same substance and same area of condition, another study or no particular study | 5 |
| Matched on an ordinary word (protein, diet, test, cell, gene, exercise, nicotine in a story about regulation) or on a class of treatments | 12 |
| Right substance, a trial of something else (a drug named as the comparator, a drug tested for another use) | 3 |

**Twenty links drawn at random from names five trials or fewer carry:**

| Judged | Of 20 |
| --- | --- |
| Right substance and right condition | 4: TARA-002, STX-003, plixorafenib, puxitatug samrotecan |
| Of those, plainly that trial ("doses first patients" beside a phase 1/2 study of the same code) | 1 |
| An ordinary word, a study's acronym used as its intervention's name, or a class of treatments (Vital, plan, LIFE, MORE, ACCESS, even, Women, Food, mRNA) | 16 |

Titles are not reproduced here beyond the names matched. Forty links are few; the finding they support is coarse and is stated coarsely: the present link does not find a trial's report, a rare name alone does not fix it, and what the four good links share is the kind of name.

**Other things a title could carry, counted over the 559,092 leads in scope:** a registry number, 0; a phase ("phase 3", "phase II"), 160; a token shaped like a development code, 693. How many of the 693 equal a code among a trial's intervention names was not measured: the query ran past five minutes on the working database and was left.

### The sets

| Set | Trials | With a name and indication | Distinct names |
| --- | --- | --- | --- |
| Under way or not yet started, phase 3 (phase 2/3 included) | 8,123 | 6,974 | 3,593 |
| Under way or not yet started, phase 2 (phase 1/2 included) | 17,775 | 15,502 | 6,987 |
| Completed, phase 2 or 3, any year | 72,135 | 59,719 | not counted |
| Completed recently | cannot be chosen: no completion date is stored | | |

Leads linked by title to each set, among the 30,471 in scope that were screened against the full corpus, and what scaling by 18.35 to all 559,092 in scope would give. The scaling assumes the last-screened leads are like the rest, which was not checked, and a lead linked to two sets is counted in both.

| Set | Linked | Passed | Held | Already read | Unread, passed or held | Scaled to all leads |
| --- | --- | --- | --- | --- | --- | --- |
| Under way, phase 3 | 66 | 55 | 6 | 43 | 18 | about 330 |
| Under way, phase 2 | 147 | 72 | 18 | 42 | 48 | about 880 |
| Completed, phase 2 or 3 | 337 | 164 | 49 | 118 | 95 | about 1,740 |
| Any other trial | 844 | 267 | 135 | 199 | 203 | about 3,700 |

These are counts under the present, weak link. Under the strong link of decision 4 they will be lower; by the second sample, perhaps a fifth.

### What exists on the site

- `/trials/<identifier>` is already answered on request by the Worker (`site/worker/trials.mjs`, spec `trial-records`): it reads one study from the registry's public API, keeps it a day, makes no model call, and answers only for identifiers the published export cites. Its pages are marked not to be indexed.
- That page labels a trial's state with the registry's words, "Recruiting" among them. The glossary says "Under way. Never recruiting", and `trial-facts` says the same of the facts on a claim page. The two disagree today.
- `site/src/pages/trial-index.json.ts` lists, for each cited identifier, the claims citing it. It is what the Worker checks an identifier against and what search answers an identifier from.
- A listing of identifier, title, state, phases and start date, as JSON: about 73 MB for all 467,064 trials (50 MB of it titles), about 4.8 MB for the 25,898 under way in phase 2 or 3. Sizes are sums of field lengths, uncompressed.

### From the trial's end: what was measured on 2026-11-16 and 17

Added after the operator asked to close the gap from the trial's side: for a trial with recent activity and no linked article, build its fingerprint and look for coverage. Everything below was measured with throwaway scripts outside the repository, a generic client name, nothing written to the working database, and nothing kept but counts and addresses.

**The two sets, counted at the registry:**

| Set | Trials |
| --- | --- |
| Not started or under way, phase 2 or 3, record changed since 2025-01-01 | 23,328 (phase 3 alone: 7,302) |
| Completed, primary completion since 2025-01-01, results posted | 2,114 (phase 2 or 3: 707) |
| Completed at any time, results first posted since 2025-01-01 | 9,283 (phase 2 or 3: 3,207) |

**What a fingerprint can hold.** 900 trials under way in phase 3 with a drug or biological intervention were drawn at random from the working database and their records read from the registry (9 requests). 439 (49%) have an acronym. 440 have an acronym or a development code that passed a first, loose rule. 200 of those were the experiment's trials: 138 with an acronym, 84 with a code, 51 with an invented drug name; 311 terms in all; 189 changed since 2025.

**What the registry record itself links** (first page of 1,000 of each set, which is the registry's order and not a sample):

| | Under way, phase 2 or 3, changed since 2025 | Completed phase 2 or 3, results first posted since 2025 |
| --- | --- | --- |
| Acronym | 373 | 331 |
| A paper of the kind result | 30 | 67 |
| A paper of the kind derived | 121 | 445 |
| A paper of the kind background | 90 | 113 |
| A see-also link | 120 | 239 |
| Other names on an intervention | 384 | 580 |

The see-also links go to sponsors' trial sites and hospitals (mdanderson.org, mskcc.org, merckclinicaltrials.com, bms.com, a file host for sponsors' result summaries). None of the twelve most common hosts in either set is a news outlet. "Derived" has no written definition on the registry's pages; its study page shows these papers under "From PubMed" and says they are filled in automatically and may or may not be about the study. It is in effect the paper index's own list of papers that carry the number.

**Papers that carry the number:**

| Asked | Trials with at least one paper | Papers |
| --- | --- | --- |
| Europe PMC, the number as a phrase in full text, 100 of the experiment's trials | 58 | 790, median 6 |
| Europe PMC, the same, 99 completed phase 2 or 3 trials with results first posted since 2025 | 85 | 1,129, median 6 |
| PubMed, the number in the field publishers supply it in (`[si]`), 60 of the experiment's trials | 9 | 14 |

For one well-known trial the agent's check found 490 papers by full text and 15 in the supplied field. Full text finds every review that cites a trial; the supplied field finds the trial's own papers.

**Stored leads matched on the fingerprints.** The 311 terms against the 559,092 stored leads in scope, as whole words in the title: 211 leads for 15 of the 200 trials. By kind of term: acronym, 192 leads for 8 trials, of which triage rejected 137 and passed 7; code, 1 lead, passed; drug name, 18 leads for 6 trials, 12 passed. The acronym hits are ordinary words that passed the loose rule.

**An encyclopedia.** Wikidata holds 391,574 items with a ClinicalTrials.gov number. 17 of them have an English Wikipedia article.

**The size of the wider record.** With every field this change now names (decision 3): 1,273 bytes a trial, 595 MB for the corpus. With planned primary outcomes too: 1,588 bytes, 742 MB. The ten fields kept today are 601.

### The batching experiment

**Question:** can one request to the news index carry many trials, and can each hit be given back to the right trial?

**How.** 20 requests at most, 30 seconds apart, to Media Cloud's story search, with the operator's key read from the main checkout's settings and never printed, over the two configured collections (United States and United Kingdom national), for stories from 2025-01-01. A query was the trials' terms as quoted phrases joined by OR. A hit was given to a trial when its headline or its address held one of that trial's terms as whole words. **19 requests were sent and logged; a twentieth may have been in flight when the first run was stopped. Count 20 against the week's allowance.**

**Limits, documented.** Read by the assistant's research agent on 2026-11-16 from Media Cloud's query guide, search API guide and public server source (the limits are in source code, not on a policy page): a query of at most 16,384 characters; at most 1,000 stories a page, with a token for the next page; a bare query searches full text; a title can be searched with `article_title:`; 2 requests a minute for an ordinary user; a default weekly quota written in the source as 10,000, where `docs/sources.md` records 4,000 from the pages read on 14 November. Its terms-of-use page answered 404 that day.

**Limits, observed.**

| Request | Trials | Terms | Query characters | Answer | Seconds | Stories |
| --- | --- | --- | --- | --- | --- | --- |
| Full text | 10 | 16 | 217 | 200 | 42.8 | 584 |
| Full text | 10 | 12 | 171 | 200 | 31.7 | 81 |
| Full text | 10 | 16 | 232 | 200 | 30.0 | 266 |
| Full text | 10 | 14 | 192 | 200 | 39.6 | 105 |
| Full text | 10 | 11 | 142 | 200 | 22.9 | 727 |
| Full text | 25 | 36 | 510 | 200 | 56.1 | 845 |
| Full text | 25 | 33 | 456 | 200 | 57.1 | 907 |
| Full text | 50 | 68 | 956 | 504 | 60.2 | |
| Full text | 50 | 74 | about 1,000 | 504 | 60 | |
| Title only | 25 | 36 | 526 | 504 | 60.6 | |
| Title only | 50 | 68 | 972 | 504 | 60.4 | |
| Title only | 200 | 291 | 4,246 | 520 | 0.4 | |
| Title only | 100 | 138 | 2,002 | 504 | 60.5 | |
| Full text | 25 | 40 | 594 | 504 | 60.7 | |
| Full text, stricter terms | 22 | 31 | 443 | 504 | 60.4 | |
| Full text, from 2026 only | 50 | 68 | 956 | 504 | 60.2 | |
| Title only, stricter terms | 167 | 241 | 3,563 | 400, "request line is too large" | 0.8 | |
| Full text, the first request again | 10 | 16 | 217 | 504 | 60 | |
| Full text, the fifth request again | 10 | 11 | 142 | 200 | 53.8 | 727 |

What this says:

- **The limit that binds is time, not length.** A gateway in front of the index gives up at 60 seconds. Ten trials answered in 23 to 43 seconds in the first quarter hour; 25 trials in 56 and 57 seconds, at the edge; 50 never. An hour later the index was slower: the same ten-trial request that took 22.9 seconds took 53.8, and the one that took 42.8 timed out. 8 of 19 requests were answered.
- **The request line is limited before the query is.** A query of 3,563 characters (an address of about 4,700) was refused as too large and one of 4,246 broke the gateway, far under the documented 16,384. About 2,000 characters was accepted and then timed out.
- **No answer was cut short.** The most stories in one answer was 907, under the page of 1,000.
- **Title-only search was not measured.** All five title-only requests failed, four of them on time during the slow hour. Whether it is faster is still unknown.

**Giving hits back to trials.** Stories are returned with a headline and an address and nothing that says which term matched. Headlines were held in memory only; those of the first run were lost when it was stopped, so the two figures below are what was kept.

| Request | Stories | Tied to one trial | To several | To none | Trials of the 10 with a tied hit |
| --- | --- | --- | --- | --- | --- |
| First, 10 trials | 584 | 29 in all | | 555 | not kept |
| Last, 10 trials | 727 | 46 | 0 | 681 | 2 |

So about one hit in twenty can be given to a trial from what the index returns. The rest matched somewhere in the article's text, and without the text, which this project never takes, nothing says for which trial.

**Forty hits judged by hand**, from the last request, by headline and outlet only: 28 drawn from the 46 tied hits and 12 from the 681 untied.

| Judged | Of 40 |
| --- | --- |
| Tied, the trial's own treatment (all ten on one invented drug name, "MariTide") | 10 |
| Of those, about that trial and not another trial of the same drug | 0 that the headline shows; the trial was the drug's study in Japan and the headlines are about its phase 2 results and its other phase 3 studies |
| Tied, wrong (all eighteen on "NSCLC", a disease's abbreviation that one record gives as its acronym) | 18 |
| Untied, with nothing in the headline to say which of the ten trials it is about | 12 |

Precision of a tie to the right treatment: 10 of 28. To the right trial: 0 of 28. Both figures turn on two terms, one good and one bad, which is itself the finding: a batch is as noisy as its worst term, and one request cannot say which term that is.

The outlets tell the rest: benzinga.com and prnewswire.co.uk carry most of the hits. Inside the national collections, a trial's code is found mainly in press-release copy.

**What a week's allowance would cover**, at ten trials a request, the size that answered reliably when the index was not slow:

| Set | Requests | Share of 4,000 a week | Hours at 30 seconds apart and about 40 seconds an answer |
| --- | --- | --- | --- |
| Under way, phase 2 or 3, changed since 2025 (23,328) | 2,333 | 58% | about 45 |
| Phase 3 only (7,302) | 731 | 18% | about 14 |
| Completed since 2025 with results (2,114) | 212 | 5% | about 4 |

Only about half of those trials have a term fit to send, so the real figures are near half. About 230 requests are left this week after this experiment: enough for the completed set once, with nothing spare for the requests that time out.

**Verdict.** One request can carry about ten trials, not fifty. The allowance then covers both sets inside a week, which a request for each trial could not. But what comes back is mostly not attributable, and what is attributable names a drug, not a trial. Batched search is worth building only after the routes that tie by the registry number, only with strict terms, and only to feed the reading path with headlines that triage then judges.

## Goals / Non-Goals

**Goals:**

- Every stored trial can be opened on the site as a page of registry facts, worded without verdict or advice.
- Stored leads reach the trials they are about with no request for each trial, in an order the operator sets.
- A trial page and a claim page never state different facts about one trial.
- Every stored trial is kept current daily (`daily-trial-refresh`), and nothing that reads, drafts or publishes is started by that.
- A trial with recent activity and no linked article is looked for from its own end, by routes that are free and exact before any that are paid or loose.
- Each phase is useful when it ships, before the next.

**Non-Goals:**

- Finding a news report for most trials. The stored leads cannot do it, and nothing here pretends they can.
- A status for a trial. Status belongs to a claim.
- Any shortcut around preparation and the audit.
- Rendering claim pages on request.

## Decisions

### 1. A trial without a claim is a registry trial with a page, and nothing more

**The record** is the registry trial: one row for each registry and identifier, with its raw payload and fetch time. Nothing new is stored for a trial because it has a page.

**The page** is `/trials/<identifier>`, the address the site already uses for a cited trial. One address for each trial whether or not a claim cites it, so a trial that gains a claim keeps its address.

**It differs from a claim page in kind, not in polish:**

| | Claim page | Trial page |
| --- | --- | --- |
| The unit | One intervention for one indication, as reported | One registry record |
| Status, gloss, no-signal overlay | Yes, derived from approved events | Never |
| Source articles, promises, reported statements | Yes | Never |
| Match score and reasons | For each match | None: nothing was matched |
| Record strip | Yes | No |
| Topic, vertical, group, approach | Yes | No |
| Counted in the site's totals and lists of claims | Yes | No |
| In the open data file | Yes | No, in this change |
| Model readings | For a claim's trials | Never for an uncited trial |

A trial page of a cited trial also lists the claims citing it, each with the claim's own status as exported, as it does today. It derives nothing.

**What the page states**, for any trial:

- the identifier followed by the registry's name, and the title;
- the trial's state, in the words of decision 2;
- phase, conditions and interventions, as the registry gives them;
- start date, primary completion date and completion date, each marked estimated when the registry marks it so, with no day invented for a month;
- whether the record holds posted results and the date they were first posted;
- enrolment, marked planned or actual;
- the lead sponsor's name when the sponsor is not a person;
- when the trial was stopped and the record says why, the reason in the registry's words;
- the date the record was read and the date the registry last changed it;
- a link to the record at the registry;
- when no published claim cites it: "No news report is linked to this record yet."
- the site's notices, including that a registered trial is not a treatment option.

**What it never states:** a status or a gloss of one; "successful", "failed", "positive", "negative", "promising" or any other word for how a trial turned out; that results are late, overdue or missing; how long anything has been quiet; whether the trial is open to participants, where it runs, whom to contact or who may take part; a sponsor's description of a result; a lead, a count of leads or anything a lead's title said; a score; a model's reading.

### 2. Which registry fields are facts, and which need a rule first

**A fact the page may state as the record gives it** (each is a field of the list response, measured above at 909 bytes a trial):

| Fact | Registry field | Stored today |
| --- | --- | --- |
| Phase | `Phase` | Yes |
| Conditions | `Condition` | Yes |
| Interventions and their kinds | `InterventionName`, `InterventionType` | Yes |
| Start date | `StartDate` | Yes |
| Primary completion and completion dates | `PrimaryCompletionDate`, `CompletionDate` | No |
| Results posted, and when | `HasResults`, `ResultsFirstPostDate` | No |
| First posted and last changed | `StudyFirstPostDate`, `LastUpdatePostDate` | No |
| Enrolment | `EnrollmentCount`, `EnrollmentType` | No |
| Sponsor's name | `LeadSponsorName` | No (class only) |

**Needs a rule before it is shown:**

| Shown | Why a rule | The rule |
| --- | --- | --- |
| State | The registry's words say whether a trial is recruiting | The mapping `trial-facts` already has: not started, under way, completed, suspended, terminated, withdrawn, unknown |
| Phase "NA" (241,524 trials) | It is not a phase | Worded "No phase given", with the registry's meaning in a note |
| State "unknown" (68,146 trials) | Readers will read it as a verdict | One fixed phrase that says the registry's record has not been confirmed, and nothing about the trial |
| Sponsor | A sponsor can be a person | Class "individual" is not recorded and not shown, as the glossary says |
| Reason for stopping | It is the sponsor's free text | The `trial-facts` rule: the registry's words, attributed, never reworded |
| Primary outcome reported | Not in the list response; it is in the results section of the full record, which can pass 2 MB | The `trial-facts` rule for posted primary outcomes, applied to a full record. Until a full record is stored for the trial the page says only that results are posted |
| A regulator's approval | Not a registry field at all | It is an evidence event of a claim. A trial page shows it only as the status of a claim that cites the trial. An uncited trial page never shows one |
| "No report linked yet" | It is a statement about the tracker, not the trial | True exactly when no published claim cites the trial |
| Anything comparing dates (years since completion with no results) | It reads as a verdict | Not shown in this change |

**Proposed phrases for a state**, for the operator to approve; the site holds them, and its build fails on verdict wording as it does for glosses:

| State | Phrase |
| --- | --- |
| Not started | The registry lists this study as not yet started. |
| Under way | The registry lists this study as started and not yet finished. |
| Completed | The registry lists this study as completed. That says the study ended, not what it found. |
| Suspended | The registry lists this study as paused. |
| Terminated | The registry lists this study as stopped early. |
| Withdrawn | The registry lists this study as withdrawn before anyone was enrolled. |
| Unknown | The registry lists this study's state as unknown: its record has not been confirmed for some time. |

Results: "Results were first posted on the registry record on 3 March 2025." or "The registry record holds no posted results."

### 3. The bulk load keeps the fields the page needs

The list request gains the fields of the first table in decision 2. Not the planned primary outcomes (a third more again, and the page of a cited trial already has them from its full record), and not the results section.

The routes of decision 12 need more of the record: the acronym, the official title, the sponsor's and other identifiers, collaborators, the papers and links the record lists, and the date it was first posted. With those the record is 1,273 bytes a trial, 595 MB for the corpus, measured on a page of 1,000.

A full record is fetched for an uncited trial only by a step, never by a load, and only for trials in a set the operator has named, when the list response says results are posted. One registry request a trial, no model. Until it has run, the page states that results are posted and when.

Considered: asking the registry for each uncited trial when its page is opened, as the page does today for cited trials. That is decision 8's bridge, not the end state: a page for each of 467,064 trials answered by a live request puts the registry behind every crawler.

### 4. A link is strong only on a telling name

The first sample says what goes wrong: an intervention's name is often an ordinary word, and the indication's word is common in health news. The second says what goes right: codes and invented names.

A name is **telling** when it is one of:

- a development code among the trial's intervention names and other names (letters, an optional hyphen, digits: "TARA-002");
- a name of a drug or biological intervention that the substance registry lists as one substance (`sources/gsrs.py`, the source development codes already come from) and that fewer than a set share of stored lead titles hold. The share is a setting, with no default until it is measured (task 3.2). "Insulin", "nicotine" and "oxytocin" are substances and are held by many titles; they are not telling.

A study's acronym, a class of treatments ("CAR-T", "SSRIs", "mRNA"), a behaviour or a food is never telling.

A link is **strong** when the title holds a telling name as whole words and a word of that trial's conditions that is not a word of the name. Every intervention name and other name of the trial is tried, not `search_name` alone, so a brand name can link.

A strong link is to a **name and a condition**, and through them to every stored trial that carries both. The samples show a headline cannot choose among those trials, and nothing here asks it to. Which trial a report is about is settled after the read, by the page naming a registry number or by the claim's matches being scored for its indication, as today.

What else was weighed as a signal:

- **Sponsor in the title.** The sponsor's name is not stored today. Once it is, it orders strong links (a title that also names the sponsor is read first). It never makes a link by itself: a company's name beside a disease is most of the trade press.
- **A phase in the title.** 160 titles of 559,092. Too few to build on; used to order.
- **A registry number in the title.** None in 559,092. The number is on the page, which the read already records.
- **The date.** A lead first shared before the trial was first posted is not linked to that trial. Possible once the wider load stores the date.

Screening's present link is kept, unchanged and still a candidate. It is right about one thing: 34% of the leads it links pass triage, against 1.6% of all. It goes on ordering reads, as `lead-reading` says. It is not strong and is never called a report.

**As built in phase 1 (2026-11-17, task 9.8 to 9.10).** Every link to a trial carries a reason and one of four strengths: `exact` (the registry number), `strong` (a development code beside a condition word), `named` (a code alone, or an acronym that carries a number beside a condition word), `candidate` (the present link, and another name of a drug or biological intervention beside a condition word). Only a development code is telling: the substance registry has not been asked, so a substance's or brand's name is a candidate and no more. An acronym with no number never links. The measurement and the forty links judged are in `tasks.md` under 9.9: a code beside its condition named the right treatment for the right condition in eight of eight, and it links 13 of 558,864 leads; another name beside a condition links 611. Only exact and strong are enough for a held lead to be read (`backfill/link_screen.py`, `STRENGTH_TO_READ`).

### 5. What a strong link changes, and what it never does

It changes two things, both in what is read:

- **A held lead with a strong link to a trial in the set being worked is read**, as a held lead naming a topic is today. A lead triage rejected is not read, whatever it is linked to: 553 of the 1,083 linked leads were rejected, and in the sample the rejected ones were stories about regulation, diet and outbreaks.
- **Order.** After the operator's topics: strong links to the set being worked, then strong links to other trials, then the present links, then shares.

Where this meets the specs of `social-link-backfill`: "Which leads are read" gains the held-with-a-strong-link case, and "Reading order" gains the two tiers. Those requirements are amended when that change is synced; until then `specs/trial-report-links` states the additions.

It never: attaches a lead to a trial; shows a lead on any page; counts as a match or its reason; approves anything; creates a claim; makes a trial "reported".

### 6. Sets, and the order they are worked in

A set is a named choice of trials that says which strong links are read first. It is the same idea as the named sets of a bulk load (`file-based-backfill`, `registry-corpus`) and says as little: which trials, and nothing of how any turned out.

1. **Under way, phase 3** (8,123 trials). Fewest and nearest a result.
2. **Under way, phase 2** (17,775).
3. **Completed in the last two years, phase 2 or 3.** Needs the wider load, since no completion date is stored.
4. Everything else, in no hurry.

**As built in phase 1:** the sets worked are the two of decision 12, `active-since-2025` and `completed-with-results-since-2025`, and inside a set the leads linked to its phase 3 trials are read first. The set is named by `LEAD_READ_TRIAL_SET` for every read, or by `thenwhat backfill read-set <set>`, which prints the plan and reads only the set's linked leads within `TRIAL_ROUTE_MONTHLY_USD`.

One set is worked at a time, by the operator's command. Finishing a set means its strong links have been read, prepared and audited; it does not mean its trials have reports.

### 7. Cost within the ceiling

The monthly ceiling is 100 US dollars, of which 40 is set aside for readers' leads (`docs/adr/0009`). This route spends only on reads and the triage before them. A read costs 2.62 dollars a thousand with every later step counted; triage, 0.030 dollars a thousand headlines.

| Work | Leads | Dollars | Claims to audit, at 44% of reads |
| --- | --- | --- | --- |
| Set 1, under the present link, scaled | about 330 | 0.9 | about 145 |
| Set 2 | about 880 | 2.3 | about 390 |
| Set 3, any year | about 1,740 | 4.6 | about 770 |
| Every unread lead triage passed or held, linked or not | 8,643 | 22.6 | about 3,800 |
| Triage for the 144,715 leads not yet scored | 144,715 | 4.4 | |

So the whole of what the stored leads can give costs about 27 dollars, once. A cap for this route of 15 dollars a month covers any one set several times over.

What actually limits it:

- **The page reader.** Reads have peaked at 256 an hour, and 23% of reads fail on the page. 8,643 reads is about 34 hours of the reader.
- **The audit.** Each batch of a few hundred claims waits for a session to audit it. Set 1 is one batch. Everything is about a dozen to twenty.
- **The leads themselves.** 708 published claims cite 3,073 trials, 4.3 a claim. If 3,800 more claims were published and cited as many, about 19,400 trials would be cited: 4% of 467,064. For the rest, the page of registry facts is the whole of what the tracker has, and it says so.

### 8. A trial-first read is an ordinary read

A lead read because of a strong link goes through the path every lead goes through: the article is fetched through the page reader, extraction names one treatment for one condition or says there is none, the claim is drafted or the article joins a claim that exists, `thenwhat prepare --pending` searches the registries and approves by rule, the claim is held awaiting audit, and `thenwhat audit clear` releases it.

The one addition: the trials of the strong link are handed to preparation as candidates, with the reason that the lead's title named them, as registry numbers a page gives are today. Each is scored for the claim's indication and decided like any candidate. None is approved for having been linked.

**Considered and not taken:**

- *Showing a linked lead on the trial page as "a report that may be about this trial".* A lead is unreviewed and never published, and none of 20 sampled links was a report of its trial.
- *A lighter audit for claims from this route.* The operator confirmed on 2026-11-16 that the audit hold stays for backfill batches. A set is a backfill batch. Put again as question 4 and decided on 2026-11-17: the hold stays.
- *A trial-level record of "reported" without a claim.* It would be a second, weaker kind of claim with none of a claim's rules.

So a trial gets a report in one way only: a published claim cites it.

### 9. A trial page and a claim page cannot disagree

They could disagree in two ways, and each is closed differently.

**About the trial's own facts** (state, phase, dates, results posted). Today a claim's trial facts are read from the record stored with its events, and the corpus holds another copy from the bulk load, read on another day. Rule: for one registry identifier, both pages state facts from the record fetched most recently, whichever copy that is, and both show the date it was read. In the store on Cloudflare a record is kept once under its checksum (`docs/adr/0008`), which makes this the natural shape; before then the export and the listing apply the same "most recent" rule that `trial-facts` already states.

**Between the trial's facts and the claim's status.** A status comes only from approved events, so a record can say "terminated" for a day while the claim still reads "Phase 3". Rule: when a load changes the state, phase, dates or results posting of a trial that a claim cites, that claim is due for its registry refresh. The refresh is the step that exists (`thenwhat fetch`: the registries are read again for the claim, events are approved by the existing rule, the status is derived again). The daily run already refreshes a set number of published claims each run, in turn (`daily-trial-refresh`, `docs/daily-run.md`); it takes these claims first. `thenwhat export` writes nothing while a cited trial's refresh is due, and says how many are. The trial page lists the claim with the status the export gives it, and never words a status of its own.

The daily run never exports, so the hold is on the export command, whoever runs it. What is left is the time between a load and the next refresh, during which nothing new is published.

### 10. The daily change load: what it makes due, and what it never starts

**The load itself is not this change's.** The change `daily-trial-refresh` (pull request 268) puts `thenwhat backfill load-trials --trials interventional --changes-only` in the daily run as a `trials` step before `refresh`, makes a load stop cleanly when the registry may not be asked, and says the daily run starts no step over the trials it loads. Reconciled with it on 2026-11-16: this change specifies none of that again and contradicts none of it.

What each change holds:

| | `daily-trial-refresh` | This change |
| --- | --- | --- |
| The daily step, its order and its summary line | Yes | Adds two counts to the summary |
| A load that stops when the allowance is used up | Yes ("Registry terms") | Nothing |
| The daily run starts no step over loaded trials; `news_search` waits | Yes | Agrees, and says the same of the load for linking and the full record |
| Which fields a stored trial holds | Nothing | The wider record (decision 3) |
| What a change makes due | `news_search`, as before | Also the offline linking, the full record, and the refresh of a citing claim |
| The order of the run's existing refresh | In turn | Claims citing a changed trial first |
| The export | The daily run never exports | `thenwhat export` waits while a cited trial's refresh is due |

**A load, by itself:** updates the stored record, payload and fetch time; stores a trial the registry added; marks work due. It starts no step.

**What a change makes due, and who runs it:**

- *The registry refresh of a claim that cites the trial*, when its state, phase, dates or results posting changed (decision 9). Run by the daily run's existing `refresh` step, which takes these claims first, within `DAILY_RUN_REFRESH_LIMIT` and under the run's spend guard. That step can call a model, as it does today; this change adds no refresh beyond the limit, only an order.
- *The offline linking*, for a trial that is new or whose names or conditions changed. No request and no model, but run by the operator, when a set is planned (task 4.2 links what is due first).
- *The full record*, for a trial in a named set whose record newly says results are posted (decision 3). Run by the operator.
- *The news search* (`article-leads`), as `registry-corpus` already says. At 4,000 requests a week it is run by command, for a set, never for the corpus.

An earlier draft let a load start the linking and the full record without a person. It was dropped for the rule `daily-trial-refresh` wrote: the daily run starts nothing over the trials it loads. Nothing is lost: both are wanted only when a set is worked.

**A load never starts, by any path:** a read of a lead; a request to the page reader; a news search; a new claim; a new match or its approval; a failure flag; an archive or its undoing; a release from audit; a message to a reader. A claim's status changes after a load only through the approved registry events of a trial it already cites, when its refresh runs.

A load reports how many trials were new and already stored (`daily-trial-refresh`), and, added here, how many cited trials changed and how many claims that made due.

**One thing to do in order.** A changes-only load asks with whatever field list the client has. After the client is widened, the first load must be a full one (468 requests), or trials unchanged since 16 November keep ten fields. Until that full load has completed, the daily step goes on as it is.

### 11. What ships before the store, and what waits

**Needs nothing from `cloudflare-source-of-truth`:**

- The wider load, and the order of the daily run's refresh (pipeline and `scripts/`; the daily load itself is `daily-trial-refresh`'s).
- Strong links, sets and the ordered reads (pipeline only; works on the present database and, when it lands, in a run folder of `file-based-backfill`).
- A **trial listing** built into the static site for a chosen set: identifier, title, state, phases, start date. For the 25,898 trials under way in phase 2 or 3 it is about 4.8 MB before compression, loaded only when a reader searches. Search then answers a trial identifier or a title from the listing, beside the claims.
- The trial page's state wording (decision 2), on the page that exists.
- Decided by the operator on 2026-11-17 (question 1): the existing page answers for identifiers in the listing as well as for cited ones. It reads the registry on request, a day's reuse, 60 requests a minute for each location, no model. Uncited pages stay marked not to be indexed and out of the sitemap.

**Waits for the store (`docs/adr/0008`):**

- A page for every stored trial. 467,064 pages cannot be built (the listing alone is 73 MB) and should not each cost the registry a request. With the records in D1 the Worker answers from the store: no request to the registry, the same rules, the read date shown.
- Search over every stored trial by word. The store's full-text index does it; a static file cannot.
- Retiring the listing: once the store answers, the listing is a query.

**Asked of `cloudflare-source-of-truth`:** its size criterion was met at 504 MB with 43,320 registry trials. With 467,064 trials at 909 bytes of payload and their columns, the registry corpus alone is an estimated 0.6 to 0.9 GB. Still inside the 3 GB criterion by estimate; to be measured in that change before its migration. Its design says a registry trial's payload goes to R2 under its checksum: that is 467,064 small objects, where one column would do, since the largest is 12 KB. Raised there, not decided here.

Considered for the static site: a file for every thousand identifiers (468 files of about 156 KB), so any stored trial is answered by identifier with one fetch. It gives no search by word and is retired by the store. Put as question 2 and not taken (2026-11-17).

### 12. From the trial's end: a fingerprint, two sets, and routes in a fixed order

Decisions 4 to 8 start from stored leads and ask which trials they name. This starts from a trial and asks what names it. The two meet in the same place, the reading path, and neither replaces the other.

**The fingerprint** is built by rule from the stored record (`specs/trial-coverage`): the registry number, the record's other identifiers, the acronym, development codes, telling names, the sponsor's name. No model.

**A term is fit to send to a source only when it cannot be an ordinary word.** The experiment's worst term was "NSCLC", which one record gives as its acronym; the stored-lead match's worst were words like it. So an acronym is fit only when it is not on the word list, is not a word of any trial's conditions, is held by few other trials' titles, and is long enough or carries a digit or hyphen. The registry number is always fit. A term that is not fit can still confirm a hit another term found.

**The sets** are the operator's two, named for what they hold and nothing else: `active-since-2025` (23,328 stored on 2026-11-17: under way in phase 2 or 3, record changed since 2025-01-01) and `completed-with-results-since-2025` (3,141 stored: completed, actual completion date in 2025 or later, results posted; decided by the operator on 2026-11-17, question 17). They are selected from stored trials by `backfill/trial_sets.py` and were called `active-recent` and `completed-with-results` in earlier drafts. For a route that yields news, a trial a published claim already cites is left out; a route that yields papers is asked for every trial of the set, since a paper belongs on the trial's page whether or not a claim cites it. Both needed the wider load, which is done.

**The target set changed on 2026-11-17, by the operator's decision.** It is one rolling set, `active-or-ended-this-year`: a trial under way now (not yet recruiting, recruiting, enrolling by invitation, active and not recruiting) in any phase, or a trial listed as completed, terminated, withdrawn or suspended with a completion date in the current calendar year. Counted on the working database that day: 91,003 under way, 10,270 completed in 2026, 1,604 terminated, withdrawn or suspended in 2026 (679 of them on an estimated date), 102,877 in all; 7,976 of those under way have had no registry update since before 2025 and stay in the set, counted as a line of the coverage report. The year comes from the clock at the command, never inside the rule (`backfill/trial_sets.py`, `rule_of(name, year)`). The two dated sets keep their names and rules: every trial of `active-since-2025` is in the new set; `completed-with-results-since-2025` overlaps it only for trials completed in the year. The site's listing still names `active-since-2025` and is not changed here. The completion date is text, a year and month with or without a day, so "in the year" is "begins with the year"; the date's kind (actual or estimated) is not part of the rule, as the operator stated it.

**The fields the routes need on a stored trial**, beyond decision 2's: `Acronym`, `OfficialTitle`, `OrgStudyId`, `SecondaryId` and `SecondaryIdType`, `CollaboratorName` and `CollaboratorClass`, `ReferencePMID` and `ReferenceType`, `SeeAlsoLinkURL` and `SeeAlsoLinkLabel`, `StudyFirstPostDate`. Not `ReferenceCitation`, which is free text and large. `InterventionOtherName` is already stored. With these the record is 1,273 bytes a trial. The list was given to the session that widens the load on 2026-11-16, so that one reload suffices.

### 13. The routes, in order of preference

Free and deterministic first. "Tie" is how a hit is given to a trial.

| | Route | Yields | Tie | Cost | Terms | Measured |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | The registry record's own references and links | Papers. No news | The record names the paper | Nothing: the fields come with the wider load | ClinicalTrials.gov, in `docs/sources.md` | A result paper on 3% of the under-way page and 7% of the completed one; a derived paper on 12% and 45%. Links go to sponsors and hospitals, not outlets |
| 2 | Papers that carry the number | Papers | The number, in the field the publisher supplied | One request a trial, free. PubMed: 3 a second with no key, 10 with a free key; more than 100 requests are asked for off-peak | PubMed's E-utilities are **not yet in `docs/sources.md`**. Pages read 2026-11-16: [NLM data guide](https://www.nlm.nih.gov/dataguide/eutilities/utilities.html), [NCBI policies](https://www.ncbi.nlm.nih.gov/home/about/policies/), [PubMed help](https://pubmed.ncbi.nlm.nih.gov/help/), [NLM download terms](https://www.nlm.nih.gov/databases/download/terms_and_conditions.html). The usage-policy chapter itself could not be read. Europe PMC is in `docs/sources.md` | 9 of 60 under-way phase 3 trials in PubMed's field. By full text in Europe PMC, 58 of 100 and 85 of 99, but that counts every paper that cites the trial |
| 3 | Stored leads matched on the fingerprint | News | A fit term in the headline, then decisions 4 and 5 | Nothing | None: stored data | 19 leads for 7 of 200 trials on codes and drug names, 13 of them passed by triage. Acronyms under the loose rule: 192 leads, 137 rejected |
| 4 | Batched news search | News, mostly press-release copy | A fit term in the headline or address. About 1 hit in 20 can be tied | About ten trials a request; both sets inside one week's 4,000 | Media Cloud, in `docs/sources.md`; its limits as read from its source are added there | See "The batching experiment" |
| 5 | Press-release wires | Sponsors' releases. Already a listed outlet group | The release's page gives the number | Free, if allowed at all | **Their sites may not be searched by a program.** Read 2026-11-16: PR Newswire's [terms](https://www.prnewswire.com/terms-of-use/) forbid any robot or site search application; GlobeNewswire's [robots file](https://www.globenewswire.com/robots.txt) disallows `/search` and its customer terms forbid bots; EurekAlert's [robots file](https://www.eurekalert.org/robots.txt) disallows both its searches and its [terms](https://www.eurekalert.org/termsAndConditions) forbid storing its material in a retrieval system without permission; Business Wire refused every page, its robots file included | Not measured. What is left: the wires' own subject feeds for new releases (GlobeNewswire has one for clinical studies; PR Newswire has health feeds of 20 items), if their terms let a program read a feed, which was question 13 and is not done (decided 2026-11-17); and the wire copy other routes already find |
| 6 | Full-text news search by number or acronym | News | The page gives the number or a fit term | GDELT: free, one request every five seconds, 250 results. NewsAPI.ai: 90 US dollars a month for 5,000 searches, archive from 2014, five times the tokens for each year searched back. NewsAPI.org: 449 dollars a month for other than development | GDELT's DOC interface is in `docs/sources.md` as refusing every request from the operator's address on 2026-11-14; its documented window and its live behaviour disagree. The two paid services are **not in `docs/sources.md`**. Read 2026-11-16: [NewsAPI.ai plans](https://newsapi.ai/plans) and [terms](https://newsapi.ai/terms), which allow storing what is retrieved and do not count a site of headlines that link to publishers as a competitor; [NewsAPI.org pricing](https://newsapi.org/pricing) and [terms](https://newsapi.org/terms) | Not measured. Whether any of them indexes a registry number as a searchable word is unknown |
| 7 | A paper-to-news mentions index | News about a trial's papers | The paper is the trial's by route 1 or 2; the index lists news that mentions the paper | Altmetric: by contract, no listed price | **Not in `docs/sources.md`.** Read 2026-11-16: [Altmetric's API pages](https://docs.altmetric.com/details-page-api/) and [its API offer](https://www.altmetric.com/solutions/altmetric-api/). Since 10 November 2025 every request needs a key. A free key is for a researcher's one-off academic project. Only the paid endpoint lists single mentions. Headlines and links of United Kingdom newspapers are withheld without a separate licence. Crossref's Event Data was [retired on 23 April 2026](https://www.crossref.org/deprecated/) | Not measured |
| | Wikipedia and Wikidata | An entry about a named trial, and the news it cites | The entry carries the number | Free. Read 2026-11-16: [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette), [User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy), [query service manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual) | Text CC BY-SA 4.0, data CC0 | **Dropped.** 391,574 items carry a registry number and 17 have an English Wikipedia article |

Three things the order rests on:

- **Routes 1 and 2 give papers, not news, and are the only routes whose tie is exact.** They are worth having for themselves: a trial page can list the papers of a trial that the news never reported (decision 15). They also feed route 7, should it ever be bought.
- **Every news route ties by a word, and a word names a drug or a study, not a registry record.** The experiment's best term tied ten headlines to the right drug and none to the right trial. So a news hit is a lead with a candidate trial. It is never a trial's report by having been found.
- **The wires are where the registry number is printed, and they may not be searched.** The practical way to them is through what already indexes them (routes 4 and 6) and through the page reader for one release at a time, which is the page reader's decision (`docs/adr/0006`).

Considered: sending a set's trials one a request to learn which term matched. That is the search the allowance rules out. Considered: asking the index twice, the second time for the untied hits' terms one by one. It spends the allowance on stories that matched an ordinary word.

### 14. Every article found goes through the path that exists

A route's hit is a link lead or an article lead with the reason it was found, and nothing more. From there nothing is new: screening, triage, the page reader, extraction, the same-claim decision, drafting or joining, `thenwhat prepare --pending`, the audit hold (`docs/adr/0007`), `thenwhat audit clear`. A lead triage rejects is not read, whatever found it. The trial that led to the article is handed to preparation as a candidate, scored for the claim's indication, and never approved for having led there (decision 8). `specs/trial-coverage` states this as one requirement with a scenario for each step, because every route will be tempted to skip one.

A search is planned and run by the operator for a set. No load and no daily run starts one, which is decision 10 and `daily-trial-refresh` said again.

The local evidence-search pilot uses complete registry study names as candidates, including multiword names with different spacing or hyphenation. The article needs nearby corroboration from the intervention or condition. When a candidate gets a study-specific excerpt, it prefers a reported finding tied to that study over an enrollment or future phase update. A nearby finding explicitly tied to a different candidate does not supply that excerpt. These rules preserve the pilot's fixed Decisions acceptance threshold.

A small sponsor with an explicitly reported phase can supply additional candidates when its registry records use an older code or a broader condition. A cited sponsor disclosure can clarify a product rename during verification. The rename is attached only to a candidate with the same sponsor and registered name when the article uses the newer name. The verifier still decides whether the reported regimen and cohort belong to that protocol.

### 15. Papers on a trial page

Decision 2 said a trial page states registry facts. A paper the registry record names is one, and a paper whose own record carries the trial's number is a fact of the paper index. Both are listed on the trial page under two fixed headings, with paper facts as `paper-facts` gives them and a link, and nothing about what a paper found. A paper never removes the line that no news report is linked.

Not shown: a paper that only mentions the number in its text. For one trial that was 490 papers against 15.

A paper of the registry's kind "derived" is shown under the paper index's heading and not as a paper the sponsor named, since the registry fills that list from PubMed by itself and says it may not be about the study.

This replaces the earlier open decision that left papers out of this change.

### 16. Order of building, and what each step costs

1. With the wider load: fingerprints and fit terms for every stored trial. No request.
2. Route 1, from stored fields. No request. Papers on trial pages once the paper index has their records (one request a paper, as `paper-facts` does now).
3. Route 3, stored leads on fingerprints. No request. The reads it sends are counted in decision 7's plan.
4. Route 2, after PubMed's entry is in `docs/sources.md`: the trials' numbers are asked many to a request, so the 3,141 trials of the completed set and the 23,328 of the active one are some hundreds of requests, off-peak, free.
5. Route 4, for `completed-with-results-since-2025` first: about 100 to 210 requests of the week's 4,000. Kept only if a hand sample of its tied hits, taken as task 8.9 says, shows it worth the allowance.
6. Routes 5 to 7 are off: decided 2026-11-17 (questions 13, 14 and 11). The operator's two emails, to Media Cloud and to Altmetric, come first.

Model spend comes only from the reads a route's leads lead to, at 2.62 dollars a thousand, inside the route's share of the ceiling (15 US dollars a month, decided 2026-11-17, question 8). No search step spends on a model.

## Risks / Trade-offs

- **A page of registry facts reads as an endorsement or a way in.** → No word about taking part, no location or contact, the site's notice that a registered trial is not a treatment option on every trial page, and the state worded as "under way".
- **"No news report is linked yet" reads as "nobody reported it".** → The line says linked, and the method page says how leads are found and that most trials are never in the news.
- **"Completed" or "results posted" reads as success.** → The completed phrase says what it does not mean; no outcome word is on the page; the build fails on verdict wording.
- **A telling-name rule still links the wrong trial.** → A strong link never attaches anything; it only chooses what is read. The read, the indication-scored match and the audit decide.
- **The substance registry cannot be asked for 58,791 names quickly.** → Codes need no request. Names are asked set by set, within the source's allowance, and a name not yet asked is not telling.
- **Scaled counts are wrong.** → They rest on 30,471 leads screened after the full load. Task 3.1 screens every lead again against the whole corpus before any set is planned, and the plan prints real counts.
- **The daily load makes more claims due than a run refreshes.** → The run's existing limit holds and the rest stay due; the export waits only on those claims and says how many, so a backlog delays publishing and is visible.
- **An export refused because of a backlog blocks an unrelated release.** → The refusal names the claims and the command; the operator can refresh those claims by hand at once.
- **Opening the live-read page to a listing invites crawlers.** → Not indexed, not in the sitemap, the existing request limit, and only a chosen set until the store answers.
- **The listing goes stale between builds.** → It carries the date the records were read; the page reads the registry itself.

- **A batch's worst term fills the answer.** → Only fit terms are sent; a term that returns more than a set number of untied stories is marked unfit and not sent again; ten trials a request.
- **The news index is slow or refuses.** → A request that times out leaves its trials due; a search stops at the allowance and says what is left; no other route waits on it.
- **A paper is attached to the wrong trial.** → Only on the number in the publisher's field or on the registry's own list; never on a mention; never when a record carries more than three numbers.
- **A source's terms are read loosely.** → No client before a dated entry in `docs/sources.md`; a source that forbids or does not say is not asked; the wires' searches are not asked at all.
- **A found article is treated as the trial's report.** → It is a lead. Only a published claim that cites the trial removes "no news report is linked yet".

## Migration Plan

1. Note the new field list in `docs/sources.md`; widen the load; load every interventional study again (468 requests at 1,000 a page). Stored trials are updated in place.
2. The daily change load is `daily-trial-refresh`'s. After the full wider load of step 1 has completed, its changes-only step carries the wider fields. Add the cited-trial counts and the refresh order; watch a week of summaries.
3. Screen every lead again with strong links. Nothing is published by this.
4. Work set 1 through read, prepare and audit. Review with the operator what it gave before set 2.
5. Ship the listing for a chosen set and the state wording. Open the page to listed identifiers if the operator agrees.
6. After the store holds the corpus: answer every trial page from it, add search by word, retire the listing.

Each step can stop there. Rollback of 1 to 3 is to leave the new columns unread; of 5, to build without the listing.

## Open Questions

None is open for the operator. Each question below was put to the operator on 2026-11-17, in a question dialog, and is recorded with the choice made. The operator's answer to all but three was "Take recommendations": each is settled by the recommendation it was written with. Questions 1, 17, and 11 with 12 were answered in the operator's own words, and are marked so. Where an answer changed a requirement, the spec delta named beside it was revised the same day.

1. **Before the store exists, may a trial with no claim open the page that reads the registry on request?** *Decided 2026-11-17, stated by the operator:* yes, for the listed set only (trials under way in phase 2 or 3), from one static listing, not indexed by search engines. This replaces "wait for the store", which was said on 2026-11-16 before the existing page had been considered. `specs/trial-records` and `specs/trial-pages` already say it; task 5.5's setting is therefore on where the listing is built; `LISTED_TRIAL_PAGES=0` at build time turns it off.
2. **What the static listing holds.** *Decided 2026-11-17 (recommendation taken):* trials under way in phase 2 or 3, one file. Settled by the build: the set is `active-since-2025`, which is that choice less the 2,570 trials whose record the registry has not changed since 1 January 2025: 23,328 trials on the working database on 2026-11-17, in one file of 7,009,433 bytes (1.18 MB with Brotli). `thenwhat trials-listing --set` takes another named set. Each row also holds the acronym, conditions and intervention names, which is why it is 7.0 MB and not the 4.8 MB estimated above for five fields.
3. **Which fields the load gains.** *Decided 2026-11-17 (recommendation taken), and done:* those of decision 2's first table and decision 12's list, with planned primary outcomes. The reload of 2026-11-17 stored them for all 467,064 trials (`backfill/registry_load.py`, migration `0031`).
4. **Does a claim drafted on this route wait for its audit?** *Decided 2026-11-17 (recommendation taken):* yes, as every backfill batch does (`docs/adr/0007`).
5. **Is a held lead read on a strong link?** *Decided 2026-11-17 (recommendation taken):* yes, for the set being worked. A rejected lead is never read.
6. **May search engines index a trial page with no claim?** *Decided 2026-11-17 (recommendation taken):* no.
7. **The fixed phrases of decision 2.** *Decided 2026-11-17 (recommendation taken):* approved as written there, the no-report line included. The site holds them and its build still fails on verdict wording. They are in `site/src/lib/trial-page.mjs`. The build added three the decision did not have, for the operator to read with the rest (task 5.9): a state the mapping lacks ("The registry gives this study a state this page has no words for. The registry's own record shows it."), results posted with no date ("The registry record holds posted results."), and no phase ("The registry gives no phase for this study.", the wording `specs/trial-pages` already gave).
8. **The share of the ceiling for this route.** *Decided 2026-11-17 (recommendation taken):* 15 US dollars a month, held as a setting and checked before each batch.
9. **How recent is "recently completed".** *Decided 2026-11-17 (recommendation taken):* primary completion in the last two years, for the reading set `completed-recently`. The coverage set of question 17 is defined apart from it.
10. **Papers on a trial page.** *Decided 2026-11-17 (recommendation taken):* papers the registry names as results, and papers whose own record carries the number in the publisher's field, under two plain headings. Not papers that only mention the number.
11. **Pay for a mentions index?** *Decided 2026-11-17, stated by the operator:* no spend now. The operator sends Altmetric one email, asking for a quote and whether a public non-commercial site qualifies for the free key; the coordinating session drafts it. No client and no entry in `docs/sources.md` until an answer makes one wanted.
12. **Ask Media Cloud for a higher allowance, and whether batched queries are welcome?** *Decided 2026-11-17, stated by the operator:* yes, one email by the operator, drafted by the coordinating session. Until answered: ten trials a request and the noted 4,000 a week.
13. **May the wires' subject feeds be read by a program?** *Decided 2026-11-17 (recommendation taken):* not until the operator has read the three terms pages and, for EurekAlert, asked AAAS. No feed is read.
14. **Pay for a full-text news search?** *Decided 2026-11-17 (recommendation taken):* no, not now.
15. **Add PubMed's E-utilities as a source?** *Decided 2026-11-17 (recommendation taken):* yes. The operator registers the free key; the entry goes in `docs/sources.md` before the client (task 9.4).
16. **The dates of the two sets.** *Decided 2026-11-17 (recommendation taken):* the date is the operator's to set and is 2025-01-01 now. As built on 2026-11-17 the date is in the sets' names, `active-since-2025` and `completed-with-results-since-2025` (`backfill/trial_sets.py`), so a set never changes its meaning under one name; a later date is a new named set, not a changed setting. This is how "settings with no default" was met while the selection was being built; `specs/trial-coverage` names the sets as built.
17. **What "completed with results" means.** *Decided 2026-11-17, stated by the operator:* completion on or after the date, with results posted. As built: the registry lists the trial as completed, its completion date is an actual one in 2025 or later, and the record holds posted results: 3,141 trials stored on 2026-11-17. (The 2,114 counted at the registry on 2026-11-16 was by primary completion date.) Reading "recent" from the day results were first posted, whenever the trial completed (9,283 at the registry), is a later second step and is not built in phase 1.
18. **Wikipedia and Wikidata.** *Decided 2026-11-17 (recommendation taken):* dropped.

### What phase 1 is

Decided with the answers above, 2026-11-17: the first phase built is the free, deterministic routes of decision 13, with no spend and no new paid source. It is tasks section 9 and nothing else:

1. Route 1, the registry record's own references and links, read from stored records with no request.
2. Route 2, papers that carry the trial's number, from PubMed's E-utilities, after its entry in `docs/sources.md`.
3. Route 3, stored leads linked to trials on more than the intervention's name (acronym, development codes, other names), each link with its own reason and strength, and a reading order for a named set within the route's share.

The plain trial page and its static listing (section 5) are built beside it by another session. The batched news search (route 4), the wires, paid search and a mentions index are not in phase 1.

Not for the operator, to settle while building:

- The share of titles above which a substance's name is not telling (task 3.2).
- Whether a registry trial's list payload is a column or an object in the store (`cloudflare-source-of-truth`).
- **Reconciled on 2026-11-16** with `daily-trial-refresh` (pull request 268, open): see decision 10. This change's `specs/daily-run` adds requirements to a capability that change creates, so it is applied after it. If pull request 268 changes before it merges, decision 10's table is checked again (task 1.4).
