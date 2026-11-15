# Corpus release verification, 2026-11-15

PR #124 was merged as `55540f1b3cef3792515fb9c0393c5c13a73f3be9`.
Production CI run `43714437328` passed all checks, deployed Worker
`12acaad3-45f2-4f36-9819-86c7d1683898`, and passed its live smoke check at
12:36:33 UTC. Safari 0.9.4 (13) was built with stable Xcode, signed with the
existing development identity, and installed with unchanged bundle IDs,
entitlements and permissions. The previous 0.9.3 (12) installation is retained
in the application's rollback directory.

The first released-address run attempted every one of the 37 selected URLs.
The three business/legal negatives now correctly return no specific treatment.
Thirty browser-only URLs return the expected post-platform refusal by address.
The browser checks execute the released collector against fresh live Chrome DOM
and send its composed requests to production; they are not represented as
installed Safari or full-video checks. All 37 browser checks completed; seven
rows also have installed Safari popup evidence. Exact per-row release and method
are recorded in `extension/test-corpus/runs/2026-11-15-release.json`.

## Company-history follow-up

The released browser run found a remaining false positive in S026: the Persian
Vertex company profile selected telaprevir/hepatitis C from its historical
product description. The earlier local run had correctly returned no treatment,
so that result was not sufficient proof of consistent released behavior.

The reading instructions now explicitly classify the whole post before selecting
a medicine. Founding dates, offices, product indications, mechanisms and historical
approvals remain company catalogue facts, not the profile's own research claim.
This implements the existing reported-treatment requirement; it does not exclude
research reports merely because a company appears in them.

Real-provider verification with the same freshly read S026 caption returned no
treatment three times. Synthetic positive controls for an actual suzetrigine
phase-3 report and an explicit PP405 hair-growth result both remained positive.
No copied caption or model gist is included in this evidence. The 78 affected
service/post/visual tests, lint and type checks passed. Version-4 shared and local
answer caches invalidate results made before this follow-up; Safari is bumped
to 0.9.5 for the corresponding local-cache correction.

The same released run also rejected S045 as a roundup because the BELIEVE post
compared monotherapy and combination arms. The instructions now distinguish arms
of one trial from unrelated studies. Two live follow-ups identify bimagrumab (alone
or with semaglutide) for obesity and return the BELIEVE candidate; the NEJM roundup
S021 stays negative in two follow-ups. A final S026 repeat remains negative with
both refinements present. The complete 163 extension tests and 24 service speed
checks pass, including rejection of version-3 saved answers.

## Released follow-up and remaining accuracy work

PR #131 merged as `907848f16759e8d752f5729193cdcb6db2386ddd`.
CI `43717386624` passed 1,437 pipeline, 607 site and 163 extension checks,
deployed Worker `a2438aac-a516-4b10-a263-7e502a79a9bb` at
2026-11-15T13:11:23.963Z and passed its live smoke check. Signed universal
Safari 0.9.5 (14) is installed at `~/Applications/WhatCameOfIt.app`, with the
previous build retained for rollback and unchanged permissions/entitlements.

The 37 released reruns currently have 15 pass, 2 partial, 18 review and 2 fail
verdicts. S036 and S045 find the relevant obesity trial but can also offer the
biological-ageing GLP-1 card: intervention-name overlap is not claim identity.
S026's caption-only company profile is correctly negative, but inspection of its
carousel changes the whole-post expectation: slide two explicitly names
suzetrigine/Journavx for pain. The collector still selects the metadata image on
slide one when it is outside an ancestor's clipped viewport; the final installed
Safari result identifies only an unnamed painkiller. It remains partial.

The corpus and native Sheet now audit card identity separately. Read-back found
zero value differences across the 37 edited rows, no changes to the existing
cell metadata or Summary formulas, exact Findings/Key values, and preserved
frozen rows/columns. Nine durable-cache tests pass. Full-sheet baseline:
258 URLs, 174 pass, 3 partial, 2 fail, 13 blocked, 28 review, 38 not run;
older verdicts do not imply a completed card audit. Three repeated production
negative address checks reused shared results in 104, 69 and 21 ms.

The continuing all-URL accuracy/efficiency goal is owned by
`openspec/changes/corpus-match-accuracy/`. Additional native Safari checks and
Sheet visual review await an unlocked Mac; Chrome DOM checks remain available.
No caption-only or single-frame check is described as a full-video check.
