# thenwhat

<img src="site/public/mark.svg" width="56" height="56" alt="The site's mark: a magnifying glass over a capsule in two halves">

News reports medical "breakthroughs" that are rarely mentioned again. thenwhat tracks what happened afterwards: each claim gets a status derived from dated, sourced evidence in public registries. Items are approved by deterministic rules, every match shown carries its confidence score, and a wrong item is removed by archiving it.

`thenwhat` is the repository codename for [What came of it?](https://whatcameofit.com). The public site runs on Cloudflare; the curation pipeline and database stay local. GitHub tests each proposed change and deploys the committed snapshot from `main`.

## Setup

Needs Docker with Compose.

```sh
git clone <repository-url> thenwhat
cd thenwhat
cp .env.example .env
docker compose up --build -d
docker compose run --rm pipeline thenwhat --help
```

The site preview is at <http://localhost:4321>. The pipeline CLI runs inside the `pipeline` container:

```sh
docker compose run --rm pipeline thenwhat db-check
```

Stop the stack with `docker compose down`. Add `-v` to also delete the local database.

## Entering claims

A claim is one intervention for one indication. Adding a second claim for the same pair is refused and names the existing one. The commands below are shown without the `docker compose run --rm pipeline` prefix. The examples use a made-up claim, `example-enamel`, with made-up sources; it stays pending and is never published unless you approve it.

```sh
thenwhat claim add example-enamel-gel \
  --headline "Gel regrows tooth enamel" --vertical dental-regeneration \
  --intervention "Enamel gel" --indication "enamel loss"
thenwhat article add example-enamel-gel --url https://example.org/article \
  --outlet "Example News" --title "Gel regrows enamel" --published 2019-08-30
thenwhat promise add example-enamel-gel --article-url https://example.org/article \
  --text "human trials within five years"
thenwhat claim rename-slug example-enamel-gel example-enamel
```

A promise's date is read from its text: a span of years counts from the article date, a single year means 31 December of that year, and anything else gets no date. Pass `--date YYYY-MM-DD` to set it yourself. A slug cannot change once its claim has been published.

### Drafting from an article

Needs `CONTACT_EMAIL`, `LLM_MODEL`, the two price settings and the provider's key in `.env`.

```sh
thenwhat extract new https://example.org/other-article --slug example-draft \
  --vertical dental-regeneration --outlet "Example News" --title "Another report" \
  --published 2020-01-15
thenwhat extract article example-enamel --article-url https://example.org/article
thenwhat claim edit example-enamel --headline "Corrected headline"
```

`extract new` drafts a claim from the article. With `APPROVE_DRAFTS_BY_RULE` on (the default) the draft is approved by rule when its intervention is a name and rejected otherwise; with it off the draft stays pending. `extract article` adds entities, the paper and promises to a claim that is still pending. If the site's robots.txt forbids fetching, or the page is gone with no archived copy, the command says so: run it again with `--paste` and pipe the text in. Article text is used for the one call and never stored.

Model calls stop for the month once the recorded cost reaches `LLM_MONTHLY_BUDGET_USD`.

### Entities and registry matches

```sh
thenwhat entity synonym example-enamel "Enamel gel" "EG-1"
thenwhat entity add example-enamel --type paper --name "Paper title" --doi 10.1000/example
thenwhat entity origin-paper example-enamel "Paper title"
thenwhat resolve example-enamel
```

`resolve` searches ClinicalTrials.gov for the intervention under every name it has, looks up each paper's DOI at Crossref, and stores every hit as a candidate match with a score. A trial scores as a match only when it tests the intervention for the claim's indication; the same intervention in another condition scores low and is labelled. A broad name (more than 100 trials) is searched within the indication, and a name that is still broad there contributes nothing. The score orders the review queue, and a candidate scored under `MATCH_REJECT_BELOW` (0.05) is rejected by rule so it does not wait for you; `review list --by-rule` shows those, and you can approve any of them. A trial candidate scored at or above `MATCH_ACCEPT_ABOVE` (0.8) for the claim's indication is approved by rule; the rest wait for you. It also suggests the stage of evidence at announcement, which stays unset until you confirm it. Compound names change over time, so add synonyms before resolving. `resolve --rescore` scores pending candidates again.

`resolve` then searches OpenAlex for papers about the intervention and the indication, under each name and search phrase, and keeps up to twenty per claim as related papers. Each is scored, carries the reasons found by rule (named in the title, indication named, from an institution the article named, published by the first report), and is approved by rule at or above `MATCH_ACCEPT_ABOVE`, with or without a reason. A related paper is never an evidence event and never changes the status. A registry number an approved paper states becomes a trial candidate, and an approved paper that is confidently the one first reported on becomes the origin paper. Institutions and companies are looked up in ROR; people never are. `resolve --rescore` also scores the pending related papers again and brings their reasons up to date; it reads each paper by its identifier, which spends none of the day's searches. Paper search needs `OPENALEX_API_KEY` and is off without it. Related papers and organisations are not in the export yet.

`thenwhat entity people` lists every stored person with their claim. Only researchers belong: remove anyone else with `thenwhat entity delete-people ID...`.

### Evidence

```sh
thenwhat fetch example-enamel
thenwhat event add example-enamel --type trial_registered --date 2024-09-01 \
  --source-url https://example.org/registry/ID123 --source-name "Registry name" \
  --id ID123 --phase phase_1 --summary "Phase 1 trial registered."
thenwhat event add example-enamel --type regulatory_decision --date 2026-03-01 \
  --source-url https://example.org/notice --outcome approved --summary "Regulator approved it."
```

`fetch` reads the registries for the claim's approved matches only. Each trial gives up to four events from the dated fields of its current record: registered, started, a current end state, and results posted. Papers that cite the origin paper become follow-up events when they share an author with it or name the intervention. Retraction notices become retraction events. Fetching again records nothing twice.

Trial events from an approved match are approved by rule. A follow-up paper is approved by rule when its confidence reaches `REVIEW_CONFIDENCE_THRESHOLD`, and waits for review otherwise. Events entered by hand always wait for review. Set `REVIEW_CONFIDENCE_THRESHOLD` above 1 to review everything yourself.

Use `event add` for what no client covers yet: approvals, company events, and trials in registries other than ClinicalTrials.gov. A trial event needs `--id` and `--phase`; a status change needs `--state` (and a `started` event is what moves a claim to its phase); a regulatory decision needs `--outcome`.

### Review

Whatever the rules did not decide waits in one queue: draft claims, candidate matches, follow-up papers below the confidence threshold and events entered by hand. An approved item is published without waiting for you; `thenwhat archive <slug> --reason` takes a claim down.

```sh
thenwhat review list
thenwhat review list --claim example-enamel --kind event
thenwhat review approve event EVENT_ID
thenwhat review reject event OTHER_EVENT_ID
thenwhat review stage example-enamel animal
thenwhat review flag-failure example-enamel --trial ID123 --event EVENT_ID \
  --source-url https://example.org/results
```

Replace `EVENT_ID` with an id that `review list` shows. `review list` shows each item's kind and id, what it asserts, its source link and its score. Use the kind and id to approve or reject. A rejected item is kept, so it is never proposed again. `approve` and `reject` also change an earlier decision, including an approval made by rule.

For many claims at once, one command does the reading, searching and fetching, several claims side by side, and says how long each step took:

```sh
thenwhat prepare --pending              # every claim awaiting review
thenwhat prepare claim-one claim-two    # or named claims
```

Then review. `review list` shows what each registry record says, so most candidates can be judged without opening the link. Several items can be decided at once:

```sh
thenwhat review approve match 12 13 14
thenwhat review reject match --claim example-enamel --below 0.1
thenwhat review approve match --claim example-enamel --at-least 0.9
```

The order of work for one claim:

1. Approve the draft claim (`review approve claim ID`) once its headline and summary are right. A claim with no summary cannot be approved.
2. Run `resolve`, then approve or reject each candidate match. Rejecting a match also rejects the events read from it.
3. Run `fetch`, then approve or reject the follow-up papers.
4. Confirm the evidence stage with `review stage`.

The claim's status is derived again after every decision on an event. A claim becomes "failed" only through `review flag-failure`, which needs the trial, an approved event that reports the result, and a link showing the primary endpoint was missed. Posted results alone never mean failure.

Your decisions on matches and on the evidence stage are recorded as human labels against what the model suggested. They are the future test set for any model that takes over those choices.

### Publishing to the site

```sh
thenwhat export
docker compose restart site
```

`export` writes one JSON file holding approved claims and their approved events, and nothing else. The site is built from that file alone: `restart site` rebuilds it and serves the result at <http://localhost:4321>. A claim's slug is fixed from its first export.

To publish to the public address (Cloudflare), see [docs/deploy.md](docs/deploy.md):

```sh
SITE_URL=https://whatcameofit.com make deploy-check   # checks and builds, publishes nothing
SITE_URL=https://whatcameofit.com make deploy
```

A deploy is refused if the export is a preview.

### Looking up an article that is not tracked

```sh
thenwhat lookup https://example.org/news/some-article
```

Names the treatment and condition the article reports and lists the registry trials it is most likely about, likeliest first. The address of a post on Bluesky, Hacker News or a Mastodon server works too: the post and the article it links to are read together. Nothing is stored and nothing is reviewed: it is a list for you to check. See [docs/lookup.md](docs/lookup.md) for how well it does.

```sh
thenwhat outlets --save docs/outlets.md --articles docs/outlets-articles.csv
```

Asks for every tracked article once and records, per outlet, whether its site let the article be read and which signals its pages carry. Add `--with-lookup` to count how often a lookup finds an approved trial; that is slower and spends on the model. Four outlets are checked at a time (`--workers`). The last record is [docs/outlets.md](docs/outlets.md), with one row per address in [docs/outlets-articles.csv](docs/outlets-articles.csv).

### The seed claim

`docker compose up` loads `data/seed/tooth-regrowth-usag1.json` when its claim is not in the database yet, so a fresh checkout shows one real claim page. The seed was compiled from the primary sources it links and has not been reviewed by a person; its decisions are recorded as made by the seed loader, not by you. Check it before any public launch.

`thenwhat icons` fetches each outlet's own icon, once per domain, for the site to show beside the outlet's name; the next `export` carries it. It needs `CONTACT_EMAIL` and honours each site's robots.txt (see `docs/sources.md`).

After changing the seed, regenerate the copy the site falls back on, then rerun `make check`:

```sh
docker compose run --rm -v "$PWD/site/data:/out" pipeline thenwhat export --out /out/seed-export.json
```

After changing what the export contains, regenerate its schema: `thenwhat export --write-schema site/export.schema.json`.

### Taking a claim down

`thenwhat archive <slug> --reason "why"` takes a published claim off the site from the next export: its address answers 410 with the date, and it leaves every feed, the sitemap, the lookup file and the data file. The reason stays in the database. `thenwhat unarchive <slug>` puts it back.

### CSV import

`thenwhat claim import-csv claims.csv` imports every row or none. Inside the container the file must be reachable, for example `docker compose run --rm -v "$PWD/data/seed:/seed" pipeline thenwhat claim import-csv /seed/claims.csv`.

A candidate list for the backfill is in `data/seed/claims.csv`: 25 dental regeneration claims first reported from 2015 to 2020, each with one source article that was fetched and checked. `data/seed/claims-notes.md` says how each row was checked, which points deserve a second look, and which leads were dropped. Importing it creates pending drafts only.

One row per source article. Rows that share a slug belong to one claim: the first defines it, later rows may leave the claim columns blank. Errors name the row, counting the header as row 1.

| Column | Required | Notes |
|---|---|---|
| `slug` | yes | Lowercase letters, digits and single hyphens, at most 60 characters. Must not exist yet. |
| `headline` | first row of a claim | |
| `vertical` | first row of a claim | Must be a configured vertical, for example `dental-regeneration`. |
| `intervention` | first row of a claim | |
| `indication` | first row of a claim | |
| `summary` | no | Your own words. Never article text. |
| `article_url` | yes | Starts with `http://` or `https://`. |
| `outlet` | yes | |
| `article_title` | yes | |
| `published_date` | yes | `YYYY-MM-DD` |
| `promise` | no | The promised timeline as worded, for example `by 2025`. |
| `promise_date` | no | `YYYY-MM-DD`. Overrides the date read from `promise`. |

## Development

Needs [uv](https://docs.astral.sh/uv/), Node 22.23.4 or later, make and Docker.

```sh
make check
```

This runs ruff, ty, pytest, the site's tests, the site build and the extension's tests and build. CI runs the same command. The tests start the Compose database and use a throwaway `thenwhat_test` database in it, which is dropped and rebuilt from the migrations on every run.

Database migrations live in `pipeline/migrations` and are applied each time the `pipeline` container starts. After changing a model, generate a migration with the database running:

```sh
cd pipeline
DATABASE_URL=postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:5433/thenwhat uv run alembic revision --autogenerate -m "describe the change"
```

## Repository

| Path | Contents |
|---|---|
| `pipeline/` | Python pipeline and CLI |
| `site/` | Astro static site, built from the pipeline's JSON export |
| `extension/` | Browser extension for Chrome and Safari |
| `video/` | Remotion project for explainer videos |
| `data/seed/` | Seed claims |
| `scripts/` | Operator helper scripts |
| `openspec/` | Specifications and the active change |
| `docs/` | Architecture decisions and data source notes |
| `SPEC.md` | Original product specification |
| `GLOSSARY.md` | Domain terms |

## Disclaimer

thenwhat gives no medical advice. A registered clinical trial is not a treatment option.

## Licence

Code: MIT, see `LICENSE`. Published dataset: CC BY 4.0, see `LICENSE-DATA`.
