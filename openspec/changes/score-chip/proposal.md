# Proposal

## Why

A claim page showed a score in seven places with five wordings and three layouts: a grey part of a disclosure's line ("Term match: high, 98%"), a grey line under a record ("Match to this claim: high, 92%"), the opening of a possible record's line, a note in a trial entry, a grey label in the timetable ("High match · 92%"), a blue disclosure beside a reported statement, and a sentence beside a lower-band reading. A reader had to learn each one, and what a score means was said in a different place each time, or not at all.

On 2026-11-16 the operator asked for claim pages to read more like a research-summary site, with "a more minimal way of displaying confidence scores with on hover popover", saw the mock (`.impeccable/mocks/claim-examine/index.html`) and chose to build the score chip first.

## What Changes

- One component, `Score`, draws every score on a claim page and a trial page: a small outlined chip with the band in words and the percentage, in sight. It opens a panel, on hover, press or key, that says what the number is about and that it says nothing about the treatment.
- The chip's text is the phrase used before ("Match to this claim: high, 92%", "Term match: high, 98%"). Where the row already says what is matched, the opening words are kept for a screen reader and for paper and not drawn.
- In "At a glance" a row's chips stand beside its value, out of the disclosure's line. A registry record's chip stands at the end of its title's line; a possible record's chip says "Possible match" in sight. A reported statement's chip replaces its disclosure. A lower-band reading's chip is outlined in dashes and reads "Low confidence · N%", with "Not confirmed, so it does not decide the status." beside it in sight.
- No colour, fill, meter or mark says how good a score is.

This replaces `page-frame`'s requirement "A match score reads as a note about the match", which kept a score in an entry's notes and off its title's line.

Out of scope: the home page's day list, the live lookup's answers and the extension, which keep their wording; the words and bands themselves.

## Capabilities

### Modified Capabilities

- `site-publishing`: a score is drawn as one chip that opens its meaning.

## Impact

- `site/`: `Score.astro`, `Pop.astro` (a panel that may stand in a paragraph), `lib/score-id.ts`, `lib/confidence.ts`, `lib/glance.ts`, `Glance.astro`, `RegistryRecordRow.astro`, `MatchList.astro`, `Statements.astro`, `Paper.astro`, `Trial.astro`, `pages/[slug].astro`, styles, tests.
- `DESIGN.md`: the "Score chip" entry, and the entries that described a score's place.
