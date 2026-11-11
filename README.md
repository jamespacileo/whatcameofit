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

## Development

Needs [uv](https://docs.astral.sh/uv/), Node 22.23.4 or later and make.

```sh
make check
```

This runs ruff, ty, pytest and the site build. CI runs the same command.

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
