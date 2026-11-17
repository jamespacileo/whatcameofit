# thenwhat site

Static Astro site. Its only input is the pipeline's JSON export: `data/export.json` when it exists, otherwise the checked-in `data/seed-export.json`, so a fresh checkout builds. `EXPORT_FILE` names another export and overrides both.

```sh
pnpm install
pnpm test         # the site's tests
pnpm run build    # writes dist/
pnpm run preview   # serves dist/ on http://localhost:4321
```

Publishing is described in `../docs/deploy.md`.
