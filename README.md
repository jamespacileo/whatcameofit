# thenwhat

News reports medical "breakthroughs" that are rarely mentioned again. thenwhat tracks what happened afterwards: each claim gets a status derived from dated, sourced evidence in public registries, reviewed by a human before it is published.

`thenwhat` is a working codename. The project is in Phase 1 (hand-curated backfill of dental regeneration claims) and runs locally only.

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

A claim is one intervention for one indication. Adding a second claim for the same pair is refused and names the existing one. The commands below are shown without the `docker compose run --rm pipeline` prefix.

```sh
thenwhat claim add tooth-regrowth-usag1 \
  --headline "Antibody regrows teeth in mice" --vertical dental-regeneration \
  --intervention "USAG-1 antibody" --indication "tooth agenesis"
thenwhat article add tooth-regrowth-usag1 --url https://example.org/article \
  --outlet "Example News" --title "Mice regrow teeth" --published 2018-03-10
thenwhat promise add tooth-regrowth-usag1 --article-url https://example.org/article \
  --text "human trials within five years"
thenwhat claim rename-slug tooth-regrowth-usag1 tooth-regrowth
```

A promise's date is read from its text: a span of years counts from the article date, a single year means 31 December of that year, and anything else gets no date. Pass `--date YYYY-MM-DD` to set it yourself. A slug cannot change once its claim has been published.

### CSV import

`thenwhat claim import-csv claims.csv` imports every row or none. Inside the container the file must be reachable, for example `docker compose run --rm -v "$PWD/data/seed:/seed" pipeline thenwhat claim import-csv /seed/claims.csv`.

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

This runs ruff, ty, pytest and the site build. CI runs the same command. The tests start the Compose database and use a throwaway `thenwhat_test` database in it, which is dropped and rebuilt from the migrations on every run.

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
| `data/seed/` | Seed claims |
| `openspec/` | Specifications and the active change |
| `docs/` | Architecture decisions and data source notes |
| `SPEC.md` | Original product specification |
| `GLOSSARY.md` | Domain terms |

## Disclaimer

thenwhat gives no medical advice. A registered clinical trial is not a treatment option.

## Licence

Code: MIT, see `LICENSE`. Published dataset: CC BY 4.0, see `LICENSE-DATA`.
