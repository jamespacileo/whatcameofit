# Proposal

## Why

On 2026-11-16 the operator asked how the tracker could become a product that pharmaceutical companies pay for, given what they already buy (pipeline databases, safety intelligence, media monitoring). The assistant's answer, recorded here at the operator's request, is that the tracker holds one thing those products do not: a link from what the public was told about an intervention to what the registries show, per claim, with the events that produced each status. The established products start from a trial or a drug that already has a sponsor. The tracker starts from the report, so it also holds the claims that never reached a registry.

This change is a recommendation, not a decision. Nothing in it is agreed by the operator yet, and no build task may start before the validation in `tasks.md` group 1 is done and the operator has answered the open questions in `design.md`.

## What Changes

The recommendation is one offer made of three parts, in this order of importance:

- **Early-stage list.** Published claims whose status is "preclinical only" or "no trial record found", each with the years since its first report, the organisations it names and their roles, its approach and its health area. For a team that looks for early research to license or partner on, this is the part no pipeline database covers: reported work with no trial on record.
- **Translation counts.** For claims first reported in a given year, how many stand at each status today, with the number of claims counted. Offered as proof of method and as context for the list, never as a forecast.
- **Access for software.** The same records through a keyed interface with a feed of status changes, so a customer's own tools can read them without scraping the site.

What is sold is service, not secrecy. The data file is already offered under CC BY 4.0 and stays so. A customer pays for coverage of a health area built on request, for the change feed, for watch lists and for support. Every claim the paid work produces is published on the public site like any other, under the same rules.

Considered and not recommended first (reasons in `design.md`): a media-against-evidence monitor for medical affairs, aggregate reader demand, answer support for medical information teams, a results-disclosure tracker, and offers to research funders, university press offices and investors.

Not in this change: any pricing, any contract or billing system, any customer account pages, any change to how a claim is approved, published or archived, and any use of what readers look up.

## Capabilities

### New Capabilities

- `professional-data`: what the tracker offers to paying organisations, how it stays identical in substance to the public site, what the early-stage list and the translation counts hold, and how they are worded.

### Modified Capabilities

None. `open-data`, `status-derivation` and `organisations` are read by this capability and not changed.

## Impact

- **Nothing is built by accepting this proposal.** Group 1 of `tasks.md` is conversations and reading; it touches no code.
- **Pipeline** (`pipeline/src/thenwhat/export/`), only after the gate: two derived views computed from the export by pure functions, and the export's schema and seed regenerated.
- **Site** (`site/`), only after the gate: the two views as public pages and data files, worded by the site, and a keyed route on the site's service.
- **Docs**: `docs/sources.md` gains a dated note per source on whether its terms allow paid reuse; `GLOSSARY.md` gains "early-stage list" and "translation count"; a new decision record if the operator accepts money from the industry the site reports on.
- **Guardrails this must be checked against:** accuracy shown and not gated (ADR 0001), no editorial verdicts, no medical advice, article text never stored, and subscriber emails as the only personal data. A customer contact is new personal data and needs the operator's decision before any is taken.
- **Operator decisions needed** before any build: whether to take industry money at all and how to disclose it; whether funded coverage is acceptable; what personal data a customer relationship may hold; which health area to cover first.
