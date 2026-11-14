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

The unit is the claim, not the article, and the status is derived by fixed rules from public registry records matched by the pipeline, each match shown with how confident the pipeline is. Publishing is automatic (decided 2026-11-13, ADR 0001); the operator takes wrong items down. No model and no editor decides the status, and every status lists the events that produced it.

## Operating Context

- Readers follow source links out to trial registries, journals and regulators; those links are the product's proof.
- A page is often shared as a link preview, so each claim has a status card image.
- Data comes from ClinicalTrials.gov, Europe PMC and Crossref. Their terms require attribution and a visible date for when the data was processed.

## Capabilities and Constraints

- Pages: one per claim at `/{slug}`, an index per topic, a list of claims that reached approval, and a home page with search, the most recent news reports and recent status changes. Also: a page that explains the method, a page per year of first report, a calendar of first-report anniversaries, the published claims as a downloadable file, and an embed of each claim's status for other sites.
- Statuses: preclinical only, no trial record found, trial registered, Phase 1, Phase 2, Phase 3, approved, failed, terminated, retracted. A "no signal for N years" note can accompany the first six.
- Never: medical advice, treatment recommendations, editorial verdicts. "No signal" is never worded as dead or abandoned. A registered trial is never presented as a treatment option.
- Never: article text. News articles are linked by outlet, title and date only.
- Every page carries a footer: not medical advice; a registered trial is not a treatment option; data sources; last-checked date.
- Browser extension (Chrome and Safari): one click on an article shows the tracked claim's status. A tracked article is matched inside the browser and its address is sent nowhere. On an untracked page, once the reader has allowed it, an automatic registry search sends the page's words (or a reduced image of what is visible) to the site's service and OpenAI; `/privacy` is the full account. It keeps the reader's recent checks, followed claims and reminders in the browser, and notifies when a followed claim moves. As of 2026-11-14: Safari 0.9.0 is waiting for App Store review; no store lists it yet.
- Extension page (`/extension`): the popup's three answers drawn from the export, what the extension reads, sends and keeps, its permissions, and the install controls. Built only once a store address is configured (`CHROME_STORE_URL`, `SAFARI_STORE_URL`); until then nothing links to it.
- Guide (`/guide`, `/guide/<slug>`): 27 entries on three shelves: the ten statuses, eight of the site's own words, and nine on how research is recorded. Each gives a one-sentence answer, what the word rests on in the records, what it does not tell the reader, the site's rule for it with up to three tracked claims where it applies, and its sources with the day each was read. Entries are Markdown files in `site/src/guide`; a build fails on a status with no entry, a research entry with no source, a missing related entry, or verdict or advice wording. An entry says it has not been checked by a person until the operator sets it checked. Readers cannot edit it.
- About page (`/about`): one published claim drawn at page scale (the outlet's title, the years since, the status now), the one cited finding on how rarely follow-ups are reported, what the site does and does not do, where to check it, who runs it, and the lookup box as its last section. The sentence on funding is the operator's to set and is not drawn until it is.
- Audience pages (`/for/journalists`, `/for/clinicians`, `/for/researchers`): each opens on a working tool. Journalists: a search whose result is the claim's embed at 440 by 420 with the code to copy. Clinicians: the lookup, whose tracked answer carries the dated sentence to copy and the card. Researchers: the data file with its licence, build day and fields.
- Topic pages for communities: under the title, one line saying what the page is; under the summary, Share, "Copy sentence" (the summary, the checked month, the address) and the topic's feed, all before the first claim. Each topic has its own link-preview card at `/og/topic/<slug>.png`.
- Paste a link: the home page's main box takes an article's address and shows the tracked claim's status, or the closest tracked claims when the article itself is not tracked. The address is compared in the browser and sent nowhere. It reads links in the shapes they are shared in (social redirects, AMP, archives, mobile hosts). It cannot open a shortened link or a social media post, and says so.
- Not yet: email follow, public deployment. A feed of first-report anniversaries exists; a feed of status changes does not.
- Topics: dental regeneration was the first. On 2026-11-11 the operator asked for wide coverage of recent, popular, miraculous-sounding cure stories, clickbait titles included, so thirteen more topics are configured. A topic is listed on the site once it has a published claim.
- Headlines: an outlet's title is shown as a quotation with the outlet named, beside the status the evidence supports. The site never repeats a headline's wording as its own.

## Brand Commitments

- Name: “What came of it?” at whatcameofit.com. `thenwhat` remains the repository codename. Brand strings live in one config file.
- Voice: plain, exact, unexcited. States what a record shows and when.
- Look: the operator chose a calm "evidence digest" direction on 2026-11-11: familiar to readers of research-summary sites, relevant to the topic, simple. The accent is a dark navy blue on a light page (the operator moved it from a brighter clinical blue on 2026-11-12), asked for to read as health and trust. It must never borrow those sites' grades or scores, and never look like an NHS or other official service. See `DESIGN.md`.
- Icon: the flat blue magnifying glass over a coral-and-blue capsule on white, selected by the operator on 2026-11-13. See `DESIGN.md`.

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
