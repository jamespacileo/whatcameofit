# Tasks

Write steps run on the one writer only. Every judgement an assistant makes is recorded as an assistant's, and the operator spot-checks a share.

## 1. Decisions and records before any build

- [x] 1.1 Write the ADR that a claim is one intervention or regimen for one indication and records its drafting source; record the superseded 2026-11-16 decision and affected wording in ADR 0013
- [x] 1.2 Record the sampled release decision and the continuing approval and export rules of ADR 0007 in ADR 0014
- [x] 1.3 Revise Claim and Source article in `GLOSSARY.md` and add the term for a claim no report is linked to; verify the terms match the specs word for word and are used exactly in the site's phrases
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

The generic-label replay compared search names for all 27,731 cached trials against commit `d9e96d98`. It changed 51 names in 3.1 seconds. It cleared 50 fragments and recovered one code written in the registered name and its aliases. The registry planner held 46 previously proposed trials whose arms included only a schedule or role for at least one component. The pilot dictionary matched 1,464 legacy names, including established treatments such as aspirin and insulin. The targeted rule leaves those names eligible. Broader word-list coverage and the independent grouping audit remain open.

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

The condition-order replay compared all 27,731 cached trials with commit `1001fb73` in 5.0 seconds. It changed the indication wording or labels for 55 trials and held 34 previously proposed trials when the arm or title described optional treatments or separate regimens by treatment line. Case P02 from the earlier audit now retains the exact phrase “Platinum-resistant Recurrent Ovarian Cancer” with the same registered regimen. Trials with distinct registered conditions still require evidence to assign them. This replay did not rerun the independent audit and used no registry requests, model calls or production writes.

A fresh grouping audit at `d11a5b47` drew 50 groups with seed `18473` from 19,084 available groups, excluding 657 trial IDs from previous reviews, rule development and held-out sets. The sample comprised 52 distinct trials. An assistant checked the official and brief titles, registered intervention names, arm assignments and condition labels. Eligibility text and arm descriptions were absent from the sampled bulk records.

| Group judgment | Count |
| --- | ---: |
| Supported by the cached registry evidence | 16 |
| Wrong indication only | 18 |
| Wrong regimen only | 2 |
| Wrong regimen and indication | 7 |
| Further evidence needed | 7 |

The result missed the 45-of-50 threshold. Even if further review supported all seven unresolved groups, the sample would reach 23 of 50. Twelve assistant-reviewed corrections citing exact registry fields passed the existing scope receipt checks. The full-cohort read-only replay took 14.9 seconds. Two corrected scopes appeared as provisional drafts with their receipt hashes. The other ten remained held for topic placement. These corrections are excluded from this audit's score. The sample, judgments and receipts are on the NVMe under `fresh-drafting-gate-audit`. Registry requests, paid model calls and production writes were zero.

On 2026-11-18 the operator chose Cancer as primary for a MeSH descriptor that supports both Cancer and an anatomical topic. The live site lookup matched the November 18 export's timestamp and all 1,126 claim slugs. That release linked 831 of 27,731 eligible trials. The before-and-after dry runs used that same export and registry cohort. Unlinked trials with a provisional draft increased from 4,569 to 8,621. Topic holds decreased from 14,052 to 9,028 groups. Six of the twelve reviewed scopes reached the preview, up from two. The preview took 16.2 seconds with the rule and 15.1 seconds without it. The evidence and live coverage check are on the NVMe under `topic-placement-audit`. Registry requests, paid model calls and production writes were zero.

Two exact-ID registry requests in 1.1 seconds returned matching versions for all 52 trials in the latest audit. Eligibility text was present for all 52 and arm descriptions for 42. An assistant used the detailed protocols to recheck the 23 groups that previously passed or needed evidence. Twelve of the 16 previous passes had a material scope error in the detailed criteria. One of seven unresolved groups passed and six had a confirmed error. Carrying forward the 27 earlier confirmed errors gives five supported groups out of 50 on this diagnostic set. Five detailed scope receipts passed version and quote checks. One dose-only example went from six proposed groups to one in the reviewed replay. The records and receipts are on the NVMe under `detailed-drafting-gate-audit`. The independent grouping gate still requires a fresh sample. The diagnostic made no extractor calls or production writes.

Fable 5.2 reviewed the experiment through the existing subscription. It advised recording arm roles and regimen relationships, then using eligibility excerpts to check the indication's population, severity, biomarkers and prior therapy. It recommended a fresh trial sample across all three unlinked categories to measure both correct output and holds, in addition to the required grouping audit. For the paid comparison, it recommended one structured pass per arm and a focused second call for a field that still has an unclear or conflicting answer.

The arm-evidence packet now labels study-wide inclusion criteria, exclusions, unassigned eligibility text and the study population. The cached replay combined the 127 development protocols and 52 diagnostic audit protocols. It found explicit inclusion text for 175 of 179 and preserved all 23 previously verified inclusion citations. The new grounding check refused 181 exact exclusion excerpts proposed as population evidence that the earlier check accepted. The median packet grew from 5,421 to 5,486 characters. The replay took 0.08 seconds with no registry requests, model calls or production writes.

The `registry-scope-evidence` command fetched the same 52 frozen audit protocols from ClinicalTrials.gov in two pages in 0.677 seconds. A second pass on the NVMe reused all 52 in 0.030 seconds and made no registry calls. The existing arm-specific packet reader accepted the resulting cache. A pipeline test verified that a run retains the first 50 when the next request is refused, resumes with only the last two and reports a changed trial version. The receipt is on the NVMe under `scope-evidence-command-replay`. Model calls and production writes were zero.

The NVMe development set holds 120 cases from 127 trials, with earlier audit and holdout trial IDs excluded. The detailed registry pull found eligibility text for all 127 trials and arm descriptions for 109. An assistant reviewed 18 cases and found evidence absent from the bulk snapshot in 12. The arm-specific command reads the frozen protocol version, validates quoted fields against the assigned arms, and can request a second pass for omitted scope. In the offline comparison, the median packet grew from 1,363 to 5,775 characters and the 95th percentile grew from 3,278 to 14,923. Simulated native JSON calls exercised both stages and the exact-request cache. Live model accuracy and spend are pending.

The regimen-label replay used the same 27,731 cached trials. The planner excluded separate explicit placebo and sham entries, kept control-only arms out of the tested arms, and held ambiguous mixed labels and alternatives. It restored proposals for 98 previously held trials, revised 14 trials' proposals, and held 269 trials that previously had proposals. There were 19,815 groups and 11,192 held trials. The plan ran in 2.22 seconds with no registry requests, model calls or production writes. An assistant checked 12 newly proposed trials. The registry supported the treatment arms in all 12, and each proposal still needed an enrollment, regimen or setting correction. On the previous 50-group audit the change only affected two groups already requiring review. A fresh audit must still pass the gate.

All 127 cached development protocols matched the identifier, update date and shared scope fields in the stored snapshot. Four assistant-reviewed receipts produced six scoped groups on the full cached replay and resolved the scope of two previously held trials. The same four records were used in a read-only drafting preview with 971 cached public claims. It took 7.90 seconds, listed one provisional draft with a receipt hash and held five groups for topic review. A separate fixture applied a reviewed draft in the test database and refused a changed arm, eligibility quote or review receipt. Model requests, registry requests and production writes were zero. The development cases remain outside the independent audit.

The topic replay used 27,731 cached trials and the same NLM vocabulary. The exact condition and population rule increased uniquely placed groups from 5,583 to 5,588, with identical regimen and indication groups. Of the six reviewed development groups, two now have a single topic from the existing mapping, one has conflicting evidence and three have no evidence. The read-only drafting command selected two provisional drafts in 7.94 seconds. The new assignment places sarcopenia in Brain and nerves under the existing map. Across the cohort, 7,857 of 8,399 conflicting groups had one descriptor mapped to several topics. The subset spanning Cancer and at least one other topic covered 4,295 distinct trials without another uniquely placed group or a cached production link. These figures describe topic placement. The grouping audit remains open.

## 3. Drafting and preparation

- [x] 3.1 Let a claim record what it was drafted from, and let a claim drafted from registry records have no source article, headline, summary or first reported date, in a new migration; verify tests that a claim entered by an operator with no article is still refused and that the record does not change when an article is added
- [x] 3.2 Add `thenwhat draft-from-registry` for a named set, with `--limit`; verify tests that a group an existing claim holds drafts nothing and hands its trials on as candidates, that a second run drafts nothing, and one success and one refusal of the command
- [x] 3.3 Have `thenwhat prepare --pending` take a registry draft: its drafting trials as candidates scored for its indication, approval only when one of them is approved, otherwise pending and listed; verify tests of both outcomes and that no trial is approved for having led to the draft
- [x] 3.4 Hold a registry draft that preparation approves awaiting audit; verify a test that no export publishes it before release and that the export says how many it left out
- [x] 3.5 Verify with a test that a read's same-claim decision attaches an article to a published registry-drafted claim, sets its first reported date, and does not hold it
- [ ] 3.6 Draft and prepare 200 claims of the first set, then audit every one; record here the drafts, the share approved, the share left pending and why, the duplicates found, the registry requests and the decision step's cost, and show the operator

Synthetic preparation exercised both match outcomes on the Mac. It fetched the drafting trial by identifier when name search missed it and sent it through ordinary indication scoring. A different approved trial alone left the claim pending. An approved drafting match held the claim, and export counted and excluded it. A later first article joined a published registry claim without adding a new audit hold.

A local fixture verified exact-ID handoff to an existing claim without a second draft. Candidates go through normal trial scoring. PostgreSQL and the D1 store preserve queued IDs across retries. The batch command applies a reviewed plan digest and records its outcome under one batch name. A verified handoff cites the exact trial and claim snapshots. Tests applied a synthetic draft and a handoff to an existing reported claim, refused changed evidence, and replayed the batch without writing again.

The existing-only replay compared 27,731 eligible trials with the 1,126 claims in the last verified public export. The current pair lookup found 11 unlinked candidates. A shared preferred MeSH concept added three. Detailed protocol review supported three of the 11 original pairs and none of the three added pairs. All three supported trials were already pending in the match queue at scores of 0.05, 0.49 and 0.70. Across the export, 372 unlinked eligible trials had pending matches and none had an approved match. The preview now shows the existing scores and review states, and a fixture verified that an existing-only batch queues a verified new candidate without drafting a claim or changing an existing score.

A scratch database rehearsal took the exact migraine study, NCT06323928, through the ordinary match review, registry evidence fetch and site export. The assistant review retained the original 0.70 score. The registry fetch produced three events and added the trial to the existing claim's export. A local browser found the claim through search and opened it with the trial link visible. Candidate retrieval took 13.76 seconds and the reviewed trial event fetch took 0.21 seconds. The protocol cache used one exact-ID page for the 14 reviews. The receipts are on the NVMe under `existing-claim-reuse`. Model calls and production writes were zero.

The full command preview ran read-only against 27,731 cached trials and 971 claims from the November 17 export on the NVMe. It took 13.5 seconds and listed 200 provisional drafts covering 165 distinct trial IDs. It found 62 groups with existing-claim candidates and held 14,520 groups for topic review. This preview used no new registry or model requests. The grouping threshold still applies before actual drafting.

The duplicate and alias replay used the same cached trials and claims. It kept all 19,815 groups visible, including two pairs with identical regimen display names and distinct component lists. Two groups were held for duplicate regimen and indication. The other pair was already held for topic review. The preview reported 67 possible alias pairs and held the 14 groups whose records named each other. Some one-way links came from comparator or combination entries. The preview took 14.1 seconds, listed 200 provisional drafts covering 166 trials, and made no registry requests, model calls or production writes. It does not satisfy the independent grouping audit.

## 4. The site

- [x] 4.1 Add to the export whether a report is linked and what a claim was drafted from, with no headline or summary for a claim with no article; regenerate `site/export.schema.json` and raise the schema version; verify the tests that compare both pass
- [x] 4.2 Word a claim with no report from fixed phrases in the site's own files, and extend the build's wording check to these phrases and to words of advice; verify tests that the build fails on a verdict word and on a word that offers the treatment to a reader
- [x] 4.3 Show the fixed line on a claim with no report and none of date first reported, promises or reported statements; verify tests of a claim with no report, the same claim after an article is linked, and the extension's view
- [x] 4.4 Let every list of claims be narrowed to reported claims, kept in the address and working with the status and topic narrowing; verify tests on the Claims list, a topic page and the home page's lists
- [x] 4.5 State how many claims a report is linked to wherever the site counts claims, and keep claims with no report out of rows whose subject is a report; verify tests of the home page's count and of the day-by-day list
- [ ] 4.6 Build a preview from an export holding the 200 claims of 3.6 and show the operator the home page, one topic page and three claim pages; record here whether lists open on every claim or on reported claims
- [ ] 4.7 Build the site from an export holding the whole first set as drafted in the plan, and record here the build time, the output's size and the size of `lookup.json`; report the figures to `cloudflare-source-of-truth` and stop if the build does not fit
- [ ] 4.8 Deploy a pull request preview and read twenty pages of claims with no report with the operator; record here anything reworded

Storage and export were exercised with a synthetic registry-only claim on the Mac. PostgreSQL and the SQLite store produced the same claim. The audit hold excluded it from export, and linking a first article later preserved its drafting origin. The PostgreSQL migration preserved a legacy row and refused to downgrade with a registry claim present. The version 3 export built a claim page and a search entry. Fixtures and the run receipt are stored on the NVMe.

The synthetic site build renders the site's fixed registry wording, the absence of a source report, and the first report after it is linked. The lookup and extension checks omit the first reported date and promises while a report is absent. The same import-time wording check rejects verdicts and offers of treatment.

The reported-only choice persisted in the address and combined with status and topic in browser tests. The home count states how many claims have a linked report, and registry-only events stay in registry rows. A local preview opened on all 201 claims, with 200 synthetic registry-only claims and one reported claim. After narrowing, home and topic each showed one claim. A registry-only claim opened from a search result. The preview with 200 audited real claims is pending.

The capacity rehearsal built 200 synthetic additions in 47.2 seconds with 1,970 files and a 122,106-byte lookup. The 600-claim warm-cache build yielded 5,578 files and a 364,106-byte lookup. A 20,224-claim synthetic stress export plus the seed exceeded the budget before rendering, at a floor of 161,800 files. The finding is recorded in `cloudflare-source-of-truth`. The full real-cohort build remains pending.

The split-release rehearsal built 20,224 synthetic additions plus the seed on the Mac using 64 repeated card designs. Astro took 120.56 seconds, Pagefind indexed 20,225 pages in 28.23 seconds, and NVMe staging took 34.41 seconds. Of 182,295 generated files, 394 remained in the Worker bundle, under its 18,000-file budget. The lookup was 12,141,512 bytes. The concentrated topic page and the home claims list exceeded 20 MiB and were served from the local object store at their original addresses. Both responses matched the staged checksums. A separate 201-claim browser run found and opened an object-backed registry claim through Pagefind. Wrangler validated the split configuration in dry-run mode. These runs made no production writes. The 200-claim review and full build from audited real claims remain pending.

## 5. The sampled audit

- [x] 5.1 Add `thenwhat audit sample` for a held batch: a drawn sample of the set size, recorded with its seed, the whole batch when smaller; verify tests of both and that a second call returns the same sample
- [x] 5.2 Record each sampled claim's judgement with who made it, an assistant's as an assistant's; verify tests of both and that a wrong claim is not released
- [x] 5.3 Release a batch on a partial sample with `thenwhat audit clear --batch` only when the sample is fully judged and the wrong share is at or below the configured figure. Preserve release after a whole audit. Verify tests at the figure, over it, unfinished, and with no figure.
- [x] 5.4 Offer the operator a drawn share of an assistant's judgements and record the count that differ; verify one test of its figures
- [x] 5.5 Verify with a test that a release changes no review state and that a released claim says no person checked it unless a person approved it

Local PostgreSQL fixtures recorded a repeatable four-of-six sample and held the batch while the audit was unfinished, the allowed share was unset, or the result was above the figure. At the configured figure, five claims reached the export and the wrong claim stayed held and was archived. The existing store merge applied the same five clear actions to a SQLite copy that already held the claims. A second fixture audited an entire two-claim batch, recorded two operator disagreements separately, and applied the operator's findings. Release preserved claim, match and event approvals. The audit settings are optional with no configured values in the example. The draft command records each reviewed batch's membership. Real drafting still needs the grouping gate.

## 6. The first set

- [ ] 6.1 Draft and prepare the first set in slices of the size the operator sets, each slice planned before it runs; record here, for each slice, the drafts, the share approved, the requests and the cost
- [ ] 6.2 Audit each batch on a sample, record the sample's size, the count wrong, the defects by category and the operator's spot-check, and release or hold as the figure says
- [ ] 6.3 After the first set is published, count again the trials of the set a claim cites and record the figure here beside the 1.7% of `proposal.md`
- [ ] 6.4 Show the operator the figures of 6.1 to 6.3 before any second set is named

## 7. Records

- [x] 7.1 Update `CLAUDE.md`, `PRODUCT.md` and `docs/backfill-loop.md` for what a claim is, the drafting command, the order after it (`thenwhat prepare --pending`, sample, release, export), and that the daily run starts none of it; verify `make scripts-test` fails if it would
- [x] 7.2 Note in `trial-first-route` and `headline-funnel` what this change supersedes and what it gives their routes; verify both `design.md` files name this change
- [x] 7.3 Regenerate `site/data/seed-export.json` if the seed's export changes, run `make check` and `openspec validate registry-drafted-claims --strict`; verify all pass

The daily-run tests passed. Injecting a registry drafting command into a disposable copy made `make scripts-test` fail with the forbidden-command assertion. The check ran against the fake pipeline only.

The version 3 seed matched its generated export in `make check`. The full pipeline, store, site and extension checks passed, including the browser checks and the strict validation of this change.
