# Proposal

## Why

The critique of 2026-11-17 counted 18 font sizes in sight on one claim page, seven of them within 1.5px of each other (13.26px to 14.96px), and 25 raw `rem` sizes across 190 declarations in the shared stylesheet, with `0.9rem` written 34 times and `0.85rem` 26 times beside two size tokens used 14 times. Roles that should look the same (a note, a label, a table cell) differed by fractions of a pixel from one section to the next. The operator asked for the type scale as the next step of the sheet work.

## What Changes

- Seven steps for running text (`--text-micro` 0.72rem, `--text-xs` 0.78rem, `--text-s` 0.85rem, `--text-m` 0.92rem, `--text-body` 1rem, `--text-l` 1.08rem, `--text-xl` 1.2rem) and three named roles (`--text-wordmark` 1.25rem, `--text-heading` 1.35rem, `--text-status` 1.5rem), defined once.
- Every `font-size` in `site/src/styles/global.css` is one of them, a title's `clamp`, or `inherit`. Each raw size moved to its nearest step: no size moved by more than 1px. `--label-size` and `--note-size` are both `--text-s`.
- A test fails on a font size outside the scale.

On the sample claim page the sizes in sight go from 18 to 9.

This touches every page that uses the shared stylesheet, by at most 1px a role. Sizes written inside a component's or a page's own styles (89 declarations: the lookup, the day list, the drawn popup, the about page and others) are not changed.

## Capabilities

### Modified Capabilities

- `site-publishing`: the shared stylesheet's font sizes come from one scale.

## Impact

- `site/src/styles/global.css`, `site/tests/primitives.test.mjs`, `DESIGN.md`.
