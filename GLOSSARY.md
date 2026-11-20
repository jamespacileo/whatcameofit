# Glossary

Domain terms for thenwhat. Behavior is specified in `openspec/`; this file only fixes the words. Claims, and the words that belonged only to them, were removed on 2026-11-20.

| Term | Meaning |
|---|---|
| **Pair** | One coded treatment for one coded condition, followed through the public trial registries. The unit the site tracks. Each pair has one page, at its address. Made by the data lab, never by the site. |
| **Treatment** | What a pair is about: a drug, device, method or complete regimen, coded as one substance or kind. The bundle calls it the intervention. A salt form counts as its base substance. |
| **Condition** | What a pair's treatment is for, coded as one MeSH descriptor. |
| **Address** | A pair's place on the site, `/<treatment>--<condition>`, fixed by the lab. |
| **Bundle** | The folder of page files the lab hands the site: one JSON file a page under `p12_<page>/`, one JSON Schema a page model under `schemas/`, and a manifest whose checksum names its version. The site's only input. A file that does not fit its schema, or a code the site has no words for, stops the build. |
| **Built ahead** | A pair whose page, cards and embed the build makes as files. Every other pair's page is made by the Worker when it is asked for, from the same page file. |
| **Status** | Where a pair stands, derived by fixed rules from its trials' registry records: preclinical only, no trial record found, trial registered, Phase 1 to 3, approved, failed, terminated or retracted. Every status lists the records that produced it. No model decides it. |
| **Standing trial** | A trial that is neither terminated nor withdrawn and carries no failure flag. Status comes from the furthest standing trial that has started. |
| **Gloss** | A status in plain words, for a reader who does not know trial phases: one fixed phrase per status, worded by the site. It claims no more than the status rule knows and is never a status itself. |
| **Overlay** | Extra text on a status, not a status itself. The no-signal overlay says how many years have passed without a new record. |
| **Trial event** | A dated change in a trial's registry record, such as its registration, start or completion, or results being posted. Shown on the trial's entry; the events that set a status are listed under "Why this status". |
| **Trial facts** | What a trial's registry record states of the trial itself: its state, phase, people taking part, dates, arms, why it stopped and posted results. Read by fixed rules from the stored record, shown with the date it was read, and never an input to status. |
| **Under way** | A trial the registry lists as started and not yet finished. Never "recruiting": the site does not say a trial is open to participants. |
| **Results paper** | A paper that a trial's registry record names: listed by the sponsor as reporting the study's results, or linked by the registry from PubMed. Attached by rule, with no search, score or model. |
| **Sponsor** | The organisation a trial's registry record names as its lead sponsor. A sponsor that is a person is not recorded and not shown. |
| **Approach** | The kind of treatment, such as drug, gene therapy or transplant. At most one per pair, and never part of status. |
| **Topic** | The reader-friendly area a pair is filed under, for example mouth and teeth. The bundle calls it the vertical; a topic belongs to one group. |
| **Clinical category** | A MeSH descriptor a pair is filed under in MeSH's tree of diseases, shown under NLM's own name. Never part of status. |
| **Confidence** | A match's score shown as a word and a percentage, such as "High match · 92%", with its reasons. An automatic estimate that a record concerns the treatment and condition, never a verdict on the treatment. |
| **Live lookup** | A registry search the lookup service makes for a reader's article when no page follows it. Shown only to that reader, with scores, marked automatic and unreviewed, and never worded as a status. |
| **Page reader** | The service that fetches a news page for the lookup service: the operator's self-hosted Firecrawl. It holds the rules about each site and answers with what happened. No page is fetched another way. |
| **Checked by a person** | Whether a person has read a pair against its sources. A pair put together by software carries a notice under its status until then. |
| **Archived** | Taken off the public site by the operator. The address answers 410 Gone. |
| **Retired address** | An address the site served while it tracked claims (before 2026-11-20), frozen in `site/data/retired-addresses.json`. It answers a 301 to the one published pair that lists it, or 410 Gone. |
| **Operator** | The person who runs the site and the lab, corrects decisions and archives wrong items. |
