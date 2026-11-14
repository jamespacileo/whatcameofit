# thenwhat site

Static Astro site. Its only input is the pipeline's JSON export: `data/export.json` when it exists, otherwise the checked-in `data/seed-export.json`, so a fresh checkout builds. `EXPORT_FILE` names another export and overrides both.

```sh
npm install
npm test          # the site's tests
npm run build     # writes dist/
npm run preview   # serves dist/ on http://localhost:4321
```

Publishing is described in `../docs/deploy.md`.
