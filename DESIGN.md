# Design

The visual system of the thenwhat site as built. Product context is in `PRODUCT.md`; behavior is in `openspec/`.

**Direction: evidence digest.** Chosen by the operator on 2026-11-11 from three sketches (`.impeccable/mocks/decision/directions.html`), replacing an earlier yellow "timetable" look that did not suit the subject. The brief: calm, familiar to readers of research-summary sites, relevant to the topic, and as simple as the first version.

## Principles

1. **Answer first.** The top of a claim page is a soft panel that says where the claim stands and when the latest record is dated, beside two sentences of summary.
2. **Promise beside record.** What was promised for a year sits beside what was recorded in it. The reader compares; the site does not conclude.
3. **Words carry status.** Status is always written out. Colour, shape and position only support the words.
4. **Quiet surface.** One typeface, one accent colour, one highlight colour. No gradients, shadows, photographs or motion.

## Colour

| Token | Value | Used for |
|---|---|---|
| `--paper` | `#ffffff` | Page ground |
| `--ink` | `#231f33` | Text |
| `--indigo` | `#3d2f7a` | The accent: site name, links, status label, years, focus ring, buttons |
| `--muted` | `#5d5677` | Secondary text, labels |
| `--panel` | `#f6f4fb` | The digest panel |
| `--tint` | `#f1eefa` | Topic chip |
| `--tag` | `#e6e0f7` | "basis of status" tag, text selection |
| `--rule`, `--rule-soft` | `#e6e2f0`, `#eeebf6` | Borders and row rules |
| `--promise` | `#fff7df` | Everything promised: the Promised column, undated promises, the "latest promise" cell in index tables |
| `--promise-rule` | `#d9c88a` | Dashed rules between promises |
| `--footer` | `#2a2150` | Footer ground, button hover |

Rules:

- Pale amber means "promised" and nothing else. A promise is always on it, with dashed rules, wherever it appears.
- An empty Promised cell says "Nothing promised for this year." in words.
- There is no colour for any status. No red, no green.
- Light only. No dark theme.

## Type

One family, Figtree Variable, self-hosted and preloaded, with `"Helvetica Neue", Arial, sans-serif` behind it.

| Role | Size | Weight |
|---|---|---|
| Page title | `clamp(1.9rem, 5.2vw, 2.5rem)` | 700 |
| Status label in the digest | `clamp(1.45rem, 3.6vw, 1.75rem)` | 700, indigo |
| Section heading | `1.2rem` | 700 |
| Body | `1rem` (root is 106.25%), line-height 1.55 | 400 |
| Notes, labels, facts | `0.75rem` to `0.9rem` | 400 to 700 |

Figures are tabular and lining throughout. Reading measure is 66 characters. A name with a hyphen in a headline never breaks at the hyphen.

## Layout

- Page width 60rem, gutter `clamp(1rem, 4vw, 2rem)`.
- Corner radius `0.85rem` on panels and table frames, `0.65rem` on the search field and button, full on the topic chip.
- One breakpoint at 40rem. Below it the digest stacks, and both table types become labelled blocks: each year is a block with a pale amber "Promised for this year" box above "Recorded this year".

## Components

- **Masthead.** White, a hairline beneath. Site name in indigo, three plain links; the current one is underlined.
- **Topic chip.** A pill with a small line drawing for the topic (a tooth for dental regeneration; a plain ring for a topic without a drawing) and the topic's name. It links to the topic page.
- **Digest panel.** "Where it stands", the status label, the no-signal note in a dashed outline when present, and "Latest record <date>. Status set <date>." beside the summary. The date a status was computed is never presented as the date something happened.
- **Facts row.** Intervention with its other names, what it is claimed for, first reported, evidence then.
- **Timetable.** A framed table: year, Promised (pale amber), Recorded. Years with nothing collapse into one quiet row. Events that produced the status carry a "basis of status" tag. Each event has a footnote letter linking to its source.
- **Promised with no date.** A pale amber list with dashed rules.
- **Index tables.** Claim, first reported, latest promise (pale amber), status.
- **Search.** One labelled field and a button. Shows "Searching…", then results, a plain "Nothing found" sentence, or a plain failure sentence.
- **Footer.** Deep indigo. The two notices in bold, then data sources and the dates the registries were checked and the pages built.
- **Link-preview card.** White, site name in indigo, headline, then a rounded panel with first reported, promised by (a year, never a day count) and status. Its text alternative is built from the same facts.
- **Favicon.** An indigo rounded square with a white "t".

## Rules for every future page

- Footer notices on every page: no medical advice; a registered trial is not a treatment option; data sources; last-checked date. A build check fails without them.
- No verdict wording in any status label; a build check fails on words such as "abandoned".
- Status never by colour alone.
- Source articles are linked by outlet, title and date. Their text is never shown.
- No stock photography. Topic imagery is a drawn mark in the accent colour.
- Focus is a 3px indigo outline. Selection is the tag lavender, inverted on the footer.
- Print hides navigation and search and drops the footer's fill.

## Not yet judged

- The earlier look was reviewed by the design reviewer; this one has not been. It was checked by eye at 1280 and 375 pixels wide on the claim page and the home page.
- Hover, focus and print states were not captured.
