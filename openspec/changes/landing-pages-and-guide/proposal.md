# Landing pages and a reference guide

## Why

Every page on the site answers a reader who already has a question. None is made for a
person who has to be told what the site is, why to trust it, or what to do with it.

- The extension is linked from nowhere on the site, and a store listing needs a page to
  point at (design review, 2026-11-14: "extension has no install link anywhere").
- `docs/launch.md` names who to tell (topic communities, journalists, clinicians, people
  who study research integrity) and what to send each. Only the method page and the topic
  pages exist to send.
- Readers meet "Preclinical only", "No signal", "Phase 2 trial" and "Trial registered"
  with one sentence of meaning. The same review scored help and documentation 2 of 4.

The operator asked on 2026-11-14 to consider marketing landing pages and wikis, and chose:
an extension page, a page per audience, a page on why the site exists, sharper topic
pages for communities, and for "wiki" a reference guide the site writes itself. The
operator confirmed the brief in `design.md` the same day.

## What changes

- **Guide.** `/guide` and one page per entry: every status, the site's own words (claim,
  promise, record, match, no signal), and how research is recorded (registries, phases,
  approval, retraction). Each entry cites public sources with the day they were checked,
  shows the word at work on tracked claims, and is linked from where a reader meets the
  word. It is written by the site. Readers cannot edit it.
- **Extension page.** `/extension`: the popup's answer for a real tracked claim, what the
  extension reads, sends and keeps, and the install buttons. Drawn only once a store
  address is configured.
- **About page.** `/about`: the gap between a headline and its follow-up, with its
  source; what the site does and does not do; who runs it; and the lookup box.
- **Audience pages.** `/for/journalists`, `/for/clinicians`, `/for/researchers`: each
  opens on the one tool made for that reader, working, not described.
- **Topic pages for communities.** The existing `/topic/<slug>` page says what it is to a
  reader arriving from a forum, puts Share, the feed and a sentence to copy under its
  summary, and has its own link-preview card.
- **Ways in.** The footer links the guide, the extension page and the about page. The
  home page and the end of a claim page name the extension once it can be installed.

## Not changed, on purpose

- No reader-edited wiki. It needs accounts and moderation, and the site holds no personal
  data before Phase 2.
- No page per treatment or condition beyond the topic pages. The operator chose the
  reference guide only.
- No second address for a topic. A community page that copies a topic page would split
  its links and its link preview.
- No testimonials, user numbers, ratings, press logos or comparisons with named sites.
  `PRODUCT.md` records that none exists, and none may be implied.
- No counting of who presses an install button. `site-measurement` already limits the
  site to counts of requests.
- The masthead keeps its three links. The guide is linked from the footer and from where
  a word is met.
- The method page keeps the explainer video and the rules. The about page links to them
  and does not repeat them.

## Risks

- **Guide entries are general statements about medical research, written by an
  assistant.** A wrong one costs the brand more than a missing one. Each entry therefore
  cites a regulator, registry or publisher standard, carries the day it was checked, and
  is marked as not yet checked by a person until the operator has read it, as claim pages
  are.
- **Explaining a trial phase sits one step from advice.** Entries describe records. A
  build check refuses advice and verdict wording, and no entry says what a reader should
  do about their own care.
- **The extension's privacy claims are exact and conditional.** A reviewed match sends
  nothing; an automatic search of an untracked page sends page content. The landing page
  must say both. `PRODUCT.md` still says "sends no page address anywhere", which the
  privacy page no longer supports; it is corrected in this change.
- **Three pages now explain the site** (home, about, method). The about page is held to
  why and who; it never restates how a status is set.
