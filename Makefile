.PHONY: check lint types db-up test site-test site-build extension-test extension extension-safari public-export publish-data deploy-check deploy deploy-ci-check deploy-ci lookup-dev

DB_PORT ?= 5433
export SITE_URL ?= https://whatcameofit.com
# Tests drop and recreate this database, so its name must end in _test.
export TEST_DATABASE_URL ?= postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:$(DB_PORT)/thenwhat_test

# Everything CI runs. Needs Docker for the database; no internet access is
# needed once dependencies and the Postgres image are present.
check: lint types test site-test site-build extension-test

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

site-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site test

site-build: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build

# The browser extension: plain JavaScript, tested with Node's own runner, then built.
extension-test: site/node_modules
	node --test extension/tests/
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

# A normal export from the running pipeline: reviewed claims only, never a preview,
# whatever EXPORT_PREVIEW is set to locally.
public-export:
	docker compose exec -T pipeline sh -c 'EXPORT_PREVIEW=0 thenwhat export --out /tmp/public-export.json >&2 && cat /tmp/public-export.json' > $(PUBLIC_EXPORT).tmp
	mv $(PUBLIC_EXPORT).tmp $(PUBLIC_EXPORT)

# Review locally, then commit this snapshot. GitHub never reads the private database.
publish-data: public-export
	node site/scripts/stage-public-export.mjs $(PUBLIC_EXPORT) site/data/published-export.json

deploy-ci-check: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/deploy.mjs --dry-run

deploy-ci: site/node_modules
	EXPORT_FILE=data/published-export.json node site/scripts/deploy.mjs

# Everything a deployment does except publishing: the checks, a public build, and
# Wrangler's own dry run.
deploy-check: site/node_modules public-export
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs --dry-run

# Publish to Cloudflare at SITE_URL's domain. Refuses a preview export, a claim not
# checked by a person, and a local address.
deploy: site/node_modules public-export
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs

# The site with its registry search, on this machine only: http://localhost:8787
# Reads the model settings from .env and builds from site/data/export.json if there is one.
lookup-dev: site/node_modules
	node site/scripts/dev-vars.mjs
	LOOKUP_URL=/api/lookup ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build
	cd site && wrangler dev --port 8787
