.PHONY: setup smoke-research check lint types db-up test scripts-test site-test site-build extension-test extension extension-safari public-export publish-data deploy-check deploy deploy-ci-check deploy-ci pr-preview-check pr-preview-state pr-preview lookup-dev

DB_PORT ?= 5433
export SITE_URL ?= https://whatcameofit.com
# Tests drop and recreate this database, so its name must end in _test.
export TEST_DATABASE_URL ?= postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:$(DB_PORT)/thenwhat_test

# Everything CI runs. Needs Docker for the database; no internet access is
# needed once dependencies and the Postgres image are present.
check: lint types test scripts-test site-test site-build extension-test

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

# The daily job's script, against a stand-in for the pipeline: no database, no network.
scripts-test:
	sh -n scripts/daily-run.sh
	sh -n scripts/worktree-setup.sh
	@if command -v shellcheck >/dev/null; then shellcheck scripts/daily-run.sh scripts/tests/daily-run.test.sh; fi
	sh scripts/tests/daily-run.test.sh

# Cloned from the main checkout where the lockfile is the same (a new worktree, in
# seconds), else installed with npm ci. See scripts/worktree-setup.sh.
site/node_modules: site/package-lock.json
	sh scripts/worktree-setup.sh site

# Everything a new checkout or worktree needs before `make check`.
setup:
	sh scripts/worktree-setup.sh

site-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site test

site-build: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build

# Live: reads each article in site/tests/fixtures/research/cases, asks the model, OpenAlex
# and ROR, and checks the report's paper is found. Costs a model call and up to five
# searches per case, so it is not part of `check`. `make smoke-research RECORD=1` rewrites
# the recorded answers the site tests replay.
smoke-research: site/node_modules
	node site/scripts/smoke-research.mjs $(if $(RECORD),--record)

# The browser extension: plain JavaScript, tested with Node's own runner, then built.
extension-test: site/node_modules
	node --test extension/tests/*.test.mjs
	node extension/build.mjs

# The extension as loaded in Chrome ("Load unpacked" on extension/dist).
extension: site/node_modules
	node extension/build.mjs

# Safari needs an app around the extension; see extension/safari.sh. Needs Xcode.
extension-safari: extension
	sh extension/safari.sh

# Publishing. See docs/deploy.md. SITE_URL must be the public address:
#   SITE_URL=https://example.org make deploy-check
PUBLIC_EXPORT := site/data/public-export.json

# A normal export from the running pipeline: every approved, unarchived claim.
# Outlets added since the last run are asked for their icon first; an outlet that
# cannot be reached does not stop the export.
public-export:
	-docker compose exec -T pipeline thenwhat icons >&2
	docker compose exec -T pipeline sh -c 'thenwhat export --out /tmp/public-export.json >&2 && cat /tmp/public-export.json' > $(PUBLIC_EXPORT).tmp
	mv $(PUBLIC_EXPORT).tmp $(PUBLIC_EXPORT)

# Review locally, then commit this snapshot. GitHub never reads the private database.
publish-data: public-export
	node site/scripts/stage-public-export.mjs $(PUBLIC_EXPORT) site/data/published-export.json site/data/published-topics.json

deploy-ci-check: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/deploy.mjs --dry-run

deploy-ci: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/deploy.mjs

# One pull request's copy of the site, on its own Worker thenwhat-pr-<number> at a
# workers.dev address. Never production. GitHub runs this for every pull request.
#   PR_NUMBER=12 make pr-preview-check
pr-preview-check: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/pr-preview.mjs --dry-run

# Whether the pull request's copy is already this commit's. Needs no dependencies.
pr-preview-state:
	EXPORT_FILE=data/published-export.json node site/scripts/pr-preview.mjs --state

pr-preview: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/pr-preview.mjs

# Everything a deployment does except publishing: the checks, a public build, and
# Wrangler's own dry run.
deploy-check: site/node_modules public-export
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs --dry-run

# Publish to Cloudflare at SITE_URL's domain. Refuses a preview export and a
# local address.
deploy: site/node_modules public-export
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs

# The site with its registry search, on this machine only: http://localhost:8787
# Reads the model settings from .env and builds from site/data/export.json if there is one.
lookup-dev: site/node_modules
	node site/scripts/dev-vars.mjs
	LOOKUP_URL=/api/lookup ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build
	cd site && wrangler dev --port 8787
