# Tasks

## 1. Pipeline

- [x] 1.1 Add the assistant decider and migration 0002; verify the review tests for an assistant decision pass and no human label is written
- [x] 1.2 Leave assistant-decided claims out of the export unless a preview is asked for, and mark each claim with whether a person checked it; verify the four export tests pass
- [x] 1.3 Add `--as-assistant` to the review commands and `--preview` to export; verify the command test passes and the schema, seed export and fixture are regenerated

## 2. Site and extension

- [x] 2.1 Show the preview band and noindex tag on a preview build and the unchecked note on unchecked claims; verify the site test "Preview build" passes
- [x] 2.2 Carry the unchecked note in `lookup.json` and show it in the extension popup; verify the lookup assertions pass

## 3. Use

- [x] 3.1 Superseded on 2026-11-13 by change `auto-publish` (`docs/adr/0001-publish-by-rule-archive-to-remove.md`): a normal export now contains assistant-decided claims, each marked as not checked by a person, so no claim waits for the operator. An operator who repeats a decision without `--as-assistant` makes it their own, and the claim counts as checked once no assistant decision stands on it.
