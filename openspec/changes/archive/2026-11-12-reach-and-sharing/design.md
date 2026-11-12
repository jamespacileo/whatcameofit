# Design

## Context

See `proposal.md` for why. What shapes the approach:

- The site is static: built from one JSON export, served as files. There is no server of its own to receive anything, and nothing public may be served from the home network.
- The card is drawn at build time by `site/src/pages/og/[slug].png.ts`. It already shows the icon, the wordmark, the claim's headline and a panel of facts at 1200 by 630.
- The export already carries each claim's articles (outlet, title, date), first-reported date, status and explaining events, and the date the registries were last checked. Nothing here needs a new field.
- `site.config.mjs` holds the brand strings and a local address. A site test forbids any page from asking another host for anything.
- No personal data is collected before Phase 2.
- The site is not deployed, 46 of 52 claims await review, and the name's final address is undecided.

## Goals / Non-Goals

**Goals:**

- Everything a reader can pass on states records as dated facts, so it stays true after it leaves the site.
- Every new surface is a static file built from the export.
- Reach can be judged from counts alone.

**Non-Goals:**

- Deploying the site, reviewing pending claims, or releasing the extension to a store. They are prerequisites, tracked elsewhere.
- Accounts that reply to posts automatically (see D9).
- Any table or page that ranks or compares outlets (see D10).
- Following a claim by email or any other notification that needs an address (Phase 2).
- Paid promotion.

## Decisions

### D1. The card quotes the outlet and dates itself

The contrast between what was announced and what the records show is the reason anyone would pass a card on. The card shows that contrast and stays silent about it: the outlet's title in quotation marks with the outlet named, the status in the site's wording, the year first reported, and "checked <month year>".

Alternative considered: "7 years later" in large type. Rejected: an image cannot be rebuilt once it has been saved and reposted, so an elapsed count becomes wrong, and the existing rule against day counts exists for the same reason. Two dates let the reader do the subtraction and are true for ever.

Alternative considered: the claim's own headline, as now. Kept only as the fallback for a claim with no article, because the site's paraphrase carries less recognition than the wording people remember.

### D2. One description of the card, three layouts

`site/src/lib/card.ts` already builds the card's facts and its text alternative from one function. It gains the quoted title, the outlet and the checked month. The image route becomes three routes that share that function and differ only in size and arrangement, so the shapes cannot drift apart. The claim page's download links and their text alternatives read from the same facts.

Alternative considered: generate the square and tall shapes in the reader's browser on demand. Rejected: it needs the image renderer in the page, and the files are small.

### D3. "Not medical advice" on everything that leaves

The footer notices cannot travel with an image or an embed. The card, the embed and the copied sentence each carry the short form. The longer notice about registered trials stays on the page; the short form is the one that fits and the one most needed where context is lost.

### D4. The embed is a page, not a script

`/embed/<slug>` is an ordinary static page with its own small stylesheet, shown by the embedding site in an `iframe`. The snippet on the claim page is that `iframe` tag and nothing else.

Alternative considered: a script tag that injects markup. Rejected: it runs our code in someone else's page, which they would have to trust and which could not be shown to be harmless. A frame cannot read or change its host, and the host's content rules usually allow it.

The embed asks search engines not to index it and is left out of the sitemap, so it does not compete with the claim page. Its link opens the claim page in the whole window.

### D5. Anniversaries are computed at build, dated by themselves

The page lists claims by month and day for the whole calendar, so it is true whenever it is read; a small script scrolls to today. The feed holds the anniversaries of the last thirty days as of the build, each item dated to its anniversary and stating the years passed as of that date.

Alternative considered: a feed of "today's anniversaries" only. Rejected: a static site is not rebuilt every day, and an empty or stale "today" feed is worse than a thirty-day window whose items are each correct as dated.

Posting anniversaries to social accounts is done by the operator by hand from the feed. No account is automated in this change.

### D6. Contact is a link, configured, absent by default

`site.config.mjs` gains two optional addresses, one for suggestions and one for corrections. Each may be a `mailto:` address or the address of a public issue form. When set, the site builds a link that carries the article address or the claim page address forward as a query value; when unset, no link is drawn.

Alternative considered: a form posting to a third-party form service. Rejected: it sends a reader's words to a party the reader did not choose, and it is the first step toward the site holding personal data, which is not allowed before Phase 2.

The pasted article address is carried in the link the reader follows, never sent by the site. This keeps the lookup's existing promise that a pasted link is never sent anywhere.

Which of the two channels to use is the operator's choice at deployment and does not change what is built.

### D7. The method page reads its wording from the status module

`site/src/lib/status.ts` already holds each status's label and meaning and refuses verdict wording at build. The method page lists them from there, so the page cannot disagree with the claim pages. The rules' own description (precedence, the no-signal years) is written once on the page and checked against the pipeline's rules by hand when either changes; a test asserts that every status code appears on the page.

### D8. Structured data that describes, never rates

Claim pages carry `WebPage` data with `datePublished` (first reported), `dateModified` (registries last checked) and the publisher. `ClaimReview`, `Review` and `Rating` are not used: each requires a rating or a verdict, which the product forbids, and a search engine would show it as a fact-check label.

The canonical address and the sitemap need the public address. A public build with a local address stops with a message, so a sitemap full of `localhost` cannot ship. A preview build publishes no sitemap and keeps its existing no-index.

### D9. No automated reply accounts

An account that replies under other people's posts would put the site's status beside a stranger's words without the site having checked that the post is about the same claim. One wrong match, at reach, is the failure the review gate exists to prevent. The lookup, the extension and the card let a person do the same thing with their own judgement.

### D10. No outlet tables

Counting how many of an outlet's reported breakthroughs reached a trial is arithmetic on public records, but a table of outlets is read as a ranking, and a ranking is a verdict on the outlets. The year pages give counts by status, which describe claims, not publishers.

### D11. Measurement comes from the host, not the page

Counts per page, per day and per referring site are what a static host's own request logs give. No script is added to the pages for it. Card and data downloads are ordinary file requests and are counted the same way. If the chosen host cannot give day-level counts without storing addresses, the method page says nothing is counted.

Alternative considered: a cookieless counting script from a privacy-minded provider. Not ruled out for later, but it is another party's script on every page and would break the test that pages ask no other host for anything. It needs its own change.

### D12. Open data is the export, filtered, with its licence inside

The site writes the download from the export it already validated, dropping outlet icon images and adding a header with the licence from `LICENSE-DATA`, a credit line, the sources and the method page's address. It is one JSON file. A CSV is not built: claims hold lists (events, articles, promises) that a flat table would have to invent rules to flatten.

## Risks / Trade-offs

- [A wrong status spreads further than it can be corrected] → Nothing in this change publishes a claim; the review gate is unchanged. Cards and embeds are built from the same export as the pages, so a correction reaches the embed at the next build. A saved image cannot be recalled: the checked date on it says what it was true as of.
- [A card is read as "debunked"] → The card adds no word of its own between the quoted title and the status. A build check already fails on verdict wording in status labels; it is extended to the card's fixed strings.
- [A status such as "Phase 1 trial" is read as "available"] → "Not medical advice" on everything shared; the copied sentence and the embed use the site's status wording only.
- [Three images per claim slow the build] → The 250-topic trial build spent most of its time on images. Accept the cost for now; if it grows past a few minutes, build only the wide shape eagerly and the others on a separate command.
- [Outlets object to their titles on cards] → Titles are short quotations, attributed, beside a link to the article, used to identify what is being tracked. The operator should still take advice before a public launch; noted in `docs/launch.md`.
- [The embed is used on a page that misrepresents the claim] → The embed states its own date and links to the full page. The site cannot control where a frame is placed.
- [Anniversary items read as mockery] → Items state the date, the years passed and the status, nothing else.

## Migration Plan

Each part is additive and can ship alone. Order: card first (it changes an existing image), then the pages, then the files that need the public address. To withdraw any part, remove its route or its link; no stored data is involved.

## Open Questions

- Which channel for suggestions and corrections: mail or a public issue form. Decided at deployment; both are built.
- Whether the chosen host can give day-level counts without storing addresses. Decided at deployment; the method page's wording follows from the answer.
