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

## Goals / Non-Goals

**Goals:**

- Every stored trial can be opened on the site as a page of registry facts, worded without verdict or advice.
- Stored leads reach the trials they are about with no request for each trial, in an order the operator sets.
- A trial page and a claim page never state different facts about one trial.
- Every stored trial is kept current daily, and nothing that costs money or publishes is started by that.
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
- *A lighter audit for claims from this route.* The operator confirmed on 2026-11-16 that the audit hold stays for backfill batches. A set is a backfill batch. Offered again as open decision 4.
- *A trial-level record of "reported" without a claim.* It would be a second, weaker kind of claim with none of a claim's rules.

So a trial gets a report in one way only: a published claim cites it.

### 9. A trial page and a claim page cannot disagree

They could disagree in two ways, and each is closed differently.

**About the trial's own facts** (state, phase, dates, results posted). Today a claim's trial facts are read from the record stored with its events, and the corpus holds another copy from the bulk load, read on another day. Rule: for one registry identifier, both pages state facts from the record fetched most recently, whichever copy that is, and both show the date it was read. In the store on Cloudflare a record is kept once under its checksum (`docs/adr/0008`), which makes this the natural shape; before then the export and the listing apply the same "most recent" rule that `trial-facts` already states.

**Between the trial's facts and the claim's status.** A status comes only from approved events, so a record can say "terminated" for a day while the claim still reads "Phase 3". Rule: when a load changes the state, phase, dates or results posting of a trial that a claim cites, that claim is due for its registry refresh, which is the existing step (one registry request a trial, events approved by the existing rule, status derived again), and the export is not written while a cited trial's refresh is due. The trial page lists the claim with the status the export gives it, and never words a status of its own.

What is left is a matter of minutes inside one run, not of pages disagreeing in public.

### 10. The daily change load: what it makes due, and what it never starts

Each day the load asks the registry for interventional studies changed since the last completed load (`registry-corpus`, "Loading changes only"), with the fields of decision 3.

**It does, by itself:**

- update the stored record, payload and fetch time;
- store a trial the registry has added.

**It makes due, and these may run without a person**, because they send nothing or ask only the registry, and call no model:

- the offline linking, for a trial that is new or whose names or conditions changed;
- the registry refresh of a claim that cites the trial, when its state, phase, dates or results posting changed (decision 9);
- the full record, for a trial in a named set whose record newly says results are posted (decision 3).

**It makes due, and this waits for the operator:**

- the news search for the trial (`article-leads`), as `registry-corpus` already says. At 4,000 requests a week it is run by command, for a set, never for the corpus.

**It never starts, by any path:** a model call of any kind (triage, a read, a reading, a match decision); a request to the page reader; a news search; a new claim; a new match or its approval; a status that changes other than through a cited trial's approved registry events; a failure flag; an archive or its undoing; a release from audit; a message to a reader.

A day's load is reported: how many changed, how many were new, how many cited trials changed and which claims that made due.

### 11. What ships before the store, and what waits

**Needs nothing from `cloudflare-source-of-truth`:**

- The wider load and the daily change load (pipeline only).
- Strong links, sets and the ordered reads (pipeline only; works on the present database and, when it lands, in a run folder of `file-based-backfill`).
- A **trial listing** built into the static site for a chosen set: identifier, title, state, phases, start date. For the 25,898 trials under way in phase 2 or 3 it is about 4.8 MB before compression, loaded only when a reader searches. Search then answers a trial identifier or a title from the listing, beside the claims.
- The trial page's state wording (decision 2), on the page that exists.
- If the operator agrees (open decision 1): the existing page answers for identifiers in the listing as well as for cited ones. It reads the registry on request, a day's reuse, 60 requests a minute for each location, no model. Uncited pages stay marked not to be indexed and out of the sitemap.

**Waits for the store (`docs/adr/0008`):**

- A page for every stored trial. 467,064 pages cannot be built (the listing alone is 73 MB) and should not each cost the registry a request. With the records in D1 the Worker answers from the store: no request to the registry, the same rules, the read date shown.
- Search over every stored trial by word. The store's full-text index does it; a static file cannot.
- Retiring the listing: once the store answers, the listing is a query.

**Asked of `cloudflare-source-of-truth`:** its size criterion was met at 504 MB with 43,320 registry trials. With 467,064 trials at 909 bytes of payload and their columns, the registry corpus alone is an estimated 0.6 to 0.9 GB. Still inside the 3 GB criterion by estimate; to be measured in that change before its migration. Its design says a registry trial's payload goes to R2 under its checksum: that is 467,064 small objects, where one column would do, since the largest is 12 KB. Raised there, not decided here.

Considered for the static site: a file for every thousand identifiers (468 files of about 156 KB), so any stored trial is answered by identifier with one fetch. It gives no search by word and is retired by the store. Offered as open decision 2.

## Risks / Trade-offs

- **A page of registry facts reads as an endorsement or a way in.** → No word about taking part, no location or contact, the site's notice that a registered trial is not a treatment option on every trial page, and the state worded as "under way".
- **"No news report is linked yet" reads as "nobody reported it".** → The line says linked, and the method page says how leads are found and that most trials are never in the news.
- **"Completed" or "results posted" reads as success.** → The completed phrase says what it does not mean; no outcome word is on the page; the build fails on verdict wording.
- **A telling-name rule still links the wrong trial.** → A strong link never attaches anything; it only chooses what is read. The read, the indication-scored match and the audit decide.
- **The substance registry cannot be asked for 58,791 names quickly.** → Codes need no request. Names are asked set by set, within the source's allowance, and a name not yet asked is not telling.
- **Scaled counts are wrong.** → They rest on 30,471 leads screened after the full load. Task 3.1 screens every lead again against the whole corpus before any set is planned, and the plan prints real counts.
- **The daily load makes thousands of claims due at once after a registry-wide change.** → A cap on refreshes a day; the export waits only on cited trials whose refresh is due, and says how many.
- **Opening the live-read page to a listing invites crawlers.** → Not indexed, not in the sitemap, the existing request limit, and only a chosen set until the store answers.
- **The listing goes stale between builds.** → It carries the date the records were read; the page reads the registry itself.

## Migration Plan

1. Note the new field list in `docs/sources.md`; widen the load; load every interventional study again (468 requests at 1,000 a page). Stored trials are updated in place.
2. Turn on the daily change load. Watch a week of its reports.
3. Screen every lead again with strong links. Nothing is published by this.
4. Work set 1 through read, prepare and audit. Review with the operator what it gave before set 2.
5. Ship the listing for a chosen set and the state wording. Open the page to listed identifiers if the operator agrees.
6. After the store holds the corpus: answer every trial page from it, add search by word, retire the listing.

Each step can stop there. Rollback of 1 to 3 is to leave the new columns unread; of 5, to build without the listing.

## Open Questions

Decisions for the operator. Each has the assistant's recommendation first.

1. **Before the store exists, may a trial with no claim open the page that reads the registry on request?**
   - *Yes, for the listed set only (recommended).* The page exists, costs no model and no build, and the wording gets tested on 26,000 trials before 467,000.
   - *No, wait for the store.* What was decided on 2026-11-16, when the existing page had not been considered. Nothing uncited is visible until then.
   - *Yes, for any stored identifier.* Every trial at once, each first view a request to the registry.
2. **What the static listing holds.**
   - *Trials under way in phase 2 or 3, 25,898, one file of about 4.8 MB (recommended).*
   - *Phase 3 of any state, 50,238, about 8 MB by proportion.*
   - *Every trial, as 468 files by identifier:* answers an identifier, no search by word.
   - *Nothing until the store.*
3. **Which fields the load gains.** Recommended: those of decision 2's first table, 909 bytes a trial. The alternative adds planned primary outcomes at 1,224 bytes, so an uncited page can name what the trial set out to measure.
4. **Does a claim drafted on this route wait for its audit?** Recommended: yes, as every backfill batch does (`docs/adr/0007`). The alternative, publishing by rule when the article's page names a registry number that preparation then approves, is what `docs/adr/0009` allows a reader's lead, and would remove the audit as the limit on this route.
5. **Is a held lead read on a strong link?** Recommended: yes, for the set being worked. Otherwise only passed leads are read and the route changes order alone.
6. **May search engines index a trial page with no claim?** Recommended: no, until the wording has been read on real pages; the page restates a public record. The alternative is the largest change to the site's size the project has considered.
7. **The fixed phrases of decision 2**, especially "completed", "unknown" and the no-report line. The operator's to approve or reword.
8. **The share of the ceiling for this route.** Recommended: 15 dollars a month, checked before each batch like any other.
9. **How recent is "recently completed".** Recommended: primary completion in the last two years.
10. **Should a trial page name the papers its registry record lists as results?** Not in this change. It is a way a trial gets something beyond registry facts with no search and no model (`Results paper` in the glossary), and is the natural next change.

Not for the operator, to settle while building:

- The share of titles above which a substance's name is not telling (task 3.2).
- Whether a registry trial's list payload is a column or an object in the store (`cloudflare-source-of-truth`).
- What the sibling work on trial status changes has already built of the daily load; this change's section 2 is to be reconciled with it before any code.
