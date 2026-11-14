# Design

This file is the design brief, confirmed by the operator on 2026-11-14. It fixes who each page is
for, what it must prove, its structure and its limits. It does not fix the composition of
the two pages that persuade; those get a structure round when they are built.

## One world, three modes

Every new page inherits the evidence digest in `DESIGN.md`: the same tokens, face,
masthead, footer and motion list. No new colour, no photograph, no new typeface. What
differs is the reader's success on each page.

| Page | Mode | The reader succeeds when |
|---|---|---|
| `/guide`, `/guide/<slug>` | Read | they understand a word they met, and know what it does not say |
| `/topic/<slug>` (sharpened) | Read | arriving from a forum, they see what the page is and can pass it on |
| `/for/<audience>` | Persuade, by use | they have used the tool made for them |
| `/extension` | Persuade | they install it knowing exactly what it sends |
| `/about` | Persuade | they believe the gap is real and look up a headline |

On the Read pages ambition is precision. On the Persuade pages the page's proof is the
product at work on real published claims, at full size, never a description of it.

What may never appear on any of them: a grade, score or meter; a status colour; amber for
anything but a promise; a testimonial, rating, user count or press logo; wording that
suggests an NHS or other official service; advice.

## Guide

**Job and audience.** A reader on a claim page, a topic page or the home page meets a
word and wants it explained without leaving the site's voice. A second reader arrives
from a search for the word itself. Both read on a phone.

**Outcome and proof.** One sentence that answers, then what the word rests on in the
records, then what it does not tell you. Proof is two things no other glossary has: the
site's own rule for the word, and tracked claims where the word applies today.

**Entries.** Twenty-seven, on three shelves.

- *Statuses* (10): one for each status. The label, gloss and meaning come from
  `status.ts`, the one source the claim pages read, and are not typed again.
- *Words this site uses* (8): claim; promise; record; match and confidence; no signal;
  origin paper; follow-up paper; checked by a person.
- *How research is recorded* (9): clinical trial; trial registry; trial phases;
  laboratory and animal studies; primary endpoint; a trial that ends early; regulatory
  approval; retraction; why a registered trial is not a treatment option.

The reader-facing words come from `GLOSSARY.md`. An entry uses a term exactly as the
glossary fixes it, and the guide never introduces a term the glossary lacks.

**Entry page, in reading order.**

1. Shelf name as a small label, then the title.
2. The answer: one sentence at lede size. A status entry shows its place on the path
   beside it, as the method page's status list does. It is not set in the digest panel:
   that panel means "where this claim stands" and stays on claim pages.
3. *In the records*: what a registry, journal or regulator holds that this word names.
4. *What it does not tell you*: the limits, in the site's own flat voice. For a status
   this is the most useful paragraph on the page ("Phase 3 trial" does not say the
   treatment works; it says a large trial has started).
5. *On this site*: the rule that uses the word, linked to its section of the method page,
   then up to three tracked claims where it applies now, in the index table. A status
   entry gives the count and links the home list narrowed to that status. With no claim
   to show, one sentence says so.
6. *Sources*: each a name, a link and the day it was checked.
7. *Related*: other entries by title. Then the next and previous entry on the shelf.

**Index page.** Three shelves as headed lists: each entry's title as the link and its
one-sentence answer in grey. Statuses are listed in path order with the small stage
track, then the four off the path. A "Find a word" field narrows the list as the reader
types, in the pattern of the topic directory.

**Wiring.** The guide earns its place by being one press away from the word:

- claim page: the status info panel and the no-signal panel each end with a link to their
  entry; the "not yet checked by a person" notice links to its entry;
- method page: each status in the framed list links to its entry;
- home page: the "No signal" and "It happened" tabs' lists open with one grey line and a
  link to the entry.

The existing sentence of meaning stays where it is. The guide adds depth; it never
becomes the only place a status is explained.

**States and ranges.** An entry runs from 150 to 500 words. Sources: one to four. Related
entries: none to five. Live claims: none to three. A status with no claim today (failed,
terminated and retracted have none in the published export) still has a full entry.

**How entries are held.** One Markdown file per entry in the site, with front matter: the
title, shelf, answer, sources (name, address, day checked), related entries, whether a
person has checked it, and for a status entry its status code. Loaded at build. The build
fails when a status has no entry, an entry on the third shelf has no source, a related
entry does not exist, or the text holds verdict or advice wording. The check reuses
`assertNeutral` and adds the advice words.

**Who writes them.** An assistant drafts each entry from the cited source and marks it as
not checked by a person. The page carries the same notice a claim page does, under the
answer. The operator reading an entry and setting it checked is the review.

## Extension page

**Job and audience.** Two arrivals. A reader who has just used the site and reads health
news often. A person who followed the "website" link from a store listing and is deciding
whether to trust a new extension with their browser. The second is sceptical and is the
one to design for.

**Outcome and proof.** They install it, having read what leaves their browser and when.
Proof is the popup itself, drawn in the page from the popup's own markup and tokens at
its real 360 pixels, answering for a published claim taken from the export at build, with
the month the registries were checked. No screenshot: a screenshot goes stale and the
page is rebuilt with the site.

**Structure.**

1. *First viewport.* The thesis is the product's own comparison, moved to where the
   reader meets a headline: an outlet's title in quotation marks with the outlet and the
   date, as a reader sees it, and beside it the popup saying where that claim stands now.
   Under it one sentence and the install control for the reader's browser, the other
   store beside it as a quiet link.
2. *Three answers it gives.* A tracked article: the status. An untracked article: a
   registry search, marked automatic and unreviewed, each candidate with its confidence.
   A claim you follow: "Was: X. Now: Y." as a notification. Each shown as the popup state
   it is, not as an icon and a paragraph.
3. *What it reads, sends and keeps.* A plain table: what, when, where it goes, how long
   it is kept. The first row is the one that matters: a reviewed match is answered inside
   the browser and sends no page address. The automatic search and its screenshot
   fallback get their own rows, with OpenAI named, and the setting that turns them off.
   Every row is true to the privacy page, which is linked.
4. *What it asks of your browser.* The permissions in plain words: this site's host,
   `t.co`, alarms, notifications.
5. *The two notices*, in full, in the body and not only the footer.
6. *Install*, again.

**Signature.** The marker lands on the claim's place in the drawn popup, once, as it does
on a claim page. Nothing else moves.

**States.** A store address is a deployment setting, as the suggest address is. With
neither store configured the page is not built and nothing links to it. With one, only
that store's control is drawn and the other browser is told plainly that it is not yet
available. With scripting off both controls are shown, neither marked as the reader's.

**Anti-goals.** No "trusted by", no star rating, no count of installs, no browser-chrome
mock-up with a fake article body (the site never shows article text, and a drawn article
would have to invent some). The headline, outlet and date are the whole of the article
side.

## About page

**Job and audience.** A reader arriving from an announcement, a journalist's link or a
forum post, who has never seen the site and doubts it. Also anyone who asks "who is
behind this?".

**Outcome and proof.** They believe the follow-up gap is real, understand that the site
describes records by rule and judges nothing, and try the lookup. Proof: one cited
finding on how rarely follow-ups are reported (Dumas-Mallet et al., PLOS ONE, 2017, to be
stated from the paper itself, not from a news summary of it), and the site's own claims.

**Structure.**

1. *First viewport.* One sentence as the title, in the voice the explainer video already
   uses ("Headlines like these travel fast. The follow-up rarely does."). Under it one
   published claim at page scale: the outlet's headline in quotation marks and its year,
   the years since drawn as the timetable draws them, a promise on amber where one
   exists, and the status now in words with its place on the path. The reader sees the
   product's whole idea before reading a paragraph about it.
2. *The gap.* Two or three sentences and the cited finding, with its link.
3. *What this site does.* Three rules, each one line and a link to its section of the
   method page: one page per claim; status by fixed rule from public records; every
   record links to its source.
4. *What it does not do.* No advice, no verdicts, no grades, no ranking of outlets. For
   the readers who care about research integrity this is the persuasive part.
5. *Check it yourself.* The open data, the method page, the corrections address, the
   count of claims and topics from the export.
6. *Who runs it.* The operator by name, as the privacy page already gives it, and that
   the site has no funder or advertiser to declare. To be worded by the operator.
7. *The lookup box*, the home page's own, as the page's last section and its action.

**Anti-goals.** No mission-statement language, no founder story, no timeline of the
project, no numbers the export cannot produce. Short: under two screens on a laptop.

## Audience pages

**Job.** A link to put in a message to one kind of person. Each page is the tool made for
that reader, already working, with the three things they will ask next.

| Page | Title names the situation | Tool in the first viewport | Then |
|---|---|---|---|
| `/for/journalists` | Writing a follow-up? | Find a claim; its status box appears as it will on their page, with the snippet to copy | How to cite a page (address and the month checked); where corrections go; the open data. Says outright: outlets are never ranked or compared |
| `/for/clinicians` | Asked about a headline? | The lookup box; the answer comes with the sentence to copy and the card | A claim page prints cleanly; the two notices in full; what a status does not say, linked to the guide |
| `/for/researchers` | Studying what follows the news? | The data file: download, licence, the day it was built, its fields | How a status is set; what a match's confidence is and is not; the feeds; how to report a wrong match |

One template for all three: title, one sentence, the tool, three short items, the limits
that matter to this reader, the contact address. The tools are the existing ones (search,
embed, lookup, copy, download), not new versions of them. The journalists' picker is the
one new interaction: the site's search field, whose result is the claim's embed at its
real 440 by 420 and the snippet under it.

**States.** Search with no result offers "suggest a headline". A claim page not yet
checked by a person says so in the embed already; the picker shows the embed as it is.

## Topic pages for communities

A forum member follows a link to `/topic/hair-loss`. Today the page opens on a title and
a count, and the ways to pass it on are at its foot.

- Under the title, the grey line a claim page already has, in the topic's words: what
  this page is, and the link to the method page.
- Under the summary sentence: Share, the topic's feed in the open, and "Copy sentence",
  which copies the summary with the month checked and the page's address.
- At the foot: "Not here?" with the suggest link, once an address for it is configured.
- A link-preview card for the topic, so a link in a forum post arrives with the topic's
  name, its drawing, where its claims stand in the summary's own words, and the month
  checked. Today a topic shares the site's general card.

The address, the table and the stage filter are unchanged.

## Ways in

- Footer: Guide, Extension (when installable), About join How it works, Anniversaries,
  Data and Privacy. The audience pages are one line: "For journalists, clinicians and
  researchers".
- Home page, last section: when the extension can be installed, one sentence and a link
  beside "Not here yet?".
- Claim page, "Another headline?": the same sentence and link.
- Sitemap and structured data cover every new page; a guide entry is a defined term.

## Constraints

- Static, built from the export and the entry files alone. No new service, no storage
  beyond what the site already keeps in the reader's browser.
- No third-party request from any new page. Store buttons are the site's own drawn
  controls, not the stores' badge images.
- Every count on a landing page is computed from the export at build.
- 44-pixel targets, one breakpoint, print styles, forced-palette outlines and the footer
  notices hold as on every page.
- `PRODUCT.md` and `DESIGN.md` are updated when each part ships, not before.

## Order of building

Each part ships on its own.

1. Extension page. The store listing needs it and the review is under way.
2. Guide: the statuses shelf and its wiring first, then the other two shelves.
3. Topic pages and the topic card.
4. About page. Needed before anything is announced.
5. Audience pages. Needed when outreach starts.

## Decisions

The operator confirmed this brief on 2026-11-14, with these answers.

1. **Masthead.** It keeps its three links. "Guide" is linked from the footer and from
   where a word is met.
2. **Guide entries and review.** An entry is published marked "not yet checked by a
   person", as a claim is (ADR 0001). The operator reading it sets it checked.
3. **About page, "who runs it".** The operator is named, as on the privacy page. The
   sentence on funding is the operator's to word (task 4.4).
4. **Store buttons.** The site's own controls. No store's badge image is loaded.
5. **The example claim** on the extension and about pages is chosen by a rule from the
   export: a status on the path, a dated promise, then the most news reports. It is not
   named in the settings.
6. **Composition of `/extension` and `/about`.** The structures above are the lead. Each
   gets a round of three first-viewport sketches to choose from when it is built.
