# 10. A record's mark is coloured by which way the record moved

Date: 2026-11-17. Status: accepted. Change: `openspec/changes/archive/2026-11-18-home-then-now`. Narrows the guardrail "No editorial verdicts".

## Context

The home page's day-by-day list gives each registry record a small mark for what the record did: a plus for a trial registered, play for started, a square for terminated, and so on (`EventMark`). As first built every mark was the one blue, so that no mark could be read as a verdict.

On 17 November 2026 the operator asked for the marks to be colour-coded, so that a reader skimming the list sees progress, a neutral update and an ending apart. The guardrail "No editorial verdicts" stood against it as written: green on a trial event is easily read as "the treatment works", and a completed trial may have found nothing, as a terminated one may have been stopped for money or for enrolment.

Four mappings were put to the operator: by direction, with a finished trial neutral; the same with a finished trial green; regulator decisions only; no colour. The operator chose the first.

## Decision

A mark's colour says which way the record moved, and nothing else.

- **Forward** (green): something began, or a regulator approved. A trial registered, a trial started, a regulatory approval.
- **Stopped** (red): something was halted, taken back or refused. A trial suspended, terminated or withdrawn, a regulatory refusal, a retraction.
- **Neither** (the site's blue): everything else. A trial completed, results posted, a follow-up paper, a grant, a company event, and any record of a kind not listed here.

A completed trial and posted results are "neither" and stay so: what a trial found is not known from the record of its ending. No colour is ever given by what a trial's results say, by a model, or by hand. The rule is one pure function (`eventDirection`), tested case by case.

Colour is never the only signal. Each mark has its own drawing, and the row says what happened in words. The mark is hidden from a screen reader, which is given the words.

The colours are for these marks only. A claim's status, its place on the path and the stage track keep the site's blue; amber stays for what was promised.

## Consequences

- The guardrail still holds for wording and for status: "No signal" is never "dead", a status is never coloured, and a registered trial is never presented as a treatment option. The guardrail's line in `CLAUDE.md` names this exception.
- A red mark on a terminated trial will be read by some as "it failed". The row's words say "terminated", the claim page gives the registry's stated reason where there is one, and the status at the row's right is the claim's, not the trial's. If readers take the red for a verdict on the treatment, the fallback is "regulator decisions only", which this decision leaves room for.
- A new kind of record is blue until this list names it.
