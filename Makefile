.PHONY: check lint types db-up test site-build

DB_PORT ?= 5433
# Tests drop and recreate this database, so its name must end in _test.
export TEST_DATABASE_URL ?= postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:$(DB_PORT)/thenwhat_test

# Everything CI runs. Needs Docker for the database; no internet access is
# needed once dependencies and the Postgres image are present.
check: lint types test site-build

lint:
	uv run --directory pipeline ruff check .
	uv run --directory pipeline ruff format --check .

types:
	uv run --directory pipeline ty check

db-up:
	docker compose up -d --wait db

# The round-trip test builds the site, so the site's dependencies must be installed.
test: db-up site/node_modules
	uv run --directory pipeline pytest -q

site/node_modules: site/package-lock.json
	npm --prefix site ci
	@touch site/node_modules

site-build: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build
