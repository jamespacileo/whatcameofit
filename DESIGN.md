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
| `--ink` | `#172534` | Text |
| `--blue` | `#0b5cad` | The accent: site name, links, status label, focus ring, buttons |
| `--muted` | `#4d5d6e` | Secondary text, labels |
| `--panel` | `#f3f7fb` | The digest panel |
| `--tint` | `#eaf2fa` | Topic chip |
| `--tag` | `#d9e8f7` | "basis of status" tag, text selection |
| `--rule`, `--rule-soft` | `#dde5ee`, `#e9eff5` | Borders and row rules |
| `--promise` | `#fff7df` | Everything promised: the Promised column, undated promises, the "latest promise" cell in index tables |
| `--promise-rule` | `#d9c88a` | Dashed rules between promises |
| `--footer` | `#0b2f57` | Footer ground, button hover |

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
| Status label in the digest | `clamp(1.45rem, 3.6vw, 1.75rem)` | 700, blue |
| Section heading | `1.2rem` | 700 |
| Body | `1rem` (root is 106.25%), line-height 1.55 | 400 |
| Notes, labels, facts | `0.75rem` to `0.9rem` | 400 to 700 |

Figures are tabular and lining throughout. Reading measure is 66 characters. A name with a hyphen in a headline never breaks at the hyphen.

## Layout

- Page width 60rem, gutter `clamp(1rem, 4vw, 2rem)`.
- Corner radius `0.85rem` on panels and table frames, `0.65rem` on the search field and button, full on the topic chip.
- One breakpoint at 40rem. Below it the digest stacks, and both table types become labelled blocks: each year is a block with a pale amber "Promised for this year" box above "Recorded this year".

## Components

- **Masthead.** White, a hairline beneath. Site name in blue, three plain links; the current one is underlined. With one topic its name is the middle link; with several the link reads "Topics" and leads to the list on the home page.
- **Topic chip.** A pill with a small line drawing for the topic (a tooth for dental regeneration; a plain ring for a topic without a drawing) and the topic's name. It links to the topic page, from the claim page and from the home page's topic list.
- **Digest panel.** "Where it stands", the status label, the no-signal note in a dashed outline when present, and "Latest record <date>." and "Status set <date>." on their own lines, beside the summary. The date a status was computed is never presented as the date something happened.
- **Facts row.** Intervention with its other names, what it is claimed for, first reported, evidence then.
- **Timetable.** A framed table: year, Promised (pale amber), Recorded. Years with nothing collapse into one quiet row. Events that produced the status carry a "basis of status" tag. Each event has a footnote letter linking to its source; each source names its record and date, because two records can share one registry entry. On a phone the rows stack, and a year with no promise shows one muted line with no amber, so amber is seen only where a promise exists.
- **Promised with no date.** A pale amber list with dashed rules.
- **Index tables.** Claim, first reported, latest promise (pale amber), status.
- **Search.** One labelled field and a button. Shows "Searching…", then results, a plain "Nothing found" sentence, or a plain failure sentence.
- **Footer.** Deep navy. The two notices in bold, then data sources and the dates the registries were checked and the pages built.
- **Link-preview card.** White, site name in blue, headline, then a rounded panel with first reported, promised by (a year, never a day count) and status. Its text alternative is built from the same facts.
- **Favicon.** A navy rounded square with a white "t". Never a solid block of the accent blue with white lettering, which is the shape of an official health mark.

## Rules for every future page

- Footer notices on every page: no medical advice; a registered trial is not a treatment option; data sources; last-checked date. A build check fails without them.
- No verdict wording in any status label; a build check fails on words such as "abandoned".
- Status never by colour alone.
- Source articles are linked by outlet, title and date. Their text is never shown.
- No stock photography. Topic imagery is a drawn mark in the accent colour.
- Focus is a 3px blue outline (white on the footer). Selection is the tag blue, inverted on the footer. Hover thickens a link's underline, darkens the chip and the button.
- A date never breaks across two lines.
- A footnote letter's link is at least 24 by 24 CSS pixels.
- Print hides navigation and search, drops the footer's fill and the table frame, never splits a record across sheets, and prints each source address after its link.

## Why blue

The operator asked on 2026-11-11 for blue in place of the first indigo, to read as health, trust and clinical care, giving NHS blue as the example. The accent is a blue of that family, not the NHS palette: this site is not an NHS service and must never look like one. No NHS logo, lozenge, name or typeface, and no wording that suggests an affiliation.

Contrast, measured: text on white 15.6:1, blue on white 6.7:1, blue on the panel 6.2:1, blue on the tag 5.4:1, secondary text on white 6.8:1 and on amber 6.3:1, white on the footer 13.5:1.

## Review

The design reviewer judged this look on 2026-11-11 from captures of the claim, home, topic, approved and not-found pages at 1280 and 375 pixels wide, hover and focus states, and the printed claim page. It accepted the topic page, hover and focus, and asked for the fixes that are now in: the phone timetable's amber, the navigation's topic link, source names, date breaks, the footnote target size, two wording changes and the print layout.

Not yet judged:

- The reviewer judged the blue version in a second pass, found the eight fixes in place, and asked for three more that are now in: the icon is navy, years and footnote letters are in ink so blue text that is not the status label is always a link, and this note. Those three were checked by eye, not by a third review.
- The accent sits close to NHS Blue in hue. The distance comes from how it is used: text and small marks on white, no blue header band, no solid blue block with white lettering. Keep it that way.
- Lists and tables have only been seen with one claim.
