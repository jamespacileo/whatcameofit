# Tasks

## 1. Record the change

- [x] 1.1 Proposal, design and spec deltas
- [x] 1.2 `GLOSSARY.md`: merged claim, moved address; `CLAUDE.md` working rules

## 2. Pipeline

- [x] 2.1 Migration `0030`: `claim.merged_into_id`, `claim.registry_search_due_at`, table `claim_change`
- [x] 2.2 `thenwhat claim merge`, one success and one refusal
- [x] 2.3 `thenwhat entity rename`, with `--old-is-description` and `--reslug`, one success and one refusal
- [x] 2.4 A merged claim answers no duplicate check; a former slug stays taken; `unarchive` refuses a merged claim
- [x] 2.5 `thenwhat prepare --due`; a registry search that succeeds clears the mark
- [x] 2.6 Export lists moved addresses; schema regenerated
- [x] 2.7 Review of PR 275: a hold for audit follows the merged content; a lead's read fields are left alone; a merge needs a stored sign of one treatment or `--same-treatment-accepted`; every moved row is recorded; `thenwhat claim unmerge`

## 3. Site

- [x] 3.1 Build writes moved addresses to `dist/gone.json`; the Worker answers them with a permanent redirect

## 4. Apply (operator's assistant, after review)

- [ ] 4.1 Apply migration `0030` to the working database
- [ ] 4.2 Merge the three duplicate pairs found on 2026-11-16
- [ ] 4.3 Rename and unarchive the 29 claims archived for their intervention's name
- [ ] 4.4 `thenwhat prepare --due`, check the records each merge listed, export and deploy

## 5. Left for later

- [ ] 5.1 Browser extension: a followed claim that was merged or re-slugged follows its new address
- [ ] 5.3 `prepare` decides by the rule for drafts any pending claim a `new_claim` lead points at: after a merge into a pending, operator-entered claim that lead points at the kept claim. The outcome is held for audit, never published unheld
- [ ] 5.2 Compare a merged claim's articles with the kept claim's by address key (after `idempotent-runs-and-one-address` 5.1)
