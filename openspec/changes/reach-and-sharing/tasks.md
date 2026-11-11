# Tasks

Prerequisites outside this change: a public deployment with a final address, the review of pending claims, and the extension's store release (`browser-extension`). Groups 1 to 6 can be built and tested before any of them. Group 7 needs the public address to be verified for real.

## 1. Card, second version

- [x] 1.1 Extend the card's facts in `site/src/lib/card.ts` with the earliest article's title and outlet, the first-reported year and the checked month, with the claim's own headline as the fallback; verify a site test "Card facts: claim with two articles picks the earliest" and "Card facts: claim with no article" pass
- [x] 1.2 Redraw the wide card to set the quoted title and outlet beside the status, with "Not medical advice" and the site's name; verify by reading the built PNG for a claim with a 140-character title and for the seed claim that nothing is cut off and the title is in quotation marks
- [x] 1.3 Update the card's text alternative to the same facts; verify the site tests "Claim promised for 2025" and "Claim with no promise" are updated and pass, and that the alternative contains no count of days or years
- [x] 1.4 Extend the build's verdict-wording check to the card's fixed strings; verify a test that adds a forbidden word to them fails the build
- [x] 1.5 Add the square (1080 by 1080) and tall (1080 by 1920) card routes from the same facts; verify a site test asserts each file exists at its size for every published claim, and read one of each to confirm nothing is cut off
- [x] 1.6 Record the card's new layout and three shapes in `DESIGN.md`; verify the "Link-preview card" entry names the quoted title, the two dates and the three sizes

## 2. Taking a claim away

- [x] 2.1 Add download links for the square and tall cards to the claim page, each with its text alternative; verify a site test finds both links on a claim page and that each target exists
- [x] 2.2 Add the sentence to copy, with a copy control that confirms and a selectable fallback; verify a site test finds the sentence with the first-reported month, the status label, the checked month and the page address, and check by hand that the keyboard reaches the control and that refusing clipboard access shows the fallback
- [x] 2.3 Build the embed page at `/embed/<slug>` with its own small stylesheet, the no-index instruction and a link that opens the claim page in the whole window; verify site tests "Embed shows status and links out" and "Embed asks no other host" pass
- [x] 2.4 Show the embed snippet on the claim page; verify by placing the snippet in a scratch HTML file that the frame shows the status and its link leaves the frame
- [x] 2.5 Check the claim page at 375 and 1280 pixels with the new controls; verify nothing overflows and the share controls do not push the status off the first screen

## 3. Anniversaries

- [x] 3.1 Add a pure function that groups published claims by month and day of first report and one that lists anniversaries in the thirty days up to a given date; verify tests cover a leap day, a claim with no date, and a first report under a year old
- [x] 3.2 Build the anniversaries page with today's entries brought into view by script; verify site tests "Claims on a calendar" and "Claim without a first-reported date" pass, and that the page reads correctly with scripting off
- [x] 3.3 Build the feed with each item dated to its anniversary; verify a site test builds with a fixed date and finds an item dated to the anniversary stating the whole years passed, and none for a claim under a year old
- [x] 3.4 Link the page from the footer and the feed from the page's head; verify a feed reader or `curl` shows a valid feed from the built site

## 4. Method and year pages

- [x] 4.1 Write the method page from the status module's labels and meanings, with the rules, what the site never says, the sources and how to report an error; verify a site test asserts every status code's label appears on it and that the footer notices are present
- [x] 4.2 Link the method page from every claim page and the footer; verify a site test finds the link on a claim page
- [x] 4.3 Build a page per year with a published claim, using the existing claim table and its status counts; verify site tests "Claims first reported in a year" and "A year with nothing has no page" pass
- [x] 4.4 Link year pages from the home page and from each claim's first-reported date; verify the links resolve in the built site
- [x] 4.5 Add both page types to `DESIGN.md` and remove them from the "Not yet" list in `PRODUCT.md`; verify both files mention them

## 5. Reader contact

- [x] 5.1 Add optional suggestion and corrections addresses to `site/site.config.mjs` and a helper that builds a link carrying an address forward for either a mail address or an issue form; verify tests for both kinds and for an unset address
- [x] 5.2 Show "suggest this headline" in the lookup's not-tracked answers and on the home page, labelled by what it opens; verify a site test with the address set finds the link holding the pasted address, and with it unset finds no link
- [x] 5.3 Show "report an error" on every claim page, carrying the page's address; verify a site test finds it with the address set and not with it unset
- [x] 5.4 Confirm no page holds a form that posts to the site; verify a site test asserts no `<form>` in the built pages has a `method` of post

## 6. Open data

- [x] 6.1 Write the data file from the validated export without icon images, with the licence, credit line, sources and method address in its header; verify a site test asserts it lists only published claims, holds no icon data and no article text field, and names the licence
- [x] 6.2 Add a page that links to the file and states the licence and credit; verify the link resolves and the wording matches `LICENSE-DATA`
- [x] 6.3 Mark the file as a preview in a preview build; verify the site test that builds a preview finds the mark

## 7. Found and cited

- [x] 7.1 Add the canonical address to every page from the configured public address; verify a site test finds it on each page type
- [x] 7.2 Add `WebPage` structured data to claim pages with the first-reported and last-checked dates; verify a site test parses it and asserts no `ClaimReview`, `Review` or `Rating` type appears anywhere in the build
- [x] 7.3 Publish a sitemap of every public page except embeds, and none in a preview build; verify site tests for a public and a preview build
- [x] 7.4 Stop a public build whose configured address is local; verify a test that such a build exits non-zero with the message, and that the default and preview builds still pass
- [x] 7.5 Set page titles for claim pages so the intervention and indication appear before the site name; verify by reading the built titles for three real claims that each fits in 60 characters or ends cleanly

## 8. Measurement and launch

- [x] 8.1 Add to the method page what is counted and that readers are not tracked, worded for the "nothing is counted" case until a host is chosen; verify the wording is on the built page
- [x] 8.2 Add a site test that no built page sets a cookie or references another host in a script, image or stylesheet; verify it passes and that it fails when a third-party script tag is added
- [x] 8.3 Write `docs/launch.md`: the prerequisites, the order of release, where to announce (with the communities and people from the growth notes), what to say and not say, the questions to settle with advice before launch (quoting titles, outlet icons), and how to answer a report of a wrong status; verify the file exists and each section is filled
- [x] 8.4 Run `make check`; verify it exits 0
- [x] 8.5 Check five real claim pages, their three cards and their embeds by eye at phone and desktop widths; verify each card reads as the outlet's words beside the site's status and nothing reads as a verdict

## Workflow follow-up

- Deploy the site and set the public address, then repeat 7.3 and 7.4 against the real address.
- Choose the suggestions and corrections channel and set both addresses.
- Find out what the host can count, then finish the wording in 8.1.
- Post the first anniversaries by hand from the feed and note in `docs/launch.md` what was passed on.
