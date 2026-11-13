# Tasks

## 1. Record the decision

- [x] 1.1 Proposal, design and spec deltas
- [x] 1.2 ADR 0001: publish by rule, take down by archive
- [x] 1.3 Replace the review-gate lines in `CLAUDE.md`; update `GLOSSARY.md` and `PRODUCT.md`

## 2. Archive (PR B)

- [x] 2.1 Migration: `archived_at`, `archive_reason` on claims
- [x] 2.2 `thenwhat archive <slug> --reason` and `thenwhat unarchive <slug>`, one success and one refusal each
- [x] 2.3 Export leaves archived claims out and lists archived slugs; regenerate schema, seed export, fixture
- [x] 2.4 Build writes the archived list (`dist/gone.json`); Worker answers those addresses 410 with the short page. Page paths now run the Worker first (`site/wrangler.jsonc`); it hands every other request to the files
- [x] 2.5 Feeds, sitemap, `lookup.json` and the data file drop archived claims

## 3. Publish by rule (PR C)

- [x] 3.1 `MATCH_ACCEPT_ABOVE` in config and `.env.example`; rule approval for matches scored with the indication
- [x] 3.2 Rule decision for new drafts behind `APPROVE_DRAFTS_BY_RULE`: approved when the intervention is a name, else rejected and kept
- [x] 3.3 Follow-up paper events use the confidence threshold
- [x] 3.4 Export: drop the assistant-decision exclusion and the preview mode; carry match scores and reasons
- [x] 3.5 Claim page: confidence word and percentage on every match, reasons on demand, pending candidates listed
- [ ] 3.6 Correct the live-lookup confidence requirement when that change is archived

## 4. Source pages (PR C)

- [ ] 4.1 Migration and model for sources and their candidates
- [ ] 4.2 Export and schema
- [ ] 4.3 `/source/{outlet}-{slug}` page, sitemap entry, archivable
- [ ] 4.4 Extension and home lookup link to a source page when one exists

## 5. Publish (PR D)

- [x] 5.1 Regenerate `site/data/published-export.json`: 84 claims (83 not checked by a person), 119 status changes in the feeds. The deploy and staging checks no longer refuse unchecked claims
