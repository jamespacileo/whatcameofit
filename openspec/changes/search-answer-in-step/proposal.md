# Proposal

## Why

A critique of the home page's search on 2026-11-17 (`.impeccable/critique/`, run on the operator's request) found that the box and its answer fall out of step. The words to try, the tally and the example stayed between the box and its answer. A field emptied by Escape or its cross kept its answer and the words in the address. Back left the page instead of returning to the search before. A search that could not be read told the reader to type in the box that had just failed. An article the site does not track was offered a date to come back on only after a registry search. On a wide screen nothing lasting said that the box takes a link, or that a pasted link is compared in the browser. The operator asked for all of it to be fixed.

## What Changes

- Once the box has answered, the words to try, the tally and the example under it are not drawn until the search is cleared.
- The line under the box that says where a search's answer is ends in a link that puts the reader on the answer's heading.
- A field emptied by its cross, by Escape or by deleting clears its answer and the words in the address.
- Each search looked up, and a search cleared, is a step in the browser's history: Back and Forward move between them and each is drawn again. Narrowing by topic still changes the address in place.
- A search or lookup that could not be read says so with "Try again", which asks the same question again, and the line on topics. It no longer says a treatment's name can be typed.
- An article the site does not track is offered "Check again later" at once, with or without a registry search.
- Under the field, on every page with the box, one line says that a pasted link is compared in the browser and where it is sent.
- Close claims none of which a person has checked say so once under the list, not under every one.
- The button that asks for a registry search is described by the line that says what it sends.
- In a tracked answer, a two-line status, its place on the path and its no-signal note each stand on a line of their own.

## Impact

- `site/src/components/Lookup.astro`, `site/src/styles/global.css`, `site/tests/home-search.test.mjs`, `site/tests/lookup-component.test.mjs`, `DESIGN.md`.
- No new data and no new request. The pasted address still never enters the page's address.
