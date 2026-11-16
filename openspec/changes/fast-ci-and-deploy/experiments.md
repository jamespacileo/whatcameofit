# Experiments

The ledger `design.md` decision 5 asks for. One row per thing tried, kept or not. Figures are from GitHub's records of the named runs.

## Baseline, 2026-11-16

See `proposal.md`. Pull request preview published: p50 146 s, p90 174 s over 26 runs. One preview run in detail (43965293073, pull request 267's first):

| Step | Seconds |
| --- | --- |
| Set-up, checkout, Node | 8 |
| `npm ci` | 6 |
| Build: 2,142 card images | 76 |
| Build: everything else (2,557 pages, feeds, JSON) | 8 |
| Search index | 2 |
| Wrangler, 7,028 files to a new Worker | 45 |
| Comment | 2 |

A re-run of the same commit found no file to send and Wrangler took 7 s, so the build is reproducible and Cloudflare keeps files it has already been sent.

## Tried

| # | Step | Hypothesis | Predicted | Refuted if | Before | After | Kept |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | Build: card images | A drawn card kept under the hash of the renderer's input is read back instead of drawn | 76 s to under 5 s | Output files differ from a build without the store | 76 s | 4.3 s (2,142 cards read through their routes); two local builds, cold then warm, 0 of 7,042 files differ | Yes |
| P2 | Whole run, nothing changed | The published copy carries its key; a push with the same key builds and sends nothing | Under 15 s | A changed site file is passed over | 146 s | 11 s wall, 8 s job (run after `f1fdaa2`, a notes-only push) | Yes |
| P3 | `npm ci` | The installed dependencies restored whole, keyed by the lock file | 6 s to 3 s | Restore is slower than installing | 6 s | 2 s (130 MB) | Yes |
| P4 | CI rehearsal | The same card store, restored in `CI and deploy` | Rehearsal 94 s to under 30 s | No effect on a build with the registry search on | 107 s (cold, run 43969681619) | 19 s (run 43970304516); job 313 s to 200 s | Yes |

## Where a push that changes the site stands (run after `82ff46b`, 50 s wall)

| Step | Seconds | Class |
| --- | --- | --- |
| Waiting for a runner | 3 | waiting |
| Set-up, checkout | 2 | starting |
| State check | 2 | remote answer |
| Node | 3 (0 to 3 across runs) | starting |
| Restore dependencies, restore cards | 4 | moving bytes |
| Astro start and bundling | 3 | computing |
| Pages: 719 claim pages 5.1 s, 1,067 source pages 1.4 s, 708 embeds 0.7 s, feeds and JSON 1.5 s | 8.7 | computing |
| Cards read back through their routes | 4.3 | computing |
| Search index | 3.2 | computing |
| Build checks | 0.4 | computing |
| Wrangler: start 2 s, list and send 7 s, triggers 0.5 s | 9 | remote answer |
| Comment | 2 | remote answer |

## Verdict on the 20 s limit for previews, as of 2026-11-16

- **A push that changes nothing the site is made from: met.** 11 s, one run. Needs 20 runs to be judged by the spec's rule.
- **A push that changes the site: not met, 50 s.** Before anything is built, the job's start, the stores and Wrangler's own 9 s come to about 23 s. The limit cannot be met on a GitHub-hosted runner while the whole site is rebuilt and Wrangler sends it.
- **A new pull request's first preview: not measured warm.** It can read the stores only once a run on `main` has kept them, which happens after this pull request is merged.

What would lower the site-changing case, largest first, none tried:

| Option | Expected | Cost |
| --- | --- | --- |
| Build routes in four processes at once and merge the outputs | Pages and cards 13 s to about 5 s; run about 40 s | Every dynamic route must take its share of paths; a new route that forgets is built four times |
| Draw or copy the cards outside Astro, beside the page build | 4 s off | The card routes leave `src/pages`; the dev server needs another way to show them |
| A runner that stays warm (the operator's machine), with dependencies, stores and the last build in place | Start and restore 11 s to about 2 s, build about 3 times faster; run plausibly under 20 s | Pull request code runs at home with a Cloudflare token; needs the operator's decision and an ADR |
| An uploader that asks Cloudflare directly | Perhaps 2 s off Wrangler's 9 s | A second way to publish, to be kept in step with Wrangler |
