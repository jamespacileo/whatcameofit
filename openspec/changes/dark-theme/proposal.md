# Proposal

## Why

Readers arrive from a search engine or a shared link, often on a phone at night, with their device set to a dark appearance. The site was light only: a white page at full brightness under a device that asked for dark. The operator asked on 2026-11-16 for a dark theme that follows the device, and a control to choose light or dark.

## What Changes

- A dark theme: the same evidence digest under low light. The page is a deep neutral slate so the navy masthead, record band and footer keep their navy as a hue of their own; the accent is the lifted blue the masthead already uses. Amber still means "promised" and nothing else. No colour is given to any status.
- With no choice made, the site follows the device's appearance, and changes with it while a page is open. This works with no script.
- An appearance control at the end of the masthead steps through "as your device", then the look the page is not showing, then the other. The choice is kept in the reader's browser only and set before the first paint. It is drawn only where a script can act on it.
- Paper is always printed light. The embed stays light, because it sits inside other sites. The drawn extension popup stays light, because it must match the real popup.
- `DESIGN.md` records the dark palette and its contrast.

## Impact

- `site/src/styles/global.css`: theme tokens in one block, a dark block for a chosen theme and one for the device's, white lettering on navy as its own token.
- `site/src/layouts/Base.astro`, `site/src/scripts/theme.ts`: the control and the pre-paint choice.
- `site/src/pages/embed/[slug].astro`, `site/src/components/PopupDemo.astro`: held light.
- No change to the export, the pipeline or the extension.
