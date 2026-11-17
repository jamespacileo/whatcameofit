# Tasks

- [x] 1 Controls a script works hold their place: `data-await` in place of `hidden` on the five home-page controls.
- [x] 2 Fallback faces with measured overrides for Figtree and Newsreader.
- [x] 3 Fetch ahead on pointing and focus.
- [ ] 4 Later, its own change: the landing page's HTML carries the first screen only.

Looked at and left: a page's scripts import shared modules two deep, in parallel. Rollup's `experimentalMinChunkSize` did not fold them, and the gain is one round trip.
