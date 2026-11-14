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
| `--ink` | `#0f1f38` | Text |
| `--blue` | `#14427f` | The accent: site name, links, status label, focus ring, buttons |
| `--muted` | `#46566b` | Secondary text, labels |
| `--panel` | `#f1f5fb` | The digest panel |
| `--tint` | `#e6eef8` | Topic chip |
| `--tag` | `#d6e2f2` | "basis of status" tag, text selection |
| `--rule`, `--rule-soft` | `#d9e2ee`, `#e9eff5` | Borders and row rules |
| `--promise` | `#fff7df` | Everything promised: the Promised column, undated promises, the "latest promise" cell in index tables |
| `--promise-rule` | `#d9c88a` | Dashed rules between promises |
| `--footer` | `#0b2545` | Masthead and footer ground, button hover |
| `--on-navy` | `#8ec1f5` | On the masthead only: the dot of the name's question mark and the underline of the current link |

Rules:

- Pale amber means "promised" and nothing else. A promise is always on it, with dashed rules, wherever it appears.
- Amber is kept for a promise that exists. An empty Promised cell is white, with "Nothing promised for this year." for screen readers; the column heading stays amber. Where a past year has a promise and no record, "No record" is in ink at body size, not in grey: the same words, easier to find. A claim with no dated promise has no Promised column, and says "No dated promise on record." above the table.
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

- **Masthead.** The footer's deep navy with white lettering and no hairline, so the page opens and closes on the same colour. The operator asked for it on 2026-11-13, to feel familiar to readers of clinical and health sites. The reverse mark (the operator asked for it on 2026-11-13: no white tile, the glass in white with the navy showing through the lens, the capsule in its own coral and blue), then the site name, then three plain links, the first of which is "Look up" (the home page's button says the same); the current one is underlined in the lifted blue. On paper it has no fill, the name is in ink and the mark is printed in one dark colour. With a forced palette the mark keeps a small navy tile of its own. With one listed topic its name is the middle link; with several the link reads "Topics" and leads to the list on the home page. A topic is listed only once it has a published claim.
- **Topic chip.** A pill with a small line drawing for the topic and the topic's name. A topic takes its group's drawing, so dementia is drawn as brain and nerves; one with no drawing gets a plain ring. The operator asked on 2026-11-13 for a drawing per group. Twelve are from Lucide: hourglass (ageing), bone, brain, ribbon (cancer), drop (diabetes, weight and hormones), eye, heart with a pulse, shield with a plus (immune system and allergies), microscope (infections), bean (kidneys and bladder), wind (lungs and breathing), baby (pregnancy and fertility). Four are drawn for the site on the same grid, where Lucide has nothing that fits: the tooth, a stomach (gut and liver), a head in profile (mental health) and a face under a fringe (skin and hair). A drawing says what part of the body or kind of illness a topic is about, never how a claim in it stands. It links to the topic page, from the claim page and from the home page's topic list.
- **Wordmark.** The name in sentence case, white on the masthead and ink elsewhere, with a light lead and a heavy tail, closed by a question mark: "What came **of it**?". The question mark is drawn, not typed, so that its dot can be the solid blue marker that also shows where a claim stands; on the masthead the dot is the lifted blue. On a first visit the hook is drawn and the dot lands; a hover plays it again. The operator added the question mark to the name on 2026-11-11, replacing the three waiting dots tried first (`.impeccable/mocks/brand/directions.html`).
- **Follow.** On a claim page, a pill beside Share: a bookmark and "Follow"; once pressed it stays tinted, the bookmark is filled and it reads "Following". It lists the claim on the home page, in this browser only. Shown only where the browser lets the page keep a list.
- **Following (home page).** Above the counts, only for a reader who follows a claim: each claim's headline as the link, then its status in ink, or the tag "Changed" with "Was: X. Now: Y." when the status differs from the one last seen; a changed claim comes first. Each row ends with the text control "Stop following", and the list with "Kept in this browser only." The site's version of the extension's list, in the same words.
- **Since line.** Above the tabs, one line in ink: "Since your last visit on 7 Nov 2026: 12 news reports, 1 status change." Each count is a text control that opens its list. A first visit reads "In the last 30 days". Rows dated since the last visit carry the tag "New" after the headline or the name. Counts only.
- **Tag.** "New" and "Changed": 0.72rem bold ink on the tag blue, 0.3rem corners. Always beside words that say what is new or what changed; never alone, never a colour for a status.
- **Text control.** A button that reads as a link: blue, underlined, semibold, no fill. Used for the counts in the since line and for "Stop following".
- **Share.** On a claim page, and under a topic's table, a quiet pill opposite the topic chip. It opens the device's share sheet, or copies the page address and says "Link copied". Hidden when neither is possible, and on paper.
- **What this is.** Under a claim's headline, one grey line for a reader who arrived from a shared link: "A record of what followed this news report." (or "these news reports"; "this reported breakthrough" when the claim has no article) and the link to the method page.
- **Reports followed.** Straight under that line, before the status: the claim's news reports, newest first and at most three, as a plain list with hairlines. Each is the outlet's title in quotation marks at 1.05rem semibold, linked to the article with the leaving arrow, and under it the outlet and the date in grey. More than three end with a link to the timetable. The sentence above is the list's only visible label; its heading is for screen readers. A reader who pressed a headline on the home page finds that headline here, so the page is seen to be about it.
- **Other claims.** Before "Pass it on": up to three other claims in the same topic, newest report first, in the index table, and a link to the topic when there are more.
- **Another headline?** The last section of a claim page: one sentence and a pill, "Look up another", that leads to the home page's box with the field ready. A page ends on a next step.
- **Check again later.** Linked from the digest panel, under the dates, once it can be offered. After "Pass it on" on a claim page: a row of the same pills, each saving a calendar file for one date (the promised date when it is still to come, six months, a year, the next anniversary of the first report). The file is made in the browser and nothing is sent. The section is hidden until the script has run, a choice that cannot be offered is removed, and saving is confirmed the way a copy is. Plain wording only: this sits on a claim page.
- **The reader's lists (extension).** Under any answer the popup offers two text controls, "Recently checked" and "Following"; they are a side door and never compete with the status. Each list is a view of its own with "Back", built from the same record cards as a registry search. A followed claim that has moved carries a filled "Changed" tag and the sentence "Was: X. Now: Y.", so the change is never told by the tag alone. Both lists end with "Kept in this browser only." Text controls are blue, underlined and 13px; they are not buttons and take no fill.
- **Unchecked notice.** On a claim page no person has checked: a dashed outline under the digest panel, never above it, so the status is the first thing read.
- **Digest panel.** The status label with an info button, the stage track, the no-signal note in a dashed outline when present, "Promised by <year>" on pale amber with a dashed rule when the claim has a dated promise (the year leads to its row in the timetable), "Latest record <date>", where the date leads to that record in the timetable, and, where the export carries matches, how many registry records were matched and how many are possible, leading to their list, beside what the status means, in one semibold sentence, and the summary under it. The status is explained in the open, so no reader has to find the info button to learn what "Preclinical only" says. The info button opens a panel with the records it rests on (each linking to its line in the timetable) and the date the status was set. The no-signal note opens a panel saying what it does and does not mean. The date a status was computed is never presented as the date something happened.
- **Reading order on a phone.** In the digest the sentence that says what the status means comes straight after the status label, ahead of the path and the dates; in "Pass it on" the sentence and its buttons come before the card. Only the drawn order changes, never the order a keyboard moves in.
- **The path, named.** The status label's info panel lists the six places on the path by name, the claim's own in bold with the marker beside it, so the unnamed dots of the track are explained where a reader presses to understand.
- **Stage track.** Under the digest's track one grey line says the place in words ("Place 4 of 6, from preclinical to approved"), the same words a screen reader is given. Six places on a line, from preclinical to approved, with one larger solid blue dot at the status's place. It marks a position, not progress, and is never filled up to the dot. It always sits beside the status in words. Failed, terminated and retracted have no track. The operator approved it on 2026-11-11 as the one exception to "no meters".
- **Facts.** Four facts under the digest, each a small grey label over its value, in columns that fold to two on a phone: intervention (its other names on a grey line beneath), what it is claimed for, first reported, and the evidence when first reported.
- **Key.** Beside the timetable heading: the amber swatch for "Promised", one drawing for each kind of record on the page, and the blue diamond for "Basis of status".
- **Timetable.** A framed table: year, Promised (pale amber, only when a dated promise exists), Recorded. Years with nothing collapse into one quiet row. Each record is one line: the drawing for its kind, the day, what happened, and a link to its source. Records in one year that share a source (a trial's registry entry) are one line with a dated step for each, so the source is named once. What happened is a dotted-underlined button with a small chevron (a report's title, which leaves the site, has an arrow) that opens a panel with the record's summary and where its date came from. A record the status rests on carries the blue diamond. A news report shows its title in quotation marks and its outlet. On a phone the rows stack, and amber is seen only where a promise exists.
- **Popover.** The browser's own popover, placed beside its trigger. Its button says whether the panel is open (`aria-expanded`), set by a small script when the panel toggles. Opens on tap, key press, or hover with a mouse; Escape or a tap outside closes it. White, hairline border, one soft shadow. On paper every panel is printed in place.
- **Outlet.** Wherever a web article is named: the outlet's own icon, its name and its short domain. The icon is 17 pixels square with the tile's 4-pixel corners, in its own colours on white so transparent marks remain legible on dark reading surfaces. Artwork that needs a publisher-coloured ground includes it in the image. It was fetched by the pipeline and is served as a content-versioned file of this site, because a page asks the network for nothing. An outlet with no usable stored icon gets a drawn letter tile of the same size; a generic hosting-platform logo is not a publisher mark.
- **Icons.** Lucide, stroke 1.7 to 1.9, in secondary-text grey. A drawing never stands alone: the key or the words beside it say what it is.
- **Promised with no date.** A pale amber list with dashed rules.
- **A promise in a list.** The year is bold; when the promise's own words name the year it is made bold where it stands and not said twice.
- **Index tables.** Claim (the intervention's name in bold as the link, reaching over its cell; under it the reported headline in grey at 0.95rem, held to two lines on a wide screen and shown in full on a phone), first reported, latest promise (pale amber only on rows that have one, the year in bold; the column is left out when no claim in the list has a dated promise), status with a small stage track beside the label. Under the label, the status gloss in grey at 0.9rem. The home page's list of news reports keeps the outlet's headline as its link, because a report is not a claim.
- **Status gloss.** One fixed phrase per status that says it without trial vocabulary ("Large late-stage trial in people"). Grey, under the label, wherever a list or a claim page shows a status; on the claim page it sits between the label and the precise meaning. Never in place of the label.
- **Topic summary.** A topic page's lede is one sentence built from the count of claims at each status, in path order ("Of 7 reported breakthroughs tracked, 5 have no trial in people on record and 2 have reached large late-stage trials in people."), then "Newest first." At most four statuses are named; the rest are counted together.
- **Stage filter.** Above a topic's table once it lists six or more claims: the path drawn large, with the number of claims at each place and the place's name. Each place is a button that narrows the table to it; pressing it again shows all. A place with no claim is not a button. Statuses off the path sit beneath as outlined buttons. It is also the legend for the small tracks in the table. Without JavaScript it still shows the counts.
- **Topic directory.** `/topics`: a "Find a topic" field that narrows the list as the reader types, a row of letters that jump to their section, and under each letter the topics in up to three columns, each with its number of claims. Built for hundreds of topics. When the export gives any topic a group, the headings are the groups from A to Z instead of letters: the group's name in ink in a column of its own beside its topics (above them on a phone), the jump row names the groups as small pills, typing a group's name keeps all its topics, and topics without a group come last under "Other topics". A group whose one topic carries the group's own name is said once: the topic's link, in bold, stands in the heading's column with its count beside it. On a phone the jump row is one line that scrolls sideways and fades at the ends, so the list starts on the first screen. The site never invents a group. The menu's "Topics" link leads here; the home page shows the twelve topics with the most claims and a link to the rest.
- **Home tally.** Under the opening band, the first line of the lists, one grey line: how many claims are tracked in how many topics, how many have an approval on record, and the day the registries were last checked. Counts only, each linking to its list.
- **Narrow these lists.** On a phone the status counts and the topic choice wait behind one outlined pill with a sliders drawing; pressed, it is tinted and they open beneath it. They start open when the address already narrows the lists. On a wide screen the pill is absent and they are always in view.
- **Home tabs.** Four tabs on a hairline, each with its count in a tint pill; the picked one is in ink over a 3px blue rule. On a phone they sit two by two, so none is off the side.
- **Not here yet?** The home page's last section: the sentence and link that suggest a headline. It left the opening band on 2026-11-14 so the band holds only the lookup and the page ends on something to do.
- **Headlines table.** On the home page: the ten newest news reports. Between the date and the status sits the latest dated promise on pale amber, when any report's claim has one, so the home page shows the same comparison a claim page does: what was said, what was promised, where it stands. The second table's date column is left out when every status in it was set on one day; the heading says the day once. The outlet's title sits in quotation marks and opens the claim page; the outlet's name beneath it, in regular weight, opens the report; then the date reported and the status now. The quotation marks and the outlet name are what mark the wording as someone else's, so neither may be dropped.
- **Opening band.** On the home page the title, the lede, the main box and its answer sit on a full-width band of the panel blue, between the navy masthead and the white lists, closed by a hairline. The operator asked for it on 2026-11-13 so that the lookup, which is what the site is for, has the page's focus. It is pale with ink on it, never a solid block of the accent. The lede is held to the box's width, so the band's column has one right edge. On the band the answer's digest panel is white in a hairline frame, because a panel there would be blue on blue. On paper the band has no fill.
- **Main box.** On the home page the field is the largest control: it takes a pasted article link or search words, and answers a pasted link at once. A tracked article is answered with a small digest panel: the status in blue, its place on the path, the no-signal note, the claim's headline, what the status means and a link to the records. When the box has no answer (an article not tracked, a search or lookup that failed), one small line follows: every claim is listed by topic, with the link, and a treatment's name can be typed. An untracked one shows close claims as a plain list, said to be a guess, so a guess never looks like an answer.
- **Search.** One labelled field and a button. A match is its headline as a link, then its status in ink ahead of its summary; a grey line above counts the matches. Shows "Searching…", then results, a plain "Nothing found" sentence, or a plain failure sentence.
- **Footer.** Deep navy. The two notices in bold, then data sources and the dates the registries were checked and the pages built.
- **Link-preview card.** White under a head that is the masthead: a deep navy band from edge to edge with the reverse mark and the wordmark in white and "Not medical advice" opposite in pale blue (`#c9d9ee`). Middle: the earliest article's title as the outlet wrote it, in quotation marks, with the outlet's name beneath; a claim with no article shows its own headline unquoted. Bottom, in the pale blue panel: "Status now" and the status in blue, the no-signal note when present, then the year first reported, the year promised by when there is one, and the month the registries were checked. The site puts no word of its own between the quotation and the status. Under the status sits the stage track, one place marked, in all three shapes; a status off the path has none. The year promised by is the only thing on pale amber, with a dashed rule, as in the timetable. Dates, never a count of days or years, so a saved card stays true. A title is cut at a word with an ellipsis past 150 to 200 characters, by shape. Built in three shapes from one description: wide 1200 by 630 (the link preview), square 1080 by 1080 and tall 1080 by 1920; in the square and tall shapes the dates sit under the status. The padding is counted inside the image, so nothing is cut off. Its text alternative is built from the same facts.
- **Pass it on.** The last section of a claim page: one line saying what it is for ("Seen this headline shared again? Reply with the record."); the square card itself, small, beside one dated sentence in a pale blue panel, ready to copy; pills to copy it, to download the square and tall cards and to copy the page's link. The networks are folded under "Post it to a network", so the first row is the four things a reader does most. The snippet that shows the status on another site is folded away just above this section, so the page ends on the sentence. Copy buttons appear only where copying works and say "Copied"; otherwise the text is left selected. Hidden on paper.
- **Embed.** `/embed/<slug>`, made for a frame of 440 by 420 that narrows with its host and never grows wider than 30rem; the headline is held to three lines: a hairline box whose head is a deep navy strip with the site's name in white and "Not medical advice" opposite in pale blue, then the claim's headline, the status with its track in a pale blue band, the checked month and a link to the records, then the two notices and the data sources in small type. Every link opens in the whole window. It loads nothing from elsewhere and stores nothing.
- **Method page.** Under the lede, the explainer video in a hairline frame with the panel's corners, held to the lede's width: the brand card as its poster, the browser's own controls, never playing on its own and fetched only when played. A grey line beneath says how long it is and the month its records are from; a fold, "What the video says", holds its narration. On paper the player is left out. Then a list of links to its sections; the claim page's status panel and no-signal note link straight to the sections that explain them. `/how-it-works`: prose in the reading measure, the rules as a numbered list, and each status in a framed list with its place on the path, its label and its meaning, read from the same source as the claim pages.
- **Anniversaries.** Opened on a day with no entry, a grey line under the lede names the next day on the calendar and links to it. `/anniversaries`: months as section headings, then each day with its claims: the year first reported in grey, the headline, the status with its track. Opened on a day that has entries, that day is tinted and marked "today". A feed at `/anniversaries.xml` carries the last thirty days.
- **Year and data pages.** `/year/<yyyy>` is a topic-style page: the count, then the claim table with its stage filter. `/data` links the downloadable file and states its licence.
- **Extension popup.** 360px wide, same tokens and face. The reverse mark and the site name in white on a deep navy head, as on the site; the claim headline; the status in the digest panel's treatment ("Where it stands", blue label, no-signal note in a dashed outline, one sentence of meaning); first reported; the latest promise on pale amber; one full-width blue button, "See the evidence", with a small arrow after the words because it opens a new tab (and "opens in a new tab" for a screen reader); every button that opens a tab carries the arrow. Under it, smaller, a hairline pill with a bell, "Keep me up to date", which follows the claim (the operator asked on 2026-11-13 for plainer words, a smaller control and icons); once followed it is a line with a tick, "You follow this claim.", and "Stop following". The reminder line starts with a clock. The two notices and the last-checked date sit under a hairline in muted small text. A tracked claim shows the stage track under its status, as the site does. A wait (checking the page, searching the registry) is marked by the site's dot, breathing slowly; with reduced motion it is still. A registry search starts with a compact, expandable "Automatic · Unreviewed" label, then the identified treatment and indication and the individual candidate cards. A reused answer keeps its checked date visible. Sources, additional search context and privacy sit in one native disclosure below the cards. A short medical limitation stays visible. Search again, Screenshot and Settings use labelled line icons in a quiet row; Screenshot opens the existing preview. A long answer scrolls under a thin bar in the tag blue. Messages (not tracked, not a web page, unreachable) are a heading, one or two sentences and at most one outlined button. Light only.
- **Automatic lookup cards.** Opening the popup on an untracked page starts one lookup. The loading state and automatic answer identify OpenAI processing and link to Privacy. Each potential record is a separate, white, hairline-bordered card with 12px corners and 14px padding. Its complete title links to the registry, followed by neutral phase and recruitment-state tags with small line icons. A blue match-confidence label is the summary of an expandable section containing the registry identifier, match reasons and confidence limitation. Blue distinguishes match information from neutral registry metadata; it never grades a treatment. Confidence remains a numeric model estimate, with no meter or traffic-light grade. The automatic/unreviewed label remains visible above the results; its full explanation opens on demand. Reviewed-claim links use the same grouping with reviewed provenance and no invented score.
- **Icon.** The operator selected the flat coral-and-blue magnifier on 2026-11-13. A white rounded square contains a blue `#16477d` magnifying glass with a short round-ended handle and a horizontal capsule: coral `#f28a62` on the left, clear blue `#1687da` on the right, divided by a white seam. These are brand colours, not evidence grades; coral never replaces the pale amber meaning “promised” in tables. No gradients, shadows, highlights or bevels. `site/public/mark.svg` is the canonical vector; `favicon.svg` is its optical version at 16–32 pixels with a larger lens, pill and seam. `site/scripts/brand-icons.mjs` generates raster icons plus square, standalone, monochrome, reverse and outlined-lettering lockup SVGs. The reverse mark (`mark-reverse.svg`) is for navy grounds: the site's masthead, the popup's head, the head of a status card and the site's own card. Every browser, toolbar and launcher icon keeps the white tile. Share cards read the canonical vector directly. The extension builds its icons from the same two sources. `extension/sync-brand-icons.mjs` updates the generated Safari image copies without changing its project, signing or version settings. A capsule can read as a pharmacy: external uses include the site name or “Not medical advice”. No tick, cross or grade appears in the mark.
- **Brand tagline.** “What happened after the headline?” The descriptive page copy continues to explain medical breakthroughs and evidence.
- **The site's own card.** `/brand-card.png`, 1200 by 630: the masthead at full size, so deep navy throughout: the reverse mark at 168 pixels, the name in white as the wordmark sets it, the tagline in pale blue, and a foot with the site's host and "Not medical advice". A page with no claim to show (home, topics, how it works) shares this card, so a link to the site never arrives bare. A claim page keeps its own status card.

## Motion

Three authored moments tell the site's story; the rest is feedback. Nothing loops, nothing moves on scroll, and no content waits for an animation to become readable.

| What | Motion | Time |
|---|---|---|
| Wordmark | The question mark's hook is drawn, then its blue dot lands. First page of a visit only; a hover plays it again. | 1.5 s, once |
| Stage marker on a claim page | The blue dot lands on the claim's place and one ring leaves it. It lands in place and never travels along the path, because a claim can reach a place without passing the others. | 0.6 s, once |
| Headline pressed on the home page | The headline is carried to its place under the claim page's title, and back again on return. Only the headline as the next page sets it is drawn, uncovered as its box opens, so it is never stretched and never seen twice. Up to three reports per claim; a headline with no place on the next page fades with the rest. | 380 ms |
| Popover | Fades in and rises 4 px beside its trigger; leaves faster. | 170 ms in, 90 ms out |
| Record or section reached by a link | The page scrolls to it, it shows in the tag blue, then settles to the tint. A section is marked along its heading's words. A link inside a popover closes the popover first. | 2.2 s |
| Between pages, and when a table is filtered | A cross-fade; the masthead holds still. | 170 ms |
| Lookup answer for a tracked article | The marker lands on the place, as on a claim page. | 0.6 s, once |
| Copied | The button's icon gives way to the blue dot, which lands; the label says "Copied" and a screen reader is told. | 0.4 s, then 2 s held |
| Extension popup, while waiting | The blue dot beside the waiting sentence fades in and out. The one loop on any surface, kept because the wait can last half a minute and the popup is closed when it ends. | 1.4 s each way |
| Explainer video on the method page | Plays only when the reader presses play. Made in `video/` with the site's own motion: things arrive and land, nothing flashes. | 1 min 52 s, on request |
| Chips, buttons, filter places | Colour changes ease; a pressed button drops 1 px; the chevron of a match's reasons turns. | 120 ms |

Easing is `cubic-bezier(0.16, 1, 0.3, 1)` for arrivals. With reduced motion asked for: no dots, no landing, no scrolling, no cross-fade, no carried headline, no movement; popovers still fade and a reached record is tinted without the change. Popover fades apply only where the browser has popovers, so elsewhere a panel is plain visible content. On paper nothing is hidden by a motion style.

## Dry wording

The voice is plain, exact and unexcited, and that is the only joke the site makes: its own way of reporting, turned on itself. It is allowed on the site's own furniture and nowhere else.

- Not-found page: "No page record found", the path with no place marked, and "Last checked: just now." Under it, the search and the topics: each by name while there are six or fewer, one link to the directory past that.
- A search with no result: "No record found for … We say that a lot."
- Footer: "We will check again." This is a promise; it stays only while the registries are in fact re-checked.
- Page source: one comment for a reader who checks it.

Never on a claim page, a card, an embed or the extension, never about a condition, a treatment, an outlet or the people behind a claim, and never a pun on a topic's name.

## Resilience

- Browser icons include SVG, PNG and a 16/32/48px ICO fallback. Brand asset URLs carry an artwork revision; launcher artwork stays inside the maskable safe area.
- Outlet names and domains wrap as separate groups with a clear gap. A missing or failed publisher image retains its letter tile without shifting the row.

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
- Tables carry their table, row and cell roles in the markup, because on a phone they are drawn as blocks and a browser would otherwise stop reporting them as tables.
- Source articles are linked by outlet, title and date. Their text is never shown.
- No stock photography. Topic imagery is a drawn mark in the accent colour.
- Everything pressed is at least 44 pixels tall on a phone: pills, the topic chip, the info button, the no-signal note, record details, the menu and the footer links.
- A link that leaves the site from a record line (a news report's title) carries a small arrow, so a quoted headline that opens the outlet is told from one that opens a claim page.
- A pasted article address never enters the page's own address; only typed search words do.
- A popover panel is a note to a screen reader, and every record line says its kind in words, not by its drawing alone.
- Focus is a 3px blue outline (white on the masthead and the footer). Selection is the tag blue, inverted on the masthead and the footer. The skip link is white with blue lettering, because it lands over the masthead. Hover thickens a link's underline, darkens the chip and the button.
- A date never breaks across two lines.
- Print hides navigation and search, drops the footer's fill and the table frame, never splits a record across sheets, and prints each source address after its link.

## Why blue

On 2026-11-12 the operator asked for dark blues on the light theme, chosen from the canvas of logo directions. The accent became the navy `#14427f`, with ink, tints and the footer moved to match. The reasons below are why the site is blue at all; they are unchanged.

The operator asked on 2026-11-11 for blue in place of the first indigo, to read as health, trust and clinical care, giving NHS blue as the example. The accent is a blue of that family, not the NHS palette: this site is not an NHS service and must never look like one. No NHS logo, lozenge, name or typeface, and no wording that suggests an affiliation.

Contrast, measured on 2026-11-12: text on white 16.5:1, blue on white 9.9:1, blue on the panel 9.1:1, blue on the tag 7.6:1, secondary text on white 7.5:1 and on amber 7.0:1, white on the footer 15.4:1. The masthead has the footer's ground, so white on it is the same; the lifted blue on it is 8.1:1, calculated on 2026-11-13.

## Review

The design reviewer judged this look on 2026-11-11 from captures of the claim, home, topic, approved and not-found pages at 1280 and 375 pixels wide, hover and focus states, and the printed claim page. It accepted the topic page, hover and focus, and asked for the fixes that are now in: the phone timetable's amber, the navigation's topic link, source names, date breaks, the footnote target size, two wording changes and the print layout.

Not yet judged:

- The reviewer judged the blue version in a second pass, found the eight fixes in place, and asked for three more that are now in: the icon is navy, years and footnote letters are in ink so blue text that is not the status label is always a link, and this note. Those three were checked by eye, not by a third review.
- The first accent (`#0b5cad`) sat close to NHS Blue in hue. The navy that replaced it on 2026-11-12 is darker and further from it; the rule on use still holds for the accent: text and small marks on white, no header band in the accent blue, no solid block of the accent with white lettering. The home page's opening band is the pale panel blue with ink on it, which this rule allows. The masthead, since 2026-11-13, is a solid block with white lettering, but in the footer's deep navy (`#0b2545`), which is far darker than NHS Blue; it must never be lightened towards the accent or a brighter blue.
- The navy masthead was checked by eye on the home and claim pages at desktop and phone width, with keyboard focus. The reviewer has not judged it. The extension popup, the embed, the link-preview cards and the site's own card took the same navy head on 2026-11-13, checked by eye in the popup states page, the embed at 440 by 420 and the three card shapes.
- Lists and tables have only been seen with one claim.
