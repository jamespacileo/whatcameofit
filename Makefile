.PHONY: setup smoke-research check check-fast check-slow check-pipeline check-site check-site-build check-extension check-store lint types db-up test-db-up test test-fast test-slow benchmark scripts-test store-test store-dev site-test site-build-test site-build extension-test extension extension-safari public-export public-trials-listing publish-data deploy-check deploy deploy-ci-check deploy-ci pr-preview-check pr-preview-state pr-preview lookup-dev

export SITE_URL ?= https://whatcameofit.com
# Tests run on their own Postgres (`test-db` in compose.yaml), never on the working
# database's server. They drop and recreate one database there, named after this checkout
# so that two checkouts do not collide (pipeline/tests/conftest.py); set
# TEST_DATABASE_URL to name another, on that server, ending in _test.
export TEST_DB_PORT ?= 5434
STORE_TEST_CONCURRENCY ?= 1

# Everything CI runs: the fast set, then the slow set. Needs Docker for the test
# database; no internet access is needed once dependencies and the Postgres image are
# present.
check: check-fast check-slow

# The fast set, for every edit: under a minute. Lint, types, every pipeline test that
# builds nothing, the site's tests that build nothing, the extension's tests and the
# daily job's script. Nothing here builds the site.
check-fast: lint types test-fast scripts-test site-test extension-test

# The slow set, before a commit is pushed: a few minutes. Every test that builds the
# site (the pipeline's round trip, the site's `*.build-test.mjs`), the store's ingest
# service, and the site and extension builds themselves.
check-slow: test-slow store-test check-site-build extension

# One area in full, fast and slow, for work that touches only that area.
.PHONY: check-pipeline-fast check-release-inputs
check-pipeline: check-pipeline-fast test-slow
check-pipeline-fast: lint types test-fast
check-site: site-test check-site-build
check-site-build: site-build-test site-build
check-extension: extension-test extension
check-store: store-test
check-release-inputs: site-test site-build extension-test extension scripts-test

lint:
	uv run --directory pipeline ruff check .
	uv run --directory pipeline ruff format --check .
	uv run --directory pipeline lint-imports

types:
	uv run --directory pipeline ty check

db-up:
	docker compose up -d --wait db

test-db-up:
	docker compose up -d --wait test-db

# The pipeline's tests, fast then slow.
test: test-fast test-slow

# One worker per core, each on a database of its own (pipeline/tests/conftest.py).
test-fast: test-db-up
	uv run --directory pipeline pytest -q -n auto -m "not slow and not benchmark"

# Tests marked `slow` build the site, so the site's dependencies must be installed.
test-slow: test-db-up site/node_modules
	uv run --directory pipeline pytest -q -m "slow and not benchmark"

# The daily job's script, against a stand-in for the pipeline: no database, no network.
# What measuring costs a step that asks no source: at most a twentieth of its time
# (openspec processing-metrics). Minutes long, so not part of `make check`.
benchmark: test-db-up
	uv run --directory pipeline pytest -m benchmark

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
	cd store/ingest && node --test --test-reporter=dot --test-concurrency="$(STORE_TEST_CONCURRENCY)" tests/*.test.mjs

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

# The site's tests that build nothing (tests/*.test.mjs).
site-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site test

# The site's tests that build the site (tests/*.build-test.mjs). One at a time: builds
# share the site's cache folder.
site-build-test: site/node_modules
	cd site && ASTRO_TELEMETRY_DISABLED=1 node --test --test-reporter=dot --test-concurrency=1 $(if $(SITE_TEST_SHARD),--test-shard="$(SITE_TEST_SHARD)") tests/*.build-test.mjs

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
	node --test --test-reporter=dot extension/tests/*.test.mjs

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

# Deploys the ingest service, the only way it is deployed (store/ingest/scripts/deploy.mjs,
# docs/deploy.md): writes the configuration for the environment, refuses unless the
# jurisdiction reads eu and no migration is left to apply, deploys to a workers.dev
# address, sets the secret INGEST_TOKENS from the file TOKENS names (checksums of tokens;
# never printed), then asks the deployed service: 401 without a token on every route, 200
# for the operator's token, read from STORE_TOKEN_OPERATOR.
#   make store-deploy ENV=preview TOKENS=/path/ingest-tokens-preview.json     ARGS="--dry-run" prints the plan
#   make store-deploy ENV=production CONFIRM=thenwhat-store-ingest TOKENS=/path/ingest-tokens.json
.PHONY: store-deploy
store-deploy: store/ingest/node_modules
	@test -n "$(ENV)" || { echo "Name ENV: preview or production."; exit 1; }
	node store/ingest/scripts/deploy.mjs --env $(ENV) $(if $(CONFIRM),--confirm $(CONFIRM)) $(if $(TOKENS),--tokens-file "$(TOKENS)") $(ARGS)

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
TRIALS_SET ?= active-or-ended-this-year

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
	EXPORT_FILE=data/published-export.json node site/scripts/deploy.mjs $(if $(filter 1,$(DEPLOY_REUSE_BUILD)),--reuse-build)

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
