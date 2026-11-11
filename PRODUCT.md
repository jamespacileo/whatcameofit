# Product

<!-- impeccable:product-schema 1 -->

> Written without an interview: the operator asked for the remaining work to be finished unattended. Everything here comes from `SPEC.md` and the decisions recorded in `openspec/`. Lines marked **Assumed** were inferred and should be confirmed or corrected.

## Platform

web

## Stack

Astro static site, built from one JSON export. No server, no client framework. Search runs in the browser from a prebuilt index.

## Users

People who remember a headline ("scientists regrow teeth") and want to know what became of it: patients and relatives, curious readers, journalists checking a past story, researchers and clinicians asked about it. They arrive from a search engine or a shared link, usually on a phone, with one question: what happened to this?

**Assumed:** most visits are a single claim page reached from outside, not browsing from the home page.

## Product Purpose

News reports medical breakthroughs that are rarely followed up. thenwhat keeps a page for each claim (one intervention for one indication) showing where it stands now and the dated, sourced evidence that says so. Success is a reader leaving with a correct picture of the evidence and a link to check it.

## Positioning

The unit is the claim, not the article, and the status is derived by fixed rules from public registry records that a human has reviewed. No model and no editor decides the status, and every status lists the events that produced it.

## Operating Context

- Readers follow source links out to trial registries, journals and regulators; those links are the product's proof.
- A page is often shared as a link preview, so each claim has a status card image.
- Data comes from ClinicalTrials.gov, Europe PMC and Crossref. Their terms require attribution and a visible date for when the data was processed.

## Capabilities and Constraints

- Pages: one per claim at `/{slug}`, an index per topic, a list of claims that reached approval, and a home page with search, the most recent news reports and recent status changes.
- Statuses: preclinical only, trial registered, Phase 1, Phase 2, Phase 3, approved, failed, terminated, retracted. A "no signal for N years" note can accompany the first five.
- Never: medical advice, treatment recommendations, editorial verdicts. "No signal" is never worded as dead or abandoned. A registered trial is never presented as a treatment option.
- Never: article text. News articles are linked by outlet, title and date only.
- Every page carries a footer: not medical advice; a registered trial is not a treatment option; data sources; last-checked date.
- Browser extension (Chrome and Safari): one click on an article shows the tracked claim's status. It matches the address inside the browser and sends no page address anywhere. Built 2026-11-11; not yet tried in a real browser toolbar, not published in any store.
- Not yet: email follow, RSS, paste-a-URL lookup, public deployment.
- Topics: dental regeneration was the first. On 2026-11-11 the operator asked for wide coverage of recent, popular, miraculous-sounding cure stories, clickbait titles included, so thirteen more topics are configured. A topic is listed on the site once it has a published claim.
- Headlines: an outlet's title is shown as a quotation with the outlet named, beside the status the evidence supports. The site never repeats a headline's wording as its own.

## Brand Commitments

- Name: `thenwhat` is a working codename; the final name and domain are undecided. Brand strings live in one config file.
- Voice: plain, exact, unexcited. States what a record shows and when.
- Look: the operator chose a calm "evidence digest" direction on 2026-11-11: familiar to readers of research-summary sites, relevant to the topic, simple. The accent is a clinical blue, asked for by the operator to read as health and trust. It must never borrow those sites' grades or scores, and never look like an NHS or other official service. See `DESIGN.md`.
- No logo has been chosen.

## Evidence on Hand

- One seeded example claim, compiled from public sources (see `data/seed/`).
- Recorded registry responses used as test fixtures.
- No testimonials, press, user numbers or track record exist. None may be implied.

## Product Principles

1. Evidence before interpretation: show the dated event and its source, then the status it produces.
2. A status is a description of records, never a judgement of a treatment or of the people behind it.
3. Absence of evidence is stated as absence, with how long, and nothing more.
4. Every claim on a page must be checkable in one click.
5. Promise and outcome sit side by side, so the reader compares them without being told what to conclude.

## Accessibility & Inclusion

**Assumed:** WCAG 2.2 AA. Status is never conveyed by colour alone. Pages must read well on a phone, with a screen reader, and when printed.
