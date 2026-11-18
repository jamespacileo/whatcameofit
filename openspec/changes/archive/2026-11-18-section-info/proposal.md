# Proposal

## Why

Each section of a claim page opened with a paragraph saying what the section holds, held to one line with "More" under it (`quiet-sheet`). The heading was followed by two lines of chrome before its first row. On 2026-11-17 the operator asked to explore another primitive: "a muted info icon next to a section heading that provides the description of section on hover", in a popover in the manner of a component library's.

## What Changes

- `FoldHead` takes an `about` slot. When it is given, a quiet info mark stands beside the heading and opens the note in a small panel, on hover, on a press and from the keyboard. The mark is named after its section.
- The panel is the site's own `Pop` (the browser's popover with anchor positioning), set as a compact card: a fixed width, even padding, the note's size, a short fade and growth as it arrives. No component library, framework or stylesheet is added.
- Five sections use it in place of their opening paragraph: "At a glance", "Trials on record", the registry records, "Papers on record", "Organisations named".
- The two sections whose note says the page is not advice ("The record in brief", "What the report said") keep their note in sight, whole, as `quiet-sheet` decided.
- On paper the note is printed whole under its heading.

## Capabilities

### Modified Capabilities

- `site-publishing`: where a claim page's section says what it holds.

## Impact

- `site/src/components/FoldHead.astro`, `Glance.astro`, `Organisations.astro`, `site/src/pages/[slug].astro`, `site/src/styles/global.css`, `site/tests/site.build-test.mjs`, `DESIGN.md`.
