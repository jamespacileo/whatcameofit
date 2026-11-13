# Release polish

## Why

Hands-on release testing found that a delayed article lookup could replace a newer answer on the home page, live website candidates omitted their match confidence, and saved extension checks could imply the registry was searched when it was not. The reminder beneath live candidates also incorrectly said nothing was on record.

## What changes

- Ignore obsolete article lookup successes and failures.
- Put each live trial's confidence beside its title, with its explanation and limitations collapsed using the existing match layout.
- Use neutral reminder copy regardless of whether candidates were found.
- Keep the generated search limitation in browser-only recent checks; give older entries a neutral fallback.
- Package the extension correction as 0.9.1. No permissions, providers, storage destinations or usage limits change.

## Scope

Home-page results and saved extension checks only. Chrome registration remains parked. The submitted Safari 0.9.0 build remains in Apple's review queue.
