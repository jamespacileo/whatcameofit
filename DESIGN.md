# Design

The visual system of the thenwhat site as built. Product context is in `PRODUCT.md`; behavior is in `openspec/`.

**Direction: evidence digest.** Chosen by the operator on 2026-11-11 from three sketches (`.impeccable/mocks/decision/directions.html`), replacing an earlier yellow "timetable" look that did not suit the subject. The brief: calm, familiar to readers of research-summary sites, relevant to the topic, and as simple as the first version.

## Principles

1. **Answer first.** The top of a claim page is a soft panel that says where the claim stands and when the latest record is dated, beside two sentences of summary.
2. **Promise beside record.** What was promised for a year sits beside what was recorded in it. The reader compares; the site does not conclude.
3. **Words carry status.** Status is always written out. Colour, shape and position only support the words.
4. **Quiet surface.** One typeface, one accent colour, one highlight colour. No gradients or photographs. One soft shadow, on popovers only. Motion is listed under Motion and nothing else moves.
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
| Page title over 70 characters | `clamp(1.35rem, 3.4vw, 1.7rem)`, measure 44 characters | 700 |
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
- **Wordmark.** The name in sentence case and ink, with a light lead and a heavy tail, closed by a question mark: "What came **of it**?". The question mark is drawn, not typed, so that its dot can be the solid blue marker that also shows where a claim stands. On a first visit the hook is drawn and the dot lands; a hover plays it again. The operator added the question mark to the name on 2026-11-11, replacing the three waiting dots tried first (`.impeccable/mocks/brand/directions.html`).
- **Share.** On a claim page, a quiet pill opposite the topic chip. It opens the device's share sheet, or copies the page address and says "Link copied". Hidden when neither is possible, and on paper.
- **Digest panel.** The status label with an info button, the stage track, the no-signal note in a dashed outline when present, and "Latest record <date>", where the date leads to that record in the timetable, beside the summary. The info button opens a panel with what the status means, the records it rests on (each linking to its line in the timetable) and the date the status was set. The no-signal note opens a panel saying what it does and does not mean. The date a status was computed is never presented as the date something happened.
- **Stage track.** Six places on a line, from preclinical to approved, with one larger solid blue dot at the status's place. It marks a position, not progress, and is never filled up to the dot. It always sits beside the status in words. Failed, terminated and retracted have no track. The operator approved it on 2026-11-11 as the one exception to "no meters".
- **Facts row.** Intervention with its other names, what it is claimed for, first reported, evidence then.
- **Key.** Beside the timetable heading: the amber swatch for "Promised", one drawing for each kind of record on the page, and the blue diamond for "Basis of status".
- **Timetable.** A framed table: year, Promised (pale amber, only when a dated promise exists), Recorded. Years with nothing collapse into one quiet row. Each record is one line: the drawing for its kind, the day, what happened, and a link to its source. Records in one year that share a source (a trial's registry entry) are one line with a dated step for each, so the source is named once. What happened is a dotted-underlined button that opens a panel with the record's summary and where its date came from. A record the status rests on carries the blue diamond. A news report shows its title in quotation marks and its outlet. On a phone the rows stack, and amber is seen only where a promise exists.
- **Popover.** The browser's own popover, placed beside its trigger. Opens on tap, key press, or hover with a mouse; Escape or a tap outside closes it. White, hairline border, one soft shadow. On paper every panel is printed in place.
- **Outlet.** Wherever a web article is named: the outlet's own icon, its name and its short domain. The icon is 17 pixels square with the tile's 4-pixel corners, and is shown in its own colours on no ground. It was fetched by the pipeline and is served as a file of this site, because a page asks the network for nothing. An outlet with no stored icon gets a drawn letter tile of the same size.
- **Icons.** Lucide, stroke 1.7 to 1.9, in secondary-text grey. A drawing never stands alone: the key or the words beside it say what it is.
- **Promised with no date.** A pale amber list with dashed rules.
- **Index tables.** Claim, first reported, latest promise (pale amber, the year in bold; the column is left out when no claim in the list has a dated promise), status with a small stage track beside the label.
- **Stage filter.** Above a topic's table once it lists six or more claims: the path drawn large, with the number of claims at each place and the place's name. Each place is a button that narrows the table to it; pressing it again shows all. A place with no claim is not a button. Statuses off the path sit beneath as outlined buttons. It is also the legend for the small tracks in the table. Without JavaScript it still shows the counts.
- **Topic directory.** `/topics`: a "Find a topic" field that narrows the list as the reader types, a row of letters that jump to their section, and under each letter the topics in up to three columns, each with its number of claims. Built for hundreds of topics. When the export gives any topic a group, the headings are the groups from A to Z instead of letters: the group's name in ink in a column of its own beside its topics (above them on a phone), the jump row names the groups as small pills, typing a group's name keeps all its topics, and topics without a group come last under "Other topics". The site never invents a group. The menu's "Topics" link leads here; the home page shows the twelve topics with the most claims and a link to the rest.
- **Headlines table.** On the home page: the ten newest news reports. The outlet's title sits in quotation marks and opens the claim page; the outlet's name beneath it, in regular weight, opens the report; then the date reported and the status now. The quotation marks and the outlet name are what mark the wording as someone else's, so neither may be dropped.
- **Main box.** On the home page the field is the largest control: it takes a pasted article link or search words, and answers a pasted link at once. A tracked article is answered with a small digest panel: the status in blue, its place on the path, the no-signal note, the claim's headline, what the status means and a link to the records. An untracked one shows close claims as a plain list, said to be a guess, so a guess never looks like an answer.
- **Search.** One labelled field and a button. Shows "Searching…", then results, a plain "Nothing found" sentence, or a plain failure sentence.
- **Footer.** Deep navy. The two notices in bold, then data sources and the dates the registries were checked and the pages built.
- **Link-preview card.** White. Top: the icon and wordmark, with "Not medical advice" opposite. Middle: the earliest article's title as the outlet wrote it, in quotation marks, with the outlet's name beneath; a claim with no article shows its own headline unquoted. Bottom, in the pale blue panel: "Status now" and the status in blue, the no-signal note when present, then the year first reported, the year promised by when there is one, and the month the registries were checked. The site puts no word of its own between the quotation and the status. The year promised by is the only thing on pale amber, with a dashed rule, as in the timetable. Dates, never a count of days or years, so a saved card stays true. A title is cut at a word with an ellipsis past 150 to 200 characters, by shape. Built in three shapes from one description: wide 1200 by 630 (the link preview), square 1080 by 1080 and tall 1080 by 1920; in the square and tall shapes the dates sit under the status. The padding is counted inside the image, so nothing is cut off. Its text alternative is built from the same facts.
- **Pass it on.** The last section of a claim page: one line saying what it is for ("Seen this headline shared again? Reply with the record."); the square card itself, small, beside one dated sentence in a pale blue panel, ready to copy; pills to copy it and to download the square and tall cards; and, folded away, the snippet that shows the status on another site. Copy buttons appear only where copying works and say "Copied"; otherwise the text is left selected. Hidden on paper.
- **Embed.** `/embed/<slug>`, made for a frame of 440 by 420 that narrows with its host; the headline is held to three lines: a hairline box holding the site's name with "Not medical advice" opposite, the claim's headline, the status with its track in a pale blue band, the checked month and a link to the records, then the two notices and the data sources in small type. Every link opens in the whole window. It loads nothing from elsewhere and stores nothing.
- **Method page.** `/how-it-works`: prose in the reading measure, the rules as a numbered list, and each status in a framed list with its place on the path, its label and its meaning, read from the same source as the claim pages.
- **Anniversaries.** `/anniversaries`: months as section headings, then each day with its claims: the year first reported in grey, the headline, the status with its track. Opened on a day that has entries, that day is tinted and marked "today". A feed at `/anniversaries.xml` carries the last thirty days.
- **Year and data pages.** `/year/<yyyy>` is a topic-style page: the count, then the claim table with its stage filter. `/data` links the downloadable file and states its licence.
- **Extension popup.** 360px wide, same tokens and face. The site name in blue over a hairline; the claim headline; the status in the digest panel's treatment ("Where it stands", blue label, no-signal note in a dashed outline, one sentence of meaning); first reported; the latest promise on pale amber; one full-width blue button, "See the evidence". The two notices and the last-checked date sit under a hairline in muted small text. Messages (not tracked, not a web page, unreachable) are a heading, one or two sentences and at most one outlined button. Light only.
- **Automatic lookup cards.** Opening the popup on an untracked page starts one lookup. The loading state and automatic answer identify OpenAI processing and link to Privacy. Each potential record is a separate, white, hairline-bordered card with 12px corners and 14px padding. Its title links to the registry, followed by the match-confidence label, phase, state and registry identifier. Reasons for the match sit within the same card under a fine rule. Confidence is a numeric, model-estimated match to the report, presented in words and figures without a meter or a colour grade. The automatic, unchecked notice remains above the results. Reviewed-claim links use the same grouping with reviewed provenance and no invented score.
- **Icon.** A pale blue rounded square holding a magnifying glass over two lines of print, a dark headline and a grey line that ends in the blue dot: a news claim, looked at closely. It has to say that with no words beside it. Chosen by the operator on 2026-11-11 from `.impeccable/mocks/brand/pictorial.html` (mark 1), replacing the headline-and-reply icon tried first. Used as the favicon, the browser extension's icon and the stamp on the link-preview card. No tick, cross or grade is ever drawn into it. Never a solid block of the accent blue with white lettering, which is the shape of an official health mark.

## Motion

Two authored moments tell the site's story; the rest is feedback. Nothing loops, nothing moves on scroll, and no content waits for an animation to become readable.

| What | Motion | Time |
|---|---|---|
| Wordmark | The question mark's hook is drawn, then its blue dot lands. First page of a visit only; a hover plays it again. | 1.5 s, once |
| Stage marker on a claim page | The blue dot lands on the claim's place and one ring leaves it. It lands in place and never travels along the path, because a claim can reach a place without passing the others. | 0.6 s, once |
| Popover | Fades in and rises 4 px beside its trigger; leaves faster. | 170 ms in, 90 ms out |
| Record reached by a link | The page scrolls to it, it shows in the tag blue, then settles to the tint. A link inside a popover closes the popover first. | 2.2 s |
| Between pages, and when a table is filtered | A cross-fade; the masthead holds still. | 170 ms |
| Lookup answer for a tracked article | The marker lands on the place, as on a claim page. | 0.6 s, once |
| Copied | The button's icon gives way to the blue dot, which lands; the label says "Copied" and a screen reader is told. | 0.4 s, then 2 s held |
| Chips, buttons, filter places | Colour changes ease; a pressed button drops 1 px. | 120 ms |

Easing is `cubic-bezier(0.16, 1, 0.3, 1)` for arrivals. With reduced motion asked for: no dots, no landing, no scrolling, no cross-fade, no movement; popovers still fade and a reached record is tinted without the change. Popover fades apply only where the browser has popovers, so elsewhere a panel is plain visible content. On paper nothing is hidden by a motion style.

## Dry wording

The voice is plain, exact and unexcited, and that is the only joke the site makes: its own way of reporting, turned on itself. It is allowed on the site's own furniture and nowhere else.

- Not-found page: "No page record found", the path with no place marked, and "Last checked: just now."
- A search with no result: "No record found for … We say that a lot."
- Footer: "We will check again." This is a promise; it stays only while the registries are in fact re-checked.
- Page source: one comment for a reader who checks it.

Never on a claim page, a card, an embed or the extension, never about a condition, a treatment, an outlet or the people behind a claim, and never a pun on a topic's name.

## Resilience

- Nothing widens the page: long names, identifiers and addresses break. Checked at 320 pixels on every page type.
- A hyphenated name stays unbroken only up to 16 characters.
- A popover taller than the screen scrolls inside itself.
- An empty place on the path is outlined in `--ring` (`#7f90a3`, 3:1 on white).
- With a forced palette (Windows high contrast) the marker, the basis mark and the name's dot take the system text colour, and promise areas, the digest and popovers gain an outline.
- `color-scheme: light` keeps form controls and scrollbars light.
- An article with no outlet name is named by its domain.
- Without JavaScript: the home page says search needs it and points to the topic list; popovers still open on tap; the share button stays hidden.
- A slow answer to an earlier search never replaces the answer to a later one.
- The stage marker starts small, never absent, so it is on the page from the first frame.

Weight, measured on the preview build: a claim page with 29 records is 5 KB of HTML, 6 KB of CSS and under 4 KB of script compressed, plus one 20 KB font file.

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
