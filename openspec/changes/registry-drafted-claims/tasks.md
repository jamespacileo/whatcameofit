# Tasks

Write steps run on the one writer only. Every judgement an assistant makes is recorded as an assistant's, and the operator spot-checks a share.

## 1. Decisions and records before any build

- [x] 1.1 Write the ADR that a claim is one intervention or regimen for one indication and records its drafting source; record the superseded 2026-11-16 decision and affected wording in ADR 0013
- [x] 1.2 Record the sampled release decision and the continuing approval and export rules of ADR 0007 in ADR 0014
- [ ] 1.3 Revise Claim and Source article in `GLOSSARY.md` and add the term for a claim no report is linked to; verify the terms match the specs word for word and are used exactly in the site's phrases
- [ ] 1.4 Ask the operator for the share of wrong claims a sample may hold and the sample's size; record both here and in `.env.example` as settings with no default
- [ ] 1.5 Ask the operator for the monthly ceiling for model spend while sets are prepared; record it here; verify no setting is changed before the answer
- [x] 1.6 Verify the condition-term topic mapping is present on `main` before sections 3 to 6. The mapping and NLM hierarchy are in `thenwhat.clinical`, introduced by `843278e0` in the clinical classification work.

## 2. The dry run, with nothing written

- [ ] 2.1 Correct the rule that works out a search name so a name made only of ordinary words is not a name, with a regression test on a synthetic registry record, and record on the fault sheet the count of trials whose name changed; verify the count is recorded here
- [x] 2.2 Count, from stored records and with no request, how many trials of the first set carry the registry's condition terms, have no indication, and list more than one condition; record the table here
- [x] 2.3 Add `active-phase-2-3-or-completed-2026` for all eligible Phase 2 or 3 interventional trials across sponsors and results states; verify tests that an unknown name is refused with the list
- [ ] 2.4 Group the set by rule and print the plan of `specs/registry-drafted-claims`, drafting nothing; verify tests for two trials of one pair, one treatment with two conditions, a synonym of an existing claim's intervention, a trial with no name, an ordinary-word name, and terms that point to two groups
- [ ] 2.5 Draw fifty groups from the plan and judge whether each one's trials test one treatment for one condition; record the table here and show the operator, and stop if fewer than nine in ten are right

| Nov 18 local snapshot, all 27,698 eligible trials | Count |
| --- | ---: |
| Registry condition vocabulary in the stored payload | 0 |
| Stored arm membership | 0 |
| No registered condition label | 0 |
| No stored news search indication | 372 |
| More than one registered condition label | 10,670 |

The baseline audit found 15 correct groups out of 50. The read-only planner uses arm membership and full indications from stored records. The existing registry bulk loader can refresh those fields before the planner runs.

The arm-aware replay proposed groups for 39 of the same 61 trials. It held 21 for condition assignment and one crossover trial for treatment sequence. Only 30 of the original 50 groups had proposals for every member. The audit gate is pending.

The refreshed target set held 27,731 trials after 28 registry page requests in 26 seconds on the Mac. The planner proposed 19,451 groups covering 16,141 trial IDs. It held 11,590 for review, including 10,680 with multiple registered conditions. The verified live export linked 831 eligible trials. The production comparison found 73 proposed groups with exact name-and-indication claim candidates and 16 with registry alias candidates. These candidates await identity verification. Model spend was zero.

The next cached replay kept documented measurements outside treatment regimens, used explicitly named cohorts and preserved title-supported subtypes and patient contexts. It produced proposals for 16,719 trial IDs and held 11,012. The frozen audit supported 20 of 50 groups. Eleven still had scope errors, one was incomplete, two needed reviewer evidence and 16 had no proposal. Six scope receipts citing the cached trial records were exercised on the pilot, producing proposals for 44 of 61 trials. The grouping gate remains open.

A separate dry-run comparison of nine currently unlinked trials to exact-name-and-indication claim candidates found two with matching scope. Three were controls or background treatment, two were different settings and two needed more review.

The next arm-role replay excluded all three reference regimens from those existing-claim candidates. It corrected one more group in the frozen sample, giving 21 of 50 supported. A separate draw of 50 from the full cohort's proposed groups found 16 supported, 28 scope errors and six needing further evidence. That draw preceded a targeted fix for product-prefixed placebo labels.

The MeSH refresh loaded condition descriptors for 22,446 trials. The final cached plan proposed 20,150 groups. It found a unique general vertical for 5,666, conflicting evidence for 8,552, and insufficient evidence for 5,932. The grouping gate remains open.

An offline replay selected exact registry spans for 11 records from known grouping failures. All 12 selected pairs grounded against their source fields. The replay produced 10 groups and split the four trials of one product code into three injection trials and one tablet trial. The options code uses the existing Pydantic AI native JSON client and response cache. A simulated provider verified one model response and one cache hit. The monthly live-run cap is awaiting the operator's setting.

All 27,731 cached trials produced review packets. The median packet has 1,301 characters and the 95th percentile 3,321. A separate holdout has 52 trial packets from 30 proposed groups and 20 held trials, with both earlier audit samples excluded.

The cached matching-placebo replay checked all 27,731 eligible records, removed 6 reference-arm memberships, and proposed 20,146 groups. It took 6.4 seconds and made no requests. An exact-name candidate for ulcerative colitis had been proposed from an add-on trial's reference arm. The current rule retains the full tested combination. The grouping gate remains open.

A fresh fixed-seed scope audit drew 50 groups covering 57 trial records, excluding 174 trial IDs from earlier audits and the reserved holdout. An assistant supported 16 groups, found 27 scope errors, and held seven for more evidence. The existing receipt path accepted seven verified corrections from their exact registry excerpts. The audit used no requests and the 45-of-50 gate remains open.

Of 11,563 unlinked trials with a proposed scope but no unique topic in the MeSH-enriched plan, 6,482 have a group for which one MeSH descriptor supports more than one topic. This includes tumor descriptors that support both cancer and an organ group.

The qualifier replay retained two previously omitted genotype restrictions and moved a broad stage proposal to review. The same 50 groups had 18 supported, 24 wrong and eight needing review. The full cached plan took 2.6 seconds, produced 20,224 groups, and left 11,021 trial scopes unresolved. One suffix rule was informed by this sample. The 45-of-50 drafting threshold still needs a fresh audit.

The NVMe development set holds 120 cases from 127 trials, with earlier audit and holdout trial IDs excluded. The detailed registry pull found eligibility text for all 127 trials and arm descriptions for 109. An assistant reviewed 18 cases and found evidence absent from the bulk snapshot in 12. The arm-specific command reads the frozen protocol version, validates quoted fields against the assigned arms, and can request a second pass for omitted scope. In the offline comparison, the median packet grew from 1,363 to 5,775 characters and the 95th percentile grew from 3,278 to 14,923. Simulated native JSON calls exercised both stages and the exact-request cache. Live model accuracy and spend are pending.

## 3. Drafting and preparation

- [x] 3.1 Let a claim record what it was drafted from, and let a claim drafted from registry records have no source article, headline, summary or first reported date, in a new migration; verify tests that a claim entered by an operator with no article is still refused and that the record does not change when an article is added
- [ ] 3.2 Add `thenwhat draft-from-registry` for a named set, with `--limit`; verify tests that a group an existing claim holds drafts nothing and hands its trials on as candidates, that a second run drafts nothing, and one success and one refusal of the command
- [x] 3.3 Have `thenwhat prepare --pending` take a registry draft: its drafting trials as candidates scored for its indication, approval only when one of them is approved, otherwise pending and listed; verify tests of both outcomes and that no trial is approved for having led to the draft
- [x] 3.4 Hold a registry draft that preparation approves awaiting audit; verify a test that no export publishes it before release and that the export says how many it left out
- [x] 3.5 Verify with a test that a read's same-claim decision attaches an article to a published registry-drafted claim, sets its first reported date, and does not hold it
- [ ] 3.6 Draft and prepare 200 claims of the first set, then audit every one; record here the drafts, the share approved, the share left pending and why, the duplicates found, the registry requests and the decision step's cost, and show the operator

Synthetic preparation exercised both match outcomes on the Mac. It fetched the drafting trial by identifier when name search missed it and sent it through ordinary indication scoring. A different approved trial alone left the claim pending. An approved drafting match held the claim, and export counted and excluded it. A later first article joined a published registry claim without adding a new audit hold.

A local fixture verified exact-ID handoff to an existing claim without a second draft. Candidates go through normal trial scoring. PostgreSQL and the D1 store preserve queued IDs across retries. The batch command still needs to consume the handoff.

## 4. The site

- [x] 4.1 Add to the export whether a report is linked and what a claim was drafted from, with no headline or summary for a claim with no article; regenerate `site/export.schema.json` and raise the schema version; verify the tests that compare both pass
- [x] 4.2 Word a claim with no report from fixed phrases in the site's own files, and extend the build's wording check to these phrases and to words of advice; verify tests that the build fails on a verdict word and on a word that offers the treatment to a reader
- [x] 4.3 Show the fixed line on a claim with no report and none of date first reported, promises or reported statements; verify tests of a claim with no report, the same claim after an article is linked, and the extension's view
- [ ] 4.4 Let every list of claims be narrowed to reported claims, kept in the address and working with the status and topic narrowing; verify tests on the Claims list, a topic page and the home page's lists
- [ ] 4.5 State how many claims a report is linked to wherever the site counts claims, and keep claims with no report out of rows whose subject is a report; verify tests of the home page's count and of the day-by-day list
- [ ] 4.6 Build a preview from an export holding the 200 claims of 3.6 and show the operator the home page, one topic page and three claim pages; record here whether lists open on every claim or on reported claims
- [ ] 4.7 Build the site from an export holding the whole first set as drafted in the plan, and record here the build time, the output's size and the size of `lookup.json`; report the figures to `cloudflare-source-of-truth` and stop if the build does not fit
- [ ] 4.8 Deploy a pull request preview and read twenty pages of claims with no report with the operator; record here anything reworded

Storage and export were exercised with a synthetic registry-only claim on the Mac. PostgreSQL and the SQLite store produced the same claim. The audit hold excluded it from export, and linking a first article later preserved its drafting origin. The PostgreSQL migration preserved a legacy row and refused to downgrade with a registry claim present. The version 3 export built a claim page and a search entry. Fixtures and the run receipt are stored on the NVMe.

The synthetic site build renders the site's fixed registry wording, the absence of a source report, and the first report after it is linked. The lookup and extension checks omit the first reported date and promises while a report is absent. The same import-time wording check rejects verdicts and offers of treatment.

The capacity rehearsal built 200 synthetic additions in 47.2 seconds with 1,970 files and a 122,106-byte lookup. The 600-claim warm-cache build yielded 5,578 files and a 364,106-byte lookup. A 20,224-claim synthetic stress export plus the seed exceeded the budget before rendering, at a floor of 161,800 files. The finding is recorded in `cloudflare-source-of-truth`. The full real-cohort build remains pending.

## 5. The sampled audit

- [ ] 5.1 Add `thenwhat audit sample` for a held batch: a drawn sample of the set size, recorded with its seed, the whole batch when smaller; verify tests of both and that a second call returns the same sample
- [ ] 5.2 Record each sampled claim's judgement with who made it, an assistant's as an assistant's; verify tests of both and that a wrong claim is not released
- [ ] 5.3 Release a batch with `thenwhat audit clear --batch` only when every sampled claim is judged and the share judged wrong is at or below the figure, and never while the figure is empty; verify tests of a sample at the figure, over it, unfinished, and with no figure
- [ ] 5.4 Offer the operator a drawn share of an assistant's judgements and record the count that differ; verify one test of its figures
- [ ] 5.5 Verify with a test that a release changes no review state and that a released claim says no person checked it unless a person approved it

## 6. The first set

- [ ] 6.1 Draft and prepare the first set in slices of the size the operator sets, each slice planned before it runs; record here, for each slice, the drafts, the share approved, the requests and the cost
- [ ] 6.2 Audit each batch on a sample, record the sample's size, the count wrong, the defects by category and the operator's spot-check, and release or hold as the figure says
- [ ] 6.3 After the first set is published, count again the trials of the set a claim cites and record the figure here beside the 1.7% of `proposal.md`
- [ ] 6.4 Show the operator the figures of 6.1 to 6.3 before any second set is named

## 7. Records

- [ ] 7.1 Update `CLAUDE.md`, `PRODUCT.md` and `docs/backfill-loop.md` for what a claim is, the drafting command, the order after it (`thenwhat prepare --pending`, sample, release, export), and that the daily run starts none of it; verify `make scripts-test` fails if it would
- [ ] 7.2 Note in `trial-first-route` and `headline-funnel` what this change supersedes and what it gives their routes; verify both `design.md` files name this change
- [ ] 7.3 Regenerate `site/data/seed-export.json` if the seed's export changes, run `make check` and `openspec validate registry-drafted-claims --strict`; verify all pass
