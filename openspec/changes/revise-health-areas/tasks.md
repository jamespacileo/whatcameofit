# Tasks

## 1. Before starting

- [x] 1.1 Read the HRCS conditions of use (hrcsonline.net/getting-started/conditions-of-use/) and confirm that keeping category names in private pipeline configuration is allowed; verify the finding and the date are noted in `docs/sources.md`
- [x] 1.2 Check which claims the operator's local database holds that are not in `data/seed/`, including any added by `backfill-dental-regeneration`; verify the list is in this change's design under the migration risk, or that the list is empty

## 2. The tree in configuration

- [x] 2.1 Rewrite `claims/verticals.py`:
  - the 16 groups with their HRCS anchors;
  - each group's general vertical, plus `dementia` and `gum-disease`;
  - an empty `RETIRED_VERTICALS`.

  Verify `thenwhat claim add --vertical pain` is refused and lists the new verticals.
- [x] 2.2 Add a configuration check covering every group anchored, every non-exempt HRCS category covered, every vertical with a group, and every group with its general vertical. Run it in `make check`, and verify one passing test plus one test per failure named in the `health-areas` spec.
- [x] 2.3 Update `GLOSSARY.md` so Group says every vertical has exactly one group, and add Approach and General vertical; verify the terms match the spec wording.

## 3. Approach

- [x] 3.1 Add the approach codes to configuration, a nullable `claim.approach` column, and migration `0006`; verify `alembic upgrade head` and `downgrade -1` both run against the test database.
- [x] 3.2 Accept `--approach` in `claim add` and `claim edit`, and an optional `approach` column in `import-csv`. Verify with one success and one refusal per command, including an all-or-nothing CSV refusal for an unknown code.
- [x] 3.3 Export the approach code, then regenerate `site/export.schema.json`; verify `test_export` passes.
- [ ] 3.4 Add the site's label for each approach code and show it on the claim page, and make the build fail on a code with no label. Verify by building the site, and by checking that a test export with an unknown code fails the build.

## 4. Refiling the seed claims

- [x] 4.1 Refile `data/seed/claims.csv`, `claims-recent.csv` and `tooth-regrowth-usag1.json` by the table in design.md, and give each claim an approach. Note any judgement call in `claims-notes.md` or `claims-recent-notes.md`. Verify `import-csv` accepts both files into a scratch database.
- [x] 4.2 In migration `0006`, map old verticals on existing rows by the design's rules, and abort with a list of any claim it cannot place. Verify one test that refiles a `pain` claim and one that aborts on an unplaceable claim.
- [x] 4.3 Regenerate `site/data/seed-export.json`; verify `make check` passes.
- [ ] 4.4 Remove the `dental-regeneration` special case from `TopicChip.astro`, moving its icon to `mouth-and-teeth` if it is kept; verify the topics page builds with the new groups and lists only groups that have claims.

## 5. Suggesting a group from MeSH

- [ ] 5.1 Write the pure MeSH-to-group function and its fixed table, ignoring broad headings. Verify tests against the recorded autism fixture (Mental Disorders → `mental-health`), against one new recorded fixture that maps to two groups, and against one with no usable term.
- [ ] 5.2 Show the suggestion, with its MeSH term, in `thenwhat prepare` output and in the review queue's claim line; verify one CLI test shows it and confirms the claim's vertical is unchanged.

## 6. Redirects after launch

- [ ] 6.1 Export `RETIRED_VERTICALS`, write a `_redirects` file at build time, and make `make deploy` record the topic slugs it publishes in `site/data/published-topics.json`. Verify that a build with a recorded slug that is neither current nor retired fails, and that a retired one produces a 301 line.
- [ ] 6.2 Document the retire-a-slug steps in `docs/deploy.md`; verify the steps run as written against a scratch build.

## 7. Integration

- [ ] 7.1 Run `make check` and build the site from the refiled seed export; verify every claim page shows its topic, and that the topics page lists 16 or fewer groups with no "Other topics" section.

## Workflow follow-up

- Archive the change once the operator has reviewed the refiled claims.
