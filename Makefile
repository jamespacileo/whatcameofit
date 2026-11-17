.PHONY: setup smoke-research check lint types db-up test scripts-test store-test store-dev site-test site-build extension-test extension extension-safari public-export public-trials-listing publish-data deploy-check deploy deploy-ci-check deploy-ci pr-preview-check pr-preview-state pr-preview lookup-dev

DB_PORT ?= 5433
export SITE_URL ?= https://whatcameofit.com
# Tests drop and recreate this database, so its name must end in _test.
export TEST_DATABASE_URL ?= postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:$(DB_PORT)/thenwhat_test

# Everything CI runs. Needs Docker for the database; no internet access is
# needed once dependencies and the Postgres image are present.
check: lint types test scripts-test store-test site-test site-build extension-test

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

# The store's ingest service (store/ingest), driven over HTTP on D1's local engine: no
# Cloudflare account, no network, nothing deployed. The proof's scenarios, each token's
# scope, checksums, a replayed batch and the limits. Where the local engine cannot start,
# the tests are skipped and say why; in CI that is a failure, not a skip.
store/ingest/node_modules: store/ingest/pnpm-lock.yaml
	sh scripts/worktree-setup.sh store/ingest

store-test: store/ingest/node_modules
	pnpm --dir store/ingest test

# The ingest service on this machine only: http://localhost:8787. Tokens come from
# store/ingest/.dev.vars (see .dev.vars.example); the store is a file under .wrangler/.
store-dev: store/ingest/node_modules
	cd store/ingest && pnpm exec wrangler d1 migrations apply STORE --local && pnpm exec wrangler dev --local

# Linked from pnpm's shared store: seconds in a new worktree. See scripts/worktree-setup.sh.
site/node_modules: site/pnpm-lock.yaml
	sh scripts/worktree-setup.sh site

# Everything a new checkout or worktree needs before `make check`.
setup:
	sh scripts/worktree-setup.sh
	uv sync --directory pipeline

site-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site test

site-build: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site run build

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
# Hold the export the truth store gives to the one the database gives, and exit with 1
# when they differ (openspec truth-store, "The two exports are compared"). The cut-over
# waits on seven nights of this in a row. DATABASE_URL names the database, which is only
# read. With STORE_FILE (and STORE_PAYLOADS, the folder of its payload objects) the
# store's export is read from that snapshot; without it a store file is first made from
# the database through store/merge.sql, which shows the store can hold the records.
#   make export-compare
#   make export-compare ARGS="--every 5 --report /tmp/compare.json"
#   STORE_FILE=/path/store.db STORE_PAYLOADS=/path/objects make export-compare
.PHONY: export-compare
export-compare:
	uv run --directory pipeline thenwhat export-compare --store-sql $(CURDIR)/store $(ARGS)

# The cut-over of the store, one command and one order (store/ingest/scripts/cutover.mjs,
# docs/deploy.md): the build proved free of people, the jurisdiction read back, migrations,
# the store found empty, the bookmark noted, the hot file dumped, replayed here, loaded
# and held to its checks, the payload objects and the bulk file put in the bucket and the
# manifest read back. It stops at the first stage that fails and names it; each stage is
# timed; everything goes to a log in the build's folder.
#   make store-rehearsal STORE_DIR=/path/build                 the same on this machine, nothing sent
#   make store-cutover ENV=preview STORE_DIR=/path/build       ARGS="--dry-run" prints the plan
#   make store-cutover ENV=production STORE_DIR=/path/build CONFIRM=thenwhat-store
# ARGS: --replace (clear a preview store that is not empty), --skip-export (rehearsal only).
.PHONY: store-rehearsal store-cutover
store-rehearsal: store/ingest/node_modules
	@test -n "$(STORE_DIR)" || { echo "Name the build's folder with STORE_DIR."; exit 1; }
	node store/ingest/scripts/cutover.mjs --env local --store-dir $(STORE_DIR) $(ARGS)

store-cutover: store/ingest/node_modules
	@test -n "$(ENV)" -a -n "$(STORE_DIR)" || { echo "Name ENV (preview or production) and STORE_DIR."; exit 1; }
	@test "$(ENV)" != "local" || { echo "For this machine use make store-rehearsal."; exit 1; }
	node store/ingest/scripts/cutover.mjs --env $(ENV) --store-dir $(STORE_DIR) $(if $(CONFIRM),--confirm $(CONFIRM)) $(ARGS)

# A rehearsal of taking the site's export from the truth store (task 6.2). It reads the D1
# database and the bucket named, writes an export under STORE_REHEARSAL, holds it to the
# schema the site reads and to the checks a published snapshot must pass, and says how it
# compares with the committed snapshot. It changes nothing the site is built from.
#   STORE_D1=thenwhat-store-preview STORE_R2_BUCKET=thenwhat-payloads-preview make store-export-rehearsal
# Wrangler must be signed in (or CLOUDFLARE_API_TOKEN set) with read access to both.
STORE_REHEARSAL ?= $(CURDIR)/.store-rehearsal
.PHONY: store-export-rehearsal
store-export-rehearsal: store/ingest/node_modules
	@test -n "$(STORE_D1)" || { echo "Name the D1 database with STORE_D1."; exit 1; }
	mkdir -p $(STORE_REHEARSAL)
	uv run --directory pipeline thenwhat export --d1 $(STORE_D1) \
	  --store $(STORE_REHEARSAL)/store.db --payloads $(STORE_REHEARSAL)/objects \
	  --out $(STORE_REHEARSAL)/export.json
	uv run --directory pipeline python -m thenwhat.export.rehearsal \
	  $(STORE_REHEARSAL)/export.json $(CURDIR)/site/export.schema.json $(CURDIR)/site/data/published-export.json
	node site/scripts/stage-public-export.mjs $(STORE_REHEARSAL)/export.json $(STORE_REHEARSAL)/published-export.json

PUBLIC_EXPORT := site/data/public-export.json

# A normal export from the running pipeline: every approved, unarchived claim.
# Outlets added since the last run are asked for their icon first; an outlet that
# cannot be reached does not stop the export.
public-export:
	-docker compose exec -T pipeline thenwhat icons >&2
	docker compose exec -T pipeline sh -c 'thenwhat export --out /tmp/public-export.json >&2 && cat /tmp/public-export.json' > $(PUBLIC_EXPORT).tmp
	mv $(PUBLIC_EXPORT).tmp $(PUBLIC_EXPORT)

# The trial listing that stands beside the export: registry facts of one named set of
# stored trials, for the site's search and its page of an uncited trial. The site finds it
# by name beside the export it builds from. Sends no request.
PUBLIC_LISTING := site/data/public-trials-listing.json
TRIALS_SET ?= active-since-2025

public-trials-listing:
	docker compose exec -T pipeline sh -c 'thenwhat trials-listing --set $(TRIALS_SET) --out /tmp/public-trials-listing.json >&2 && cat /tmp/public-trials-listing.json' > $(PUBLIC_LISTING).tmp
	mv $(PUBLIC_LISTING).tmp $(PUBLIC_LISTING)

# Review locally, then commit these snapshots. GitHub never reads the private database.
publish-data: public-export public-trials-listing
	node site/scripts/stage-public-export.mjs $(PUBLIC_EXPORT) site/data/published-export.json site/data/published-topics.json
	node site/scripts/stage-trials-listing.mjs $(PUBLIC_LISTING) site/data/published-trials-listing.json site/data/published-export.json

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
deploy-check: site/node_modules public-export public-trials-listing
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs --dry-run

# Publish to Cloudflare at SITE_URL's domain. Refuses a preview export and a
# local address.
deploy: site/node_modules public-export public-trials-listing
	EXPORT_FILE=data/public-export.json node site/scripts/deploy.mjs

# The site with its registry search, on this machine only: http://localhost:8787
# Reads the model settings from .env and builds from site/data/export.json if there is one.
lookup-dev: site/node_modules
	node site/scripts/dev-vars.mjs
	LOOKUP_URL=/api/lookup ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site run build
	pnpm --dir site exec wrangler dev --port 8787
