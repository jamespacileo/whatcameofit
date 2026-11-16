# Proposal

## Why

The operator asked on 2026-11-16 for two things, due now that the demo is over: a pipeline run that can be repeated with the same or partly the same data and either resumes or gives the same results, and every stored address of an article or post in one form, so that one article is not processed twice and a shortened or redirecting link is stored as where it leads.

Measured on the working database on 2026-11-16, read only (612,148 link leads, 741,623 shares, 1,897 source articles, 1,395 claims):

- **The stored keys are sound for what the key already knew.** Recomputing every lead's key from its address gave the stored key 612,148 times out of 612,148. `http` and `https`, `www.`, a trailing slash, a fragment, the listed tracking parameters and `bbc.co.uk` do not make a second lead: 91,222 leads are stored under an `http` address, 417,821 under `www.`, 177,011 with a trailing slash and 10,619 under `bbc.co.uk`, each folded into one key. The duplicates reported after the run are of other kinds.
- **5,756 leads are a second lead of an article that already has one** (4,773 articles). 5,367 differ by a tracking parameter the key did not know (`_r`, `mbid`, `WT.nav`, `pgtype`, an outlet's own `mod`, `single_page`, `tid`), 305 by an edition, text or renamed host (`uk.businessinsider.com`, `lite.cnn.com`, `motherboard.vice.com`, `x.com`, a stray dot), 84 by a doubled slash or the letter case of an escape.
- **Those duplicates were paid for.** In 4,353 of the 4,773 articles two or more leads were scored by triage: 5,313 scores bought twice. In 7 the page was read twice, and in 2 the two reads made two claims.
- **5 claims hold one article twice** under two address forms, and 38 articles are a source article of two claims (2 of them under different forms). `source_article` is unique on the claim and the address as written.
- **115 trials hold one news article twice** among their 44,166 article leads.
- **Shorteners and redirectors are rare in what was loaded**: 125 leads on outlets' own shorteners (`on.wsj.com` 74, `on.ft.com` 51), 3 `google.com/url` links, 68 `web.archive.org` copies that name the original address. None on `t.co`, `bit.ly`, `lnkd.in`, `news.google.com` or `apple.news`. That is 196 of 612,148 leads.

The audit of each step (design.md, "What a second run does today") found that loading, screening, triage, `audit clear` and the export already resume or repeat without spend, and three places where a second run pays again.

## What Changes

- **A stricter address key, in one shared form.** More tracking parameters, parameters that only one outlet uses to say how a reader arrived, editions and renamed hosts seen serving one article under two names, doubled slashes and the letter case of escapes. The pipeline's key and the site's and extension's article key change together and are tested on one cases file, which now also lists addresses that must not share a key.
- **The key has a version, and a lead records the one it was keyed under.** `thenwhat backfill rekey-links` brings stored leads to the current form and merges leads that are one article, keeping the one that was scored or read. It asks no source and no model, and makes no lead due again for a step that does. Loading and the link steps are refused until it has run. **Built, not run on the working database.**
- **A rerun pays for nothing twice**: the requirement, per step, with what each step does today.
- **Unfurling for a fixed list of shorteners and redirectors**, never a news page. Addresses that name where they lead (an archive copy, a redirect parameter) are unfurled by reading the address alone. A shortener is asked for its redirect only, by the site's bounded redirect reader, under the terms in `docs/sources.md`. **Designed, not built**: it waits for the operator's decisions below.
- **One article once per claim, by key.** Designed, not built: the code that adds a source article is being changed by other work.

Not in this change:

- Stored results reused across steps and writers (`work-reuse-and-metrics`), which this change leaves as designed there. This change makes the key those results will be found under the same for every form of an address.
- Any change to how a claim is approved, audited or given a status, or to the export's shape.
- Reading one syndicated story once across different outlets: two outlets' pages are two addresses.

## Capabilities

### New Capabilities

- `address-identity`: which addresses are one article, the version of that rule, how stored leads follow it, and how a shortened or redirecting address is unfurled. It refines "Addresses are compared as the site compares them" of `link-leads` (change `social-link-backfill`), which stays true.
- `rerun-safety`: what a second run of each step with the same or overlapping input does.

## Impact

- `pipeline/src/thenwhat/backfill/address.py`, `site/src/lib/article-key.mjs` (copied into the extension at build), `site/tests/fixtures/article-key-cases.json`.
- New: `pipeline/src/thenwhat/backfill/link_rekey.py`, `thenwhat backfill rekey-links`, migration `0027` (one column, `link_lead.url_key_version`, default 1; nothing is rewritten by the migration).
- The site's `lookup.json` and the extension match more forms of a tracked article's address. No stored data of the site changes.
- After this is merged and before the next load: `alembic upgrade head`, then `thenwhat backfill rekey-links` to look and `--apply` to do it (design.md, "Bringing the working database up to date").
