# Design

The visual system of the thenwhat site as built. Product context is in `PRODUCT.md`; behavior is in `openspec/`.

**Direction: evidence digest.** Chosen by the operator on 2026-11-11 from three sketches (`.impeccable/mocks/decision/directions.html`), replacing an earlier yellow "timetable" look that did not suit the subject. The brief: calm, familiar to readers of research-summary sites, relevant to the topic, and as simple as the first version.

## Principles

1. **Answer first.** The top of a claim page is a soft panel that says where the claim stands and when the latest record is dated, beside two sentences of summary.
2. **Promise beside record.** What was promised for a year sits beside what was recorded in it. The reader compares; the site does not conclude.
3. **Words carry status.** Status is always written out. Colour, shape and position only support the words.
4. **Quiet surface.** One typeface, one accent colour, one highlight colour. No gradients or photographs. One soft shadow, on popovers only. One motion, on the site name only.
5. **Say it once.** A colour or drawing is named once in a key, then used without its words. A record appears once, with its source on the same line; detail opens on demand.

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
- An empty Promised cell is plain amber, with "Nothing promised for this year." for screen readers. A claim with no dated promise has no Promised column, and says "No dated promise on record." above the table.
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

- **Masthead.** White, a hairline beneath. Site name in blue, three plain links; the current one is underlined. With one listed topic its name is the middle link; with several the link reads "Topics" and leads to the list on the home page. A topic is listed only once it has a published claim.
- **Topic chip.** A pill with a small line drawing for the topic (a tooth for dental regeneration; a plain ring for a topic without a drawing) and the topic's name. It links to the topic page, from the claim page and from the home page's topic list.
- **Site name.** The name, then a solid blue dot. On load, and again on hover, three small grey dots count the wait after a headline and close up into the blue dot, the same marker the stage track uses for where a claim stands. No motion when the reader asks for reduced motion.
- **Share.** On a claim page, a quiet pill opposite the topic chip. It opens the device's share sheet, or copies the page address and says "Link copied". Hidden when neither is possible, and on paper.
- **Digest panel.** The status label with an info button, the stage track, the no-signal note in a dashed outline when present, and "Latest record <date>", beside the summary. The info button opens a panel with what the status means, the records it rests on (each linking to its line in the timetable) and the date the status was set. The no-signal note opens a panel saying what it does and does not mean. The date a status was computed is never presented as the date something happened.
- **Stage track.** Six places on a line, from preclinical to approved, with one larger solid blue dot at the status's place. It marks a position, not progress, and is never filled up to the dot. It always sits beside the status in words. Failed, terminated and retracted have no track. The operator approved it on 2026-11-11 as the one exception to "no meters".
- **Facts row.** Intervention with its other names, what it is claimed for, first reported, evidence then.
- **Key.** Beside the timetable heading: the amber swatch for "Promised", one drawing for each kind of record on the page, and the blue diamond for "Basis of status".
- **Timetable.** A framed table: year, Promised (pale amber, only when a dated promise exists), Recorded. Years with nothing collapse into one quiet row. Each record is one line: the drawing for its kind, the day, what happened, and a link to its source. What happened is a dotted-underlined button that opens a panel with the record's summary and where its date came from. A record the status rests on carries the blue diamond. A news report shows its title in quotation marks and its outlet. On a phone the rows stack, and amber is seen only where a promise exists.
- **Popover.** The browser's own popover, placed beside its trigger. Opens on tap, key press, or hover with a mouse; Escape or a tap outside closes it. White, hairline border, one soft shadow. On paper every panel is printed in place.
- **Outlet.** Wherever a web article is named: the outlet's own icon, its name and its short domain. The icon is 17 pixels square with the tile's 4-pixel corners, and is shown in its own colours on no ground. It was fetched by the pipeline and is served as a file of this site, because a page asks the network for nothing. An outlet with no stored icon gets a drawn letter tile of the same size.
- **Icons.** Lucide, stroke 1.7 to 1.9, in secondary-text grey. A drawing never stands alone: the key or the words beside it say what it is.
- **Promised with no date.** A pale amber list with dashed rules.
- **Index tables.** Claim, first reported, latest promise (pale amber, the year in bold; the column is left out when no claim in the list has a dated promise), status with a small stage track beside the label.
- **Stage filter.** Above a topic's table once it lists six or more claims: the path drawn large, with the number of claims at each place and the place's name. Each place is a button that narrows the table to it; pressing it again shows all. A place with no claim is not a button. Statuses off the path sit beneath as outlined buttons. It is also the legend for the small tracks in the table. Without JavaScript it still shows the counts.
- **Topic directory.** `/topics`: a "Find a topic" field that narrows the list as the reader types, a row of letters that jump to their section, and under each letter the topics in up to three columns, each with its number of claims. Built for hundreds of topics. When the export gives any topic a group, the headings are the groups from A to Z instead of letters: the group's name in ink in a column of its own beside its topics (above them on a phone), the jump row names the groups as small pills, typing a group's name keeps all its topics, and topics without a group come last under "Other topics". The site never invents a group. The menu's "Topics" link leads here; the home page shows the twelve topics with the most claims and a link to the rest.
- **Headlines table.** On the home page: the ten newest news reports. The outlet's title sits in quotation marks and opens the claim page; the outlet's name beneath it, in regular weight, opens the report; then the date reported and the status now. The quotation marks and the outlet name are what mark the wording as someone else's, so neither may be dropped.
- **Search.** One labelled field and a button. Shows "Searching…", then results, a plain "Nothing found" sentence, or a plain failure sentence.
- **Footer.** Deep navy. The two notices in bold, then data sources and the dates the registries were checked and the pages built.
- **Link-preview card.** White, site name in blue, headline, then a rounded panel with first reported, promised by (a year, never a day count) and status. Its text alternative is built from the same facts.
- **Extension popup.** 360px wide, same tokens and face. The site name in blue over a hairline; the claim headline; the status in the digest panel's treatment ("Where it stands", blue label, no-signal note in a dashed outline, one sentence of meaning); first reported; the latest promise on pale amber; one full-width blue button, "See the evidence". The two notices and the last-checked date sit under a hairline in muted small text. Messages (not tracked, not a web page, unreachable) are a heading, one or two sentences and at most one outlined button. Light only.
- **Favicon.** A navy rounded square with a white "t". Never a solid block of the accent blue with white lettering, which is the shape of an official health mark.

## Rules for every future page

- Footer notices on every page: no medical advice; a registered trial is not a treatment option; data sources; last-checked date. A build check fails without them.
- No verdict wording in any status label; a build check fails on words such as "abandoned".
- Status never by colour alone.
- Source articles are linked by outlet, title and date. Their text is never shown.
- No stock photography. Topic imagery is a drawn mark in the accent colour.
- Focus is a 3px blue outline (white on the footer). Selection is the tag blue, inverted on the footer. Hover thickens a link's underline, darkens the chip and the button.
- A date never breaks across two lines.
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
