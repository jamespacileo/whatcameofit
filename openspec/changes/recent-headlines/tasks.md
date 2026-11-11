# Tasks

## 1. Home page and topics

- [x] 1.1 List the ten newest reports of published claims on the home page, each title quoted with its outlet, date and status; verify the site test "Home lists the newest reports" passes
- [x] 1.2 List a topic in menus and lists only when it has a published claim; verify the site test "Vertical with no published claims" passes and the empty topic's page still builds
- [x] 1.3 Add the thirteen new topics to the configured set and regenerate `site/data/seed-export.json`; verify `make check` passes
- [x] 1.4 Look at the built home page at desktop and phone widths; verify nothing overflows and the outlet link is a full-size target
- [x] 1.5 Give each configured topic a group, carry it in the export and list the topic directory under groups; verify the site tests "Topics with groups" and "No topic has a group" pass
- [x] 1.6 Fetch one icon per outlet domain with `thenwhat icons` (robots.txt, contact User-Agent, size cap, fetch time), carry it in the export and show it in place of the letter tile; verify `make check` passes, the site test "Offline build" still passes and the seed claim's page shows its outlet's icon

## 2. Candidate list

- [x] 2.1 Collect claims reported between 2026-08-11 and 2026-11-11 into `data/seed/claims-recent.csv`, with the method and open points in `data/seed/claims-recent-notes.md`; verify every URL returns 200 and shows the recorded title and date
- [x] 2.2 Verify `thenwhat claim import-csv` accepts the file against a scratch database
- [ ] 2.3 The operator reads `data/seed/claims-recent-notes.md` and removes or corrects any row they do not want

## 3. Run and review

Needs the `.env` settings named in `backfill-dental-regeneration` task 1.1.

- [ ] 3.1 Import the candidates, then run `extract article`, `resolve` and `fetch` for each claim; verify none stopped on an error that is still unexplained
  - 2026-11-11: all 46 imported and drafted (5 articles could not be read: robots.txt or page would not load). 38 searched, fetched and decided by the assistant for the local preview. 8 broad-name claims still to finish searching. See `data/seed/claims-recent-notes.md`.
- [ ] 3.2 The operator reviews everything pending for these claims; verify `thenwhat review list` reports an empty queue
- [ ] 3.3 Export and rebuild the site; verify the home page lists the newest reports and each new topic with a published claim appears under Topics
- [ ] 3.4 Check five of the new claim pages by hand against their sources, including two whose headline says more than the status; verify the page reads as the outlet's words beside the site's status
