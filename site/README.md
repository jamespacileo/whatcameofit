# thenwhat site

Static Astro site. Its only input is a bundle of pairs: the folder `PAIRS_BUNDLE` names, holding the lab's page files and their manifest (openspec `pairs-site`). `tests/bundle` is the small one the tests build, and `make site-build` uses it when none is named. A build given no bundle stops.

```sh
pnpm install
pnpm test         # the site's tests
PAIRS_BUNDLE=tests/bundle pnpm run build    # writes dist/
pnpm run preview   # serves dist/ on http://localhost:4321
```

Publishing is described in `../docs/deploy.md`.
