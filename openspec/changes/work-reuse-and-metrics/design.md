# Design

## Context

Measured on 2026-11-16 on a copy of the present database restored from that day's dump (Postgres, 829 claims, 2,686,680 link leads of which 357,964 are on listed outlets):

**Spend, from `llm_usage` (34,882 calls, 2026-11-11 to 2026-11-16, 16.08 US dollars in all):**

| Purpose | Calls | Cost | A call |
| --- | --- | --- | --- |
| Lead triage | 18,065 | 10.83 | 0.00060 |
| Entity match | 4,482 | 1.73 | 0.00039 |
| Link lead extraction (a read) | 1,564 | 1.33 | 0.00085 |
| Paper match | 971 | 0.56 | 0.00057 |
| Readings | 3,026 | 0.52 | 0.00017 |
| Statement check | 1,351 | 0.44 | 0.00033 |
| Everything else | 5,423 | 0.67 | |

**The funnel of leads on listed outlets:** 357,964 scored; 348,480 rejected (score under 0.1), 4,670 held, 4,814 passed (0.7 or more). 1,603 read: 733 drafted a claim, 242 joined one, 364 could not be read, 136 were not one treatment, 51 were business news, 77 were left unresolved. 975 leads led to 739 claims.

**Triage's tokens:** 5,994 input tokens a call of 20 headlines, so 300 a headline. Headlines average 58 characters, about 15 tokens. `link_triage.py` notes why: "The question and the options' descriptions are sent with every headline."

**Where passes come from:** of 545 listed outlets, 114 have ever had a lead pass. The pass rate among outlets with 2,000 leads or more runs from 14.5% (medicalxpress.com) and 6.9% (sciencedaily.com) to under 1% (nytimes.com 0.9%, bloomberg.com 0.5%).

**Rules tried as a filter, on the assistant's quick lists of health words and section names in addresses, not tuned:**

| Rule | Passed leads kept | Leads that led to a claim kept | Rejected leads dropped |
| --- | --- | --- | --- |
| A health word in the title | 82.9% | 87.0% | 92.2% |
| That, or a health or science section in the address | 87.8% | 92.1% | 87.7% |

**Repeats:** `decision_log` holds 4,236 lookup match decisions for 1,738 distinct inputs; 17,953 entity match decisions for 17,121; 361,391 triage decisions for 357,964. 21.7 entity match decisions were made for each claim. Among leads on listed outlets, 6,681 share their exact title with another.

**Labels:** 560 leads carry a label given by an assistant (294 not health, 156 health but not a treatment report, 110 treatment report). There are no labels by the operator in the data.

**Time:** not recorded. `llm_usage` has no duration. `work_entry` has `last_attempt_at` and attempts. From call times alone: triage ran at up to 5,419 calls in an hour; reads peaked at 256 in an hour.

`cloudflare-source-of-truth` puts the records in D1 with one merge for all writers. `file-based-backfill` gives a device a run folder and a reference file of what the store already scored and read. This change builds on both.

## Goals / Non-Goals

**Goals:**

- Know, for any address and any day, how long each step took, how long it waited, what it cost and how it ended.
- Never pay twice for the same question, whoever asks: a device, the store-side consumer or a reader's lookup.
- Ask a model about a lead only when something cheaper could not settle it, and prove what the cheaper thing lets through.
- Every saving claimed is a measured one.

**Non-Goals:**

- Squeezing dollars for their own sake. At 2 cents a claim, the aim is time, requests and headroom at ten times the leads.
- Changing any rule that approves, prepares, audits or derives a status.
- Replacing the decision step for triage. It stays the judge of what the cheaper steps leave.
- Tracing or profiling readers.

## Decisions

### 1. Measurements come first, and are spans

Each step, when it handles one address or one batch, records a **span**: step and step version; the writer (a device by name, store-side, lookup); the address key or batch size; when it started; how long it ran; how long it waited before running and on what (a queue, a source's rate limit, the spend ceiling); the outcome; whether stored work answered it and from which key; model tokens in and out and cost; requests sent, by source; rows written. Spans for one address share a **trace** identifier made from the address key and the run or request that started it.

One small module records spans; a step wraps its work in it. No step computes its own timing.

Built first because every other decision here is a guess until it exists. It can be added to the present pipeline before the store moves.

### 2. Where measurements are kept

- **On a device:** `spans.jsonl` in the run folder. Pushed with the run as daily totals, not span by span.
- **Store-side and in the Worker:** written to Workers Analytics Engine or logs for the raw spans, kept for days, and to a `measure_daily` table in D1 for totals by day, step, step version, writer and outcome.
- **How long:** single-step measurements are kept 30 days where they were made, and those of readers' lookups 7 days, set by the operator on 2026-11-16.
- **In D1 for good:** only the daily totals. At a million leads a month that is a few thousand rows a month, not millions.
- **For each published claim:** the sum of the spans that led to it, stored with the claim's run: total time from first seen, time working, cost.

A lookup's spans carry the step and the article's address key for the day they are needed and are then only totals. Nothing in a span says who asked.

Considered: every span in D1. At tens of spans an address it would outgrow the leads it describes.

### 3. A unit of work has a key, and its result is stored once

| Work | Key | Stored result | Done again when |
| --- | --- | --- | --- |
| Triage score | address key, title hash, triage version | score, decision id | the version rises or the title changes |
| Page fetch | address key | outcome, time; for a refusal, the kind | a waiting time passes that grows with each refusal |
| Article read | address key, extraction version | the extraction's structured result, or why none | the version rises |
| Registry search | registry, intervention, indication | the trials found, by registry number | 24 hours for a claim being worked; on schedule after |
| Paper search | index, intervention, indication | the papers found, by identifier | as registry search |
| Match decision | claim, record, decision version | answer, score, reasons | the version rises or the record's payload checksum changes |
| Raw payload | checksum | the payload, in R2 | never |

Rules that hold for all of them:

- **A negative result is a result.** "Not health", "nothing found" and "cannot be read" are stored and reused. The present database repeats 59% of lookup match decisions.
- **The version is in the key.** Rewording a question raises its version and only then is the work redone.
- **Any writer reads the key before doing the work.** A device reads it from the reference file; the store-side consumer and the Worker read it from the store.
- **A stored result says which run made it**, like any record.
- **No article text is a stored result.** A read's result is the extraction's fields.

In D1 this is one table for results by kind and key, beside the records the results belong to. The reference file of `file-based-backfill` already carries scores and read outcomes; it gains the other kinds a device uses.

### 4. Rules before any model

Applied by the load and screening, at no cost, and recorded on the lead so later steps and the classifier can use them:

- **Outlet pass rate**, kept by outlet from stored scores and updated as scores arrive.
- **Section in the address** (a health, medicine or science section).
- **Words in the title**: topic words and a list of health words.
- **Shares**: how many places shared it.

On the figures in Context, no combination of these tried so far can be a gate: the best keeps 87.8% of passes. They are used to **order** work, so that what is likely to pass is scored and read first, and as **inputs** to decision 5. A rule becomes a gate only when measured on held-out scores to keep at least the recall decision 5 requires.

### 5. A classifier on the device settles the obvious

A small text classifier, trained on stored triage scores (357,964 to begin with), gives each headline a probability of passing or being held. Below a **settle threshold** the lead is marked settled as not health by the prefilter, with the classifier's version and its probability, and is never sent to the decision step. Everything else is.

- **The threshold is set from a required recall, not picked.** The setting is the share of passed-or-held leads that must still reach the decision step, with no default. The threshold that meets it is computed on held-out scores and stored with the classifier's version.
- **It is checked as it runs.** A set share of the leads it settles is sent to the decision step anyway. If more of that sample passes than the required recall allows, the prefilter stops settling and says so.
- **It is a model, and is treated as one:** versioned, its training data and held-out figures recorded, no identifier of it in code.
- **It decides one thing:** whether a headline is worth asking about. It approves nothing and is never shown on the site.
- **Its teacher is triage, which is itself imperfect.** The 560 assistant-labelled leads are the only independent check today. Decided by the operator on 2026-11-16, following their decision of 2026-11-14 that an assistant's labels count: an assistant labels a fresh sample of about 1,000 headlines without seeing scores, recorded as assistant-made and never as a person's, and the operator checks 50 of them.

Which library: a linear model over word and character n-grams (scikit-learn) is tried first. It trains in seconds on this much text, runs anywhere Python does, and its misses can be read. An embedding model is tried only if the linear one cannot reach the recall.

**Required recall, set by the operator on 2026-11-16: 99%.**

Tried the same day, as a probe and not the classifier of task 5.3: a linear model over word and character n-grams of the headline and outlet, trained on 250,574 stored scores and tested on 107,390 it had not seen (one random split, nothing tuned, 20 seconds to fit and score). In the test set 2,845 leads had passed or been held, 1,457 had passed, and 288 had led to a claim.

| Required recall | Leads settled with no model call | Passed leads kept | Leads that led to a claim kept | Passed-or-held lost in 100,000 leads |
| --- | --- | --- | --- | --- |
| 99.9% | 22.3% | 100.0% | 100.0% | 2 |
| 99.5% | 58.4% | 100.0% | 100.0% | 13 |
| 99.0% | 72.3% | 99.9% | 100.0% | 26 |
| 98.0% | 85.8% | 99.6% | 100.0% | 52 |
| 95.0% | 93.1% | 98.7% | 99.3% | 132 |
| 90.0% | 95.6% | 97.1% | 96.9% | 264 |

What is lost at 99% is nearly all held leads, not passed ones. Of the assistant-labelled leads that fell in the test set, all 30 treatment reports were kept at 99%, 93% of 46 health-but-not-treatment, and 17% of 86 not-health. So at the operator's setting about seven in ten triage calls are not made. The figures are from one split of one probe and are to be measured again.

Considered: making the decision step cheaper and stopping there (decision 6). Both are done; they multiply.

### 6. The triage call stops paying for its wording with every headline

The Decisions API takes one shared input and up to 400 questions, each with its own options and descriptions (`docs/sources.md`). Today each headline is a question carrying the full wording. To try, each measured on the same 2,000 stored leads against their present scores:

1. The wording once in the shared input, each question reduced to its headline and bare option values.
2. More headlines to a call.
3. Both.

A shape replaces the present one only if its scores agree with the present ones on that sample within the tolerance, and the triage version rises when it does.

**Tolerance, set by the operator on 2026-11-16:** at least 98% of the sample's leads fall in the same band (rejected, held, passed) as their stored score, and no lead that passes today is rejected by the new shape.

The floor for any such figure, measured the same day: 588 headlines were scored twice by the present triage, and 582 (99.0%) fell in the same band both times; none went from passed to rejected, one from passed to held, one from rejected to passed; of 7 first held, 5 stayed held. The repeats are few, mostly rejected, and some may span a rewording, so 99.0% is an indication. If no shape holds, the present one stays and decision 5 carries the saving.

Estimate, not measured: up to ten times fewer input tokens.

### 7. Reads in order of likely yield, and patience with outlets that refuse

- Leads to read are ordered by: names a topic; triage score; the outlet's rate of readable pages and of reads that led to a claim; shares.
- An outlet whose pages keep failing gets a waiting time that grows, by outlet, and is tried again after it. 364 of 1,603 reads failed; the measurements will show how many of those were the same few outlets.
- A read that fails is stored under its key with the kind of failure, so no writer tries it again before its time.

### 8. The same story on many outlets is read once

Moved to `headline-funnel` (capability `lead-story-groups`) on 2026-11-18, when the open changes were pruned: its story groups decide the same thing by a closer measure than an exact title. What follows is kept as the reasoning at the time.

Leads whose titles match after tidying, within a few days of each other, on different outlets, are grouped. The one most likely to be readable is read. If it leads to a claim, the others are offered to the same-claim decision as further articles of that claim, which is one cheap decision each in place of a read each.

Exact-title matches are 6,681 of 357,964. Near matches are not yet counted, and a near match can be a different story, which is why the same-claim decision still judges each.

### 9. Reports

`thenwhat measure` prints, for a range of days: time working, time waiting and cost by step and writer; the funnel with how many leads each tier settled; reuse, as the share of each kind of work answered from a stored result; cost and time for each published claim, median and slowest; the slowest steps and the sources waited on longest. The same totals are available from the store for the operator's own queries.

### 10. Order of work

1. Spans and reports, on the present pipeline.
2. A week of real measurements, read with the operator.
3. The triage call's shape.
4. Result keys, in the store's schema as it is designed.
5. The classifier.
6. Read ordering (grouping of the same story moved to `headline-funnel`).

Steps 3 to 6 are each kept or dropped on what step 1 shows.

## Risks / Trade-offs

- **The prefilter drops a real treatment report.** → The required recall is a setting with no default; a sample of what it settles is always scored; it stops itself when the sample disagrees.
- **Triage's own mistakes are learned by the classifier.** → Independent labels, and the sample in decision 5 catches drift from triage, not triage's errors; the second needs the labels.
- **A stored negative result outlives its truth** (an article that was unreadable becomes readable; a registry gains a trial). → Every negative result has a time after which it is asked again.
- **Measuring slows the work.** → A span is a line in a file or one write in a batch already being sent.
- **Daily totals hide a single bad address.** → Raw spans are kept for days where they are made, long enough to look.
- **A reshaped triage call scores differently.** → It is compared on a fixed sample first and gets a new version.
- **Grouping joins two different stories.** → Grouping only chooses what to read first; the same-claim decision still judges each article.

## Open Questions

- **Answered on 2026-11-16:** required recall 99% (decision 5); tolerance 98% in the same band and no passing lead rejected (decision 6); single-step measurements kept 30 days, and 7 days for those of readers' lookups (decision 2); an assistant labels a sample of about 1,000 headlines, marked as assistant-made, and the operator checks 50 of them (decision 5).
- **The sample's make-up.** Proposed by the assistant: 300 from what the prefilter would settle, 300 held, 200 passed, 200 rejected, drawn without scores shown.
- **What counts as too much disagreement** between the operator's 50 and the assistant's labels for the same headlines.
- **Whether Workers Analytics Engine is wanted** for store-side spans, or logs suffice. Its terms and limits have not been read.
