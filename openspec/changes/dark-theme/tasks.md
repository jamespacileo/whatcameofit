# Tasks

## 1. Theme

- [x] 1.1 Gather the colour tokens into one block and add the dark values, for a chosen theme and for the device's, screen only. Verify: no light colour literal is left outside the token block, the outlet tile and the brand mark; text on the dark page is 4.5:1 or more.
- [x] 1.2 Give white lettering on the navy grounds and lettering on a filled blue control their own tokens, so neither inverts in the dark theme. Verify: masthead, record band, footer, pressed kind tab, trial columns head, search button, store controls and the data file button read in both themes.
- [x] 1.3 Hold the embed and the drawn popup light. Verify: the embed's computed colour scheme is light on a dark device.

## 2. Control

- [x] 2.1 Add the masthead control and `scripts/theme.ts`; set a stored choice before the first paint. Verify: a reload keeps the choice.
- [x] 2.2 Follow a device change live when no choice is stored. Verify: switching the emulated scheme changes an open page.
- [x] 2.3 After the critique of 2026-11-16: make the control a two-state switch whose press to the device's look clears the choice, announce the choice in a status line, apply another tab's choice without writing it back, and change colours in one frame. Verify: ten fast presses with a second tab open give one storage event per write and none after.

## 4. After the critique

- [x] 4.1 Raise the status card on the band (`--raised`), give the navy band its own hairline (`--on-navy-rule`), warm the dark amber, step the filled blue down (`--blue-fill`), dim the explainer video, and make the search box's lift show in dark. Verify: contrast probe of six pages in each theme finds no text under 4.5:1.

## 3. Record

- [x] 3.1 Record the dark palette in `DESIGN.md`.
- [x] 4.2 After the second critique of 2026-11-16: restore the dark status card's ring on the record band (`--band-card-rule`, none in light), raise `--raised` to `#202c40` with a soft drop, dim the explainer to 70% until started, and say in the switch's label when a kept look differs from the device. Verify: light card unchanged (white, no edge, no shadow); dark card ringed; muted text on it 6.4:1.
