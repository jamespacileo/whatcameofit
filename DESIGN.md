---
name: thenwhat
description: A printed public timetable for reported medical breakthroughs; promised on yellow beside recorded on white, year by year.
colors:
  yellow: "#ffd21e"
  blue: "#1b47b0"
  ink: "#14161a"
  paper: "#ffffff"
  muted: "color-mix(in oklch, #14161a 66%, #ffffff)"
  hairline: "color-mix(in oklch, #14161a 24%, #ffffff)"
  wash: "color-mix(in oklch, #14161a 5%, #ffffff)"
typography:
  display:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(2.1rem, 6vw, 3.6rem)"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.015em"
    fontVariation: "'wdth' 72"
  headline:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.7rem, 4.6vw, 2.5rem)"
    fontWeight: 800
    lineHeight: 1
    fontVariation: "'wdth' 72"
  title:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.6rem"
    fontWeight: 800
    lineHeight: 1.1
    fontVariation: "'wdth' 72"
  bar:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "0.05em"
    fontVariation: "'wdth' 72"
  lede:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "'tnum', 'lnum'"
  note:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    lineHeight: 1.55
rounded:
  none: "0px"
spacing:
  gutter: "clamp(1rem, 4vw, 2.5rem)"
  page: "70rem"
  measure: "65ch"
components:
  masthead:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    padding: "0.7rem {spacing.gutter}"
  section-bar:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.bar}"
    padding: "0.55rem 0.8rem"
  timetable-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "0.75rem 0.8rem"
  timetable-cell-promised:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    padding: "0.75rem 0.8rem"
    width: "34%"
  timetable-year:
    textColor: "{colors.ink}"
    typography: "{typography.title}"
    width: "5.5rem"
  index-cell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "0.7rem 0.8rem"
  index-cell-promise:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    padding: "0.7rem 0.8rem"
  status-label:
    textColor: "{colors.ink}"
    typography: "{typography.headline}"
  overlay-tag:
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.2rem 0.6rem"
  basis-tag:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    padding: "0.05rem 0.4rem"
  search-input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "0.75rem 0.9rem"
  search-button:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "0.75rem 1.25rem"
  search-button-hover:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.paper}"
  colophon:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    padding: "2.25rem {spacing.gutter} 2.75rem"
  status-card:
    backgroundColor: "{colors.yellow}"
    textColor: "{colors.ink}"
    size: "1200px 630px"
---

# Design System: thenwhat

> Provisional. This direction (printed public timetable) was assigned by a concept roll and built unattended. It awaits the operator's approval; nothing here is a confirmed brand decision. Recorded from the shipped site under `site/`, with `site/src/styles/global.css` as the source of every token.

## Overview

**Creative North Star: "The Printed Timetable"**

A claim is treated as a service that was announced, and its page is the timetable. What was promised sits on yellow beside what the records show on white, year by year, and the reader compares them unaided. The page is white paper, black ink, one yellow that fills whole fields, and one blue for links. Nothing is decorative: every fill and rule says what kind of thing sits inside it.

The site is a reading surface for people arriving on a phone from a search or a shared link. It is dense where a timetable is dense (tables, dates, footnote letters) and plain everywhere else. There is no motion, no shadow, no rounded corner, no image, and no icon in the built pages.

**Key Characteristics:**
- Yellow means "promised" or "the sheet's header"; white means "recorded".
- One typeface; a condensed cut for heads, tabular lining figures everywhere.
- Rule weight and line form carry structure and state: 3px ink, 1px ink, 1px hairline, dashed.
- Status is always words, set large in ink. No status has a colour.
- Square corners, flat surfaces, light only.

## Colors

Four chosen colours and three neutrals mixed from ink and paper in OKLCH.

### Primary
- **Departure-sheet Yellow** (`yellow`): a field colour. It fills the masthead band, the Promised column of the timetable (header cell included), the Latest promise column of index tables, the upper field of the link-preview card, and the text selection. Its one use as a line is the focus ring inside the black footer. It is never a text colour.

### Secondary
- **Signal Blue** (`blue`): links on paper, the default focus ring, the search caret, and the search button on hover. Nothing else.

### Neutral
- **Ink** (`ink`): all text, all structural rules, section bars, the footer, the basis tag, the search button.
- **Paper** (`paper`): the page, recorded cells, the search field, text on ink.
- **Muted** (`muted`): secondary notes under an entry, quiet timetable rows, the "status last changed" line, placeholder text. Only on paper.
- **Hairline** (`hairline`): rules between entries inside a recorded cell, and around rows of plain lists and footnotes.
- **Wash** (`wash`): the scrollbar track only.

The footer's inner divider is a one-off mix (paper 40% into ink) and is not a token.

### Named Rules
**The Whole Field Rule.** Yellow fills a whole band, column or card field with ink text on it. It is not used for text, tags, underlines or small accents.

**The Ink On Yellow Rule.** Anything on yellow is ink, including links and notes (blue and muted are for paper only). On the masthead the focus ring is ink; on the footer it is yellow; elsewhere it is blue.

**The No Status Colour Rule.** No status, event type or outcome has a colour of its own. A status is its wording.

## Typography

**Display Font:** Archivo Variable at 72% width (with Helvetica Neue, Arial, sans-serif)
**Body Font:** Archivo Variable at normal width (same fallbacks)

**Character:** one grotesque doing both jobs, as on a printed timetable: a tight condensed bold for heads and years, the regular width for reading. Root size is 106.25% (17px), so every rem below is slightly larger than default.

### Hierarchy
- **Display** (800, clamp(2.1rem, 6vw, 3.6rem), 1.05, -0.015em, condensed): the page title, one per page, capped at 22ch and balanced.
- **Headline** (800, clamp(1.7rem, 4.6vw, 2.5rem), 1, condensed): the status label on a claim page.
- **Title** (800, 1.6rem, 1.1, condensed, no wrap): the year in the timetable. The site name in the masthead is the same cut at 1.7rem with -0.01em tracking.
- **Bar** (700, 1.05rem, 0.05em, uppercase, condensed): section headings, always inside a black bar. Table column heads use the same size and cut without the uppercase.
- **Lede** (400, 1.15rem, 1.55): the summary paragraph under the title or status.
- **Body** (400, 1rem, 1.55): running text, capped at the 65ch measure. Entry dates, entry kinds, definition terms and claim links in index tables are 700.
- **Note** (400, 0.9rem, muted on paper, ink on yellow): the line under an entry; footer text is 0.95rem.
- **Label** (700, 0.8rem): the basis tag; the "this year" line under the current year is the same size at 600 and normal width.

### Named Rules
**The One Family Rule.** No second typeface. Contrast comes from width (72% against 100%) and weight (400, 600, 700, 800).

**The Tabular Figures Rule.** Tabular lining numerals are set on the root and apply to every date, year and trial number.

## Layout

- **Page:** a single column, maximum 70rem, centred, with a fluid gutter (clamp(1rem, 4vw, 2.5rem)). The body is a flex column so the footer sits at the bottom of short pages.
- **Measure:** paragraphs, the facts list, plain lists and footnotes stop at 65ch. Tables and section bars run the full column width. The search form stops at 44rem.
- **Order on every page:** title at the left margin, then the lede, then sections opened by black bars. On a claim page the status block sits between the title and the lede.
- **Vertical rhythm:** main has clamp(1.75rem, 5vw, 3.5rem) above and clamp(3rem, 8vw, 5rem) below; a section bar has clamp(2.5rem, 7vw, 4rem) above it and 1.1rem below, except that a table sits flush against its bar.
- **One breakpoint, 40rem.** Below it both table types stop being tables: the header row is hidden from sight only (still available to assistive technology), each row becomes a block with a 3px ink rule above it, and each cell prints its column name as a label from its `data-column` attribute. Above it nothing reflows except by wrapping.
- **Alignment:** everything left-aligned and top-aligned. Nothing is centred.

## Elevation & Depth

Flat. There are no shadows, gradients, blurs or overlapping layers. Separation is by fill (yellow, ink, paper) and by ruled lines. The only stacking is the skip link, which appears at the top-left on focus.

### Named Rules
**The Ruled Paper Rule.** Depth is never used to group or lift. Use a rule or a field.

## Shapes

Square corners everywhere (0 radius, set explicitly on the search field and button). Form is made of horizontal rules in four grades:

- **3px ink:** structural edges. Under the masthead, above and below the status block, the bottom of every table, the top of each row once tables collapse, the search field and button borders.
- **1px ink:** between rows of a table.
- **1px hairline:** between entries inside a recorded cell; around rows of plain lists and footnotes.
- **Dashed ink:** between entries inside a promised cell (1px), and around the overlay tag (2px).

### Named Rules
**The Solid And Dashed Rule.** Solid lines belong to what is recorded; dashed lines belong to what was promised or to a noted absence of records. Line form carries this alongside the yellow field, so it survives without colour.

## Components

### Frame
- **Masthead:** a yellow band with a 3px ink rule beneath. Site name at the left in condensed 800, linking home; three plain ink links at the right (600 weight, no underline). Hover and the current page get a 3px underline offset 0.3em. Items wrap onto further lines on narrow screens; there is no menu button.
- **Section bar:** every section opens with an h2 set as a full-width black bar, paper text, uppercase.
- **Footer:** a black block on every page, paper text and paper links. First the two notices at 600 weight (no medical advice; a registered trial is not a treatment option), then, under a thin divider, the data sources as links and the dates the registries were last checked and the pages were built.
- **Skip link:** ink block with paper text, off-screen until focused.

### Timetable (signature)
A three-column table: Year, Promised for this year, Recorded this year.
- **Year column:** 5.5rem wide, condensed 800 at 1.6rem; the current year carries a small "this year" line beneath.
- **Promised column:** 34% wide, yellow from header to last row, empty cells included, so it reads as one unbroken strip. Entries are the promise in 700 with a note naming the outlet (linked, in ink) and the date it was said. Entries are divided by dashed ink.
- **Recorded column:** white. Each entry is day and month in 700, the kind of record in 700, a superscript footnote letter, and a muted note beneath. Entries are divided by a hairline. An empty year says so in a muted note.
- **Basis tag:** a small ink block with paper text reading "basis of status", placed after the footnote letter of each record that the status rests on.
- **Quiet rows:** a year or run of years with nothing promised and nothing recorded is one short row in muted text, year at 1rem and 600, with reduced padding. Gaps are shown, not skipped.
- **Below 40rem:** each year becomes a block under a 3px rule; the year sits on its own line; each cell is labelled with its column name in condensed 700; empty promised cells are removed; the promised cell keeps its yellow fill at full width; quiet rows become a single baseline-aligned line under a 1px rule.

### Index tables
Used for topic pages, the approved list, and recent status changes on the home page. Same construction as the timetable: 1px ink row rules, 3px ink bottom rule, condensed column heads. The claim name is a 700 link. The Latest promise column is yellow from the header down. Status is its wording in bold, with any overlay as a muted note beneath. Dates do not wrap. Below 40rem each claim becomes a block under a 3px rule, cells after the first are prefixed with "Column name: " in 700, and the promise cell keeps its yellow fill.

### Status line and overlay tag
On a claim page the status sits between two 3px ink rules. The label is condensed 800 at headline size. If the claim has a "no signal for N years" overlay it sits beside the label as a 700 line of text inside a 2px dashed ink border. The one-sentence meaning of the status and a muted "status last changed" line each take a full row beneath.

### Facts list
A two-column definition list (term in 700 sized to its content, value beside it) at the 65ch measure, under the lede.

### Plain lists and footnotes
- **Plain list:** unbulleted rows with hairlines above and below, at the measure. Used for search results, topics, undated promises, the records a status rests on, and the links on the not-found page.
- **Footnote marks:** sources are lettered a, b, c. In the table the letter is a superscript 700 link to the source row; in the Sources section each row is a 2rem letter column in 700 followed by the linked source name and trial number, with a note on where the date came from.

### Search
A labelled field joined to its button with no gap: the field has a 3px ink border on three sides and paper fill; the button is ink with paper text at 700. Button hover turns fill and border blue. Results appear below as a plain list; the results region is hidden while empty.

### Links
Blue, underlined at 1px with a 0.18em offset; 2px on hover. Ink on yellow, paper on the footer. No visited colour is set.

### Focus, selection, scrollbar
- **Focus:** 3px solid outline, 2px offset. Blue by default, ink on the masthead, yellow on the footer.
- **Selection:** yellow field, ink text.
- **Scrollbar:** ink thumb on a wash track.

### Link-preview card
A 1200 by 630 image per claim, drawn at build time. Upper field yellow: site name (30px, 800) and the claim headline (70px, or 56px when longer than 70 characters, 800). Lower field paper under a 6px ink rule: up to three facts side by side, each a 24px label over a 40px 800 value: first reported (year), promised by (year), status now (the status wording). Dates are years, never day counts, so the card does not go stale.

### Print
Navigation, search and the skip link are removed. Section bars and the footer drop their black fill and become ink text under a 3px ink top rule; footer links become ink. Nothing else changes.

## Do's and Don'ts

These hold for every future page.

### Do:
- **Do** state every status in words, using the wording in `site/src/lib/status.ts`. Colour, position or shape alone must never tell the reader a status.
- **Do** build every page on the shared layout so it carries the yellow masthead and the black footer with both notices, the data sources and the last-checked date.
- **Do** put promised material on yellow and recorded material on white, side by side, and let the reader compare.
- **Do** pair any dashed or solid distinction with its fill and its words, so it holds in greyscale and in print.
- **Do** open each section with a black bar and keep running text within 65ch.
- **Do** give every table cell a `data-column` label so it survives the collapse below 40rem.
- **Do** link every record to its source with a footnote letter.
- **Do** keep text on yellow in ink.

### Don't:
- **Don't** use verdict wording. The build fails on dead, abandoned, scam, hoax, debunked, bogus, fake, quack or fraud in status text; "no signal" is never worded as an ending.
- **Don't** add verdict badges, meters, scores, ticks, crosses, or red and green for outcomes.
- **Don't** add a progress stepper for trial phases.
- **Don't** add a dark theme. The system is light only; no dark values exist.
- **Don't** add a second typeface, a third colour, shadows, rounded corners or motion.
- **Don't** use yellow for text or as a small accent, or blue for anything that is not a link, focus or the search hover.
- **Don't** drop or shorten the footer notices on any page, including error pages.
- **Don't** hide empty years. A gap in the record is shown as a quiet row.
