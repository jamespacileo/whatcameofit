# Tasks

## 1. Measure and audit

- [x] 1.1 Count, read only, the leads that share an article by kind, the source articles that share one, and the leads on shorteners, redirectors and archives (design.md, "What was measured")
- [x] 1.2 Say what a second run of each step does, with the code (design.md, "What a second run does today")

## 2. A stricter key, in one form

- [x] 2.1 Tracking parameters, outlets' own parameters, listed hosts, dots, doubled slashes and escape case in `pipeline/src/thenwhat/backfill/address.py`
- [x] 2.2 The same in `site/src/lib/article-key.mjs`, which the extension's build copies
- [x] 2.3 The shared cases file extended, with pairs that must not share a key, read by the site's and the pipeline's tests
- [x] 2.4 `KEY_VERSION`, `link_lead.url_key_version` and migration `0027`

## 3. Stored leads follow the key

- [x] 3.1 `rekey` and `rekey_links`: new key, merge keeping the lead that came furthest, shares and labels moved
- [x] 3.2 Entries of steps that spend are kept; steps that ask nothing are due again
- [x] 3.3 `thenwhat backfill rekey-links`, reporting only unless `--apply`
- [x] 3.4 `load-links` and steps over link leads refused while a lead is behind
- [x] 3.5 Tests at the session seam and one success and one refusal for the command
- [x] 3.6 After review: screening's records move with a merge; the lead that drafted a claim is kept and claim pointers carried; `--apply` refused while the ledger shows a step at work; host dot removed before the YouTube rule; parameter order and path escaping made the same in both files
- [ ] 3.7 Operator: run it on the working database after the current run (design.md, "Bringing the working database up to date")
- [ ] 3.8 Operator: compare the two pairs of claims it names

## 4. Waiting for the operator's decisions (PR body)

- [ ] 4.1 An address that names where it leads has the key of that address (archive copies, `google.com/url`), in both key files and the cases file
- [ ] 4.2 Read robots.txt and terms of `on.wsj.com` and `on.ft.com`; note them in `docs/sources.md`
- [ ] 4.3 The unfurl step and its client: redirect only, fixed list, robots obeyed, one request a second per host
- [ ] 4.4 A lead follows its earliest share in address as well as title, so the order of loads changes nothing

## 5. Waiting for other work to land (`link_read.py`, `extract/`, `resolve/` are being changed elsewhere)

- [ ] 5.1 `source_article` and `article_lead` store the key, unique with the claim or trial; `find_article` and `add_article` compare by key
- [ ] 5.2 Merge the 5 pairs of source articles that are one article on one claim, and the 121 article leads too many
- [ ] 5.3 A failed read keeps what it paid for (with `work-reuse-and-metrics` 4.1 to 4.6)
- [ ] 5.4 A reader's "not now" is recorded with its time and respected by the next run
- [ ] 5.5 A failed scoring call withdraws only the candidates it did not score (`resolve/service.py`, `resolve/papers.py`, `resolve/named.py`)
- [ ] 5.6 The export's query for a claim's intervention entity states its order
