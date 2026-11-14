# Tasks

Each numbered group is one pull request. Groups 1, 3, 4 and 8 depend on nothing; group 2 comes before 5 and 6 (they use its database); group 7 is the operator's and can start at any time. All site work builds on `share-everywhere`.

## 1. Search items (gap 8)

- [ ] 1.1 Add the large-preview permission to every page of a non-preview build; verify a reach test finds it on a public build and finds only `noindex` on a preview build
- [ ] 1.2 Give each claim's sitemap entry the date its status was last set, and no date to other pages; verify a test reads the fixture's date from the sitemap and that a second build of the same export gives the same dates
- [ ] 1.3 End a claim's tab title with its status, clip the first part at a word to 65 characters, and leave the site's name off claim titles only; verify tests for a short and a ninety-character name, and that `og:title` is still the headline
- [ ] 1.4 Publish each claim's data file and name it as the claim page's alternate, with a visible link; verify a test compares it with the same claim in `claims.json`, and that an archived claim has no file
- [ ] 1.5 Publish `/llms.txt` from the brand config, the notices and the data constants; verify a test finds both notices, the data addresses, the licence and no status label, and that a preview build says its claims are unchecked
- [ ] 1.6 Add the cite line and its copy control to the claim page; verify a test of the line's wording against the neutral check, and by hand that copying works from the keyboard and is announced

## 2. Counting (gap 3)

- [ ] 2.1 Add the D1 database binding and the first migration (page, download and missed-lookup tables), and have `make deploy` apply migrations; verify the migration applies to a local database and `docs/deploy.md` says how to create the database
- [ ] 2.2 Count a reader's page view by page, day and referring host after the response is sent; verify Worker tests for a browser request, a crawler, a link-preview fetcher, a request with no referrer, a referrer on the site itself, and a failing database that leaves the response unchanged
- [ ] 2.3 Count downloads of square, tall and change cards and of data files, leaving out the card shown inline; verify Worker tests for a download, an inline image request and a crawler
- [ ] 2.4 Add `make counts` to print counts for a period; verify it runs against a local database seeded by the tests
- [ ] 2.5 Rewrite "What is counted" on the method page and the matching lines on the privacy page; verify the existing measurement tests still pass (no cookie, no other party's script) and a test finds the new wording

## 3. Cards (gaps 4 and 7, drawing only)

- [ ] 3.1 Add the change card's content and drawing in the wide and square shapes, built only for claims with a changed status; verify card tests for a forward change, a backward change and a claim with no change, and look at both shapes for a fixture claim
- [ ] 3.2 Offer the change card in "Pass it on" with its text alternative; verify a site test on a fixture claim with history and one without, at desktop and phone widths
- [ ] 3.3 Add the year and topic cards and make them those pages' link previews; verify tests for the counts' wording ("1 claim", "Approvals on record: 0 of 6"), the neutral check, and that each list page's preview image is its own card

## 4. Install and share target (gap 6)

- [ ] 4.1 Make the manifest installable with a share target that posts to `/share`; verify a test of the manifest's fields
- [ ] 4.2 Answer `POST /share` in the Worker by handing the first web address to the home page without putting it in any address; verify Worker tests for an address in `url`, an address inside `text`, and text with no address
- [ ] 4.3 Have the home page pick up a shared address, clear it and run the lookup; verify in the browser that the answer shows and the page's address is bare, and that a reload does not repeat the lookup
- [ ] 4.4 Check on an Android phone that the installed site appears in the share sheet and that a page's address can still be copied from the installed copy; record the result in the pull request

## 5. Missed lookups (gap 2)

- [ ] 5.1 Count a miss by cleaned address and day when the service has read a public article, including when the answer came from the cache; verify Worker tests for a counted miss, a refused address, pasted text, a screenshot, a post, an unreadable article and a failing database
- [ ] 5.2 Amend the in-flight `live-lookup` requirement "A lookup keeps nothing it read" to name the count; verify `openspec validate live-lookup` passes
- [ ] 5.3 Add `make demand` to write the intake file, most asked first, into a folder git ignores; verify it against a seeded local database and that no built page, feed or data file contains a missed address
- [ ] 5.4 Say on the method and privacy pages that a looked-up article's address is counted by day for ninety days; verify a test finds the wording
- [ ] 5.5 Add "missed lookup" to `GLOSSARY.md` and the intake steps (`make demand`, then `thenwhat extract new`) to the README's operator section; verify the documented commands run as written

## 6. Announcements (gap 4, posting)

- [ ] 6.1 Read Bluesky's and Mastodon's current terms, automation rules and posting limits and record them, dated, in `docs/sources.md`; verify the entries exist before any client code
- [ ] 6.2 Build `/announce.json` from the export: changes from the last seven days and each claim's anniversary sentence, empty in a preview build; verify tests for a recent change, an old change, a first status, a claim under a year old, and the neutral check on every text
- [ ] 6.3 Add the daily scheduled run: delete counts past their age, then choose what is due and not yet announced, changes first, four at most; verify Worker tests with a fixed date for the cap, the order, no repeat after a second run, and deletion at 91 and 401 days
- [ ] 6.4 Add the Bluesky client (session, card upload, post with link) behind its two secrets; verify tests against recorded responses, including a refusal that is not retried
- [ ] 6.5 Add the Mastodon client behind its two secrets; verify tests against recorded responses, including a refusal that is not retried
- [ ] 6.6 Document the cron trigger, the four secrets and how to delete a post in `docs/deploy.md`, and add "announcement" to `GLOSSARY.md`; verify a deploy with no secrets posts nothing

## 7. Extension stores (gap 5)

- [ ] 7.1 Add a target that zips `extension/dist` for the Chrome Web Store; verify the archive's manifest version matches the build
- [ ] 7.2 Write the listing text, permission justifications and privacy declarations for both stores in `extension/store/`, from the privacy page's wording; verify each permission in the manifest has a justification
- [ ] 7.3 Read the two store addresses from the environment and link them from the home and method pages only when set; verify site tests with none, one and both set
- [ ] 7.4 The operator submits to the Chrome Web Store and App Store Connect and sets the store addresses at deployment; verify the live home page links to each published listing

## 8. Older headlines (gap 1)

- [ ] 8.1 Gather about 120 candidates first reported 2010 to 2020, each carried by at least two widely read outlets, into `data/seed/claims-2010s.csv` with a notes file; verify `thenwhat claim import-csv` accepts the file and no row holds article text
- [ ] 8.2 Import the rows as pending and run `thenwhat prepare` over them; verify none stopped on an unexplained error and each has a draft, scored matches and a recorded status
- [ ] 8.3 Decide the pending items by the existing rules, recording any assistant decision `--as-assistant`; verify `thenwhat review list` is empty and no candidate marked as scored without the indication was approved by score alone
- [ ] 8.4 Export, regenerate what the export's tests require, and rebuild; verify `make check` passes and the count of published claims first reported before 2021 has risen
- [ ] 8.5 Check ten of the new claim pages by hand against their sources and note any rule that misled in the notes file; verify each note names the claim, the rule and the evidence

## 9. Together

- [ ] 9.1 With groups 2, 5 and 6 deployed, look up an untracked article on the live site, then run `make demand` and `make counts`; verify the miss and the page view appear and nothing about the request beyond address, page, day and referring host is stored

## Workflow follow-up

- The operator creates the Bluesky and Mastodon accounts and sets their secrets; posting starts on the next daily run.
- Archive the change once every group is merged, or split what remains into its own change first.
