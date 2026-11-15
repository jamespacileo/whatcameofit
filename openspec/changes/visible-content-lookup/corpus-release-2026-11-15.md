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
installed Safari or full-video checks. Installed Safari verification and the
final corpus/Sheet read-back are still in progress.

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
