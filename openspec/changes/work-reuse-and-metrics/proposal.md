# Proposal

## Why

The tracker is about to take leads from more places at once: bulk files worked on several devices (`file-based-backfill`), readers' lookups, and four more groups of outlets the operator added on 2026-11-16. The operator expects millions of leads, and asked for two things: a way to reuse work and avoid waste that holds at that size, and measurements of the time and cost of each part of processing one address end to end, so the pipeline can be tuned from evidence.

What the present database shows, measured on 2026-11-16 on a restored copy (829 claims, 357,964 leads on listed outlets):

- **Model spend to date is 16.08 US dollars, and 10.83 of it (67%) is triage.** Triage scored 357,964 headlines and rejected 348,480 of them (97.3%). 4,814 passed and 4,670 were held. Most of what triage costs is spent saying no to headlines that are not about health.
- **A headline costs 300 input tokens, of which about 15 are the headline.** The question and each option's description are sent with every headline (`backfill/link_triage.py`).
- **Work is repeated.** 4,236 lookup match decisions were made for 1,738 distinct inputs, so 59% repeated one already made. A claim takes 21.7 trial match decisions on average. 6,681 leads share their exact title with another lead.
- **A quarter of reads fail on the page.** Of 1,603 leads read, 364 (23%) could not be read.
- **Nothing records how long anything takes.** `llm_usage` holds tokens and cost with no duration; the ledger holds the time of the last attempt and no more. Time per step, time waiting on a source, and time end to end cannot be answered today.

Money is small at this size, about 2 cents a published claim. Time and requests are the scarcer things: a page reader at home, registries with rate limits, and a store that runs one query at a time. And none of them is measured.

## What Changes

- **Measurements for every step of every address.** Each step records when it started, how long it ran, how long it waited, what it cost, what it asked of which source, and how it ended, including whether stored work answered it. They add up to one account of an address from first seen to published or dropped.
- **Reports from those measurements**: time and cost by step, by writer and by day; cost and time for each published claim; where addresses wait; how often stored work was reused.
- **One key for each unit of work**, so a result is made once and used by every writer: a triage score, an article read, a page fetch, a registry search, a match decision. A result of "nothing" or "no" is stored and reused like any other.
- **Cheaper steps decide first.** Before a model is asked about a lead, rules that cost nothing are applied, then a small classifier that runs on the device. The model is asked only about what they leave undecided. **BREAKING** for `lead-triage`: not every in-scope lead is scored by the decision step.
- **The triage call is reshaped** so the fixed wording is not paid for with every headline. How much it saves is measured before it replaces the present call.
- **Reads are ordered by what they are likely to yield**, and an outlet that keeps refusing the reader is left alone for a while.
- **The same story on many outlets is read once**, and the others are offered as further articles of the claim it made.

Not in this change:

- The store, its merge and the run folder. This change adds keys, measurements and earlier steps to `cloudflare-source-of-truth` and `file-based-backfill`; it does not replace either.
- Any change to how a claim is approved, prepared, audited or given a status.
- Measuring readers. A measurement holds a step and an article, never who asked.
- A hosted monitoring product. Measurements are kept in the store and in files.
- Routes for papers, regulators' notices, video and posts.

## Capabilities

### New Capabilities

- `processing-metrics`: what is measured for each step of each address, how it is kept and for how long, and the reports made from it.
- `work-reuse`: the unit of work and its key, how a stored result is found and reused by any writer, how a negative result is kept, and when work is done again.
- `lead-prefilter`: the steps that settle a lead before the decision step is asked: rules, then a classifier trained on stored scores, with the recall each must keep and how that is checked.

### Modified Capabilities

None by delta. `lead-triage` (in `openspec/changes/social-link-backfill`, not yet synced) says every in-scope lead is scored; `lead-prefilter` narrows which leads reach it, and the delta to `lead-triage` is written when that spec is synced.

## Impact

- **Depends on** `cloudflare-source-of-truth` (the store holds the keys and the daily measurements) and `file-based-backfill` (the run folder holds a device's measurements and prefilter). Measurements can be built first, on the present pipeline.
- **Code:** a small measurement module used by every step; `backfill/link_triage.py`, `link_read.py`, the lookup Worker and the store-side consumer record through it. A prefilter stage before triage. Result keys in the store's schema.
- **Store:** tables for work results by key and for daily measurements. Both are small beside the leads.
- **Dependencies:** a classifier library for the device-side prefilter; which one is `design.md` decision 5.
- **Guardrails:** no model decides a status, and none here does: the prefilter decides only whether a headline is worth asking the decision step about. No article text is kept: a stored read is the extraction's structured result. Nothing about a reader is measured.
- **Cost:** expected to lower spend; by how much is what the measurements are for. Estimates in `design.md` are marked as estimates.
