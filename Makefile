.PHONY: setup smoke-research check check-fast check-slow check-site check-site-build check-extension check-store scripts-test store-test store-dev site-test site-build-test site-search-test site-search-browser site-build extension-test extension-package-test extension extension-safari deploy-check deploy-pairs-check deploy deploy-ci-check pr-preview-check pr-preview-state pr-preview lookup-dev

export SITE_URL ?= https://whatcameofit.com
STORE_TEST_CONCURRENCY ?= 1

# Everything CI runs: the fast set, then the slow set. No internet access is needed once
# dependencies are present.
check: check-fast check-slow

# The fast set, for every edit: under a minute. The site and extension tests that build
# nothing, and the scripts' tests.
check-fast: scripts-test site-test extension-test

# The slow set, before a commit is pushed: a few minutes. Every test that builds the
# site (the site's build tests and browser journeys), the store's ingest service, the
# site build, and the packaged extension tests.
check-slow: store-test check-site-build extension-package-test

# One area in full, fast and slow, for work that touches only that area.
.PHONY: check-release-inputs
check-site: site-test check-site-build
check-site-build: site-build-test site-search-test site-build
check-extension: extension-test extension-package-test
check-store: store-test
check-release-inputs: site-test site-build check-extension scripts-test

scripts-test:
	sh -n scripts/worktree-setup.sh
	node --test --test-reporter=dot scripts/tests/ci-timing.test.mjs

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
	$(MAKE) site-search-browser

# The site's tests that build nothing (tests/*.test.mjs).
site-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site test

# The site's tests that build the site (tests/*.build-test.mjs). One at a time: builds
# share the site's cache folder.
site-build-test: site/node_modules
	cd site && ASTRO_TELEMETRY_DISABLED=1 node --test --test-reporter=dot --test-concurrency=1 $(if $(SITE_TEST_SHARD),--test-shard="$(SITE_TEST_SHARD)") tests/*.build-test.mjs

site-search-browser: site/node_modules
	PLAYWRIGHT_SKIP_BROWSER_GC=1 pnpm --dir site exec playwright install --only-shell chromium

site-search-test: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site test:search

# From PAIRS_BUNDLE, or the tests' small bundle when none is named.
site-build: site/node_modules
	PAIRS_BUNDLE=$(or $(PAIRS_BUNDLE),tests/bundle) ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site run build

# Live: reads each article in site/tests/fixtures/research/cases, asks the model, OpenAlex
# and ROR, and checks the report's paper is found. Costs a model call and up to five
# searches per case, so it is not part of `check`. `make smoke-research RECORD=1` rewrites
# the recorded answers the site tests replay.
smoke-research: site/node_modules
	node site/scripts/smoke-research.mjs $(if $(RECORD),--record)

# The extension tests that run directly against source.
extension-test: site/node_modules
	node --test --test-reporter=dot extension/tests/*.test.mjs

# The popup and background run from the normal package.
extension-package-test: extension
	node --test --test-reporter=dot extension/tests/*.package-test.mjs

# The extension as loaded in Chrome ("Load unpacked" on extension/dist).
extension: site/node_modules
	node extension/build.mjs

# Safari needs an app around the extension; see extension/safari.sh. Needs Xcode.
extension-safari: extension
	sh extension/safari.sh

# Publishing. See docs/deploy.md. SITE_URL must be the public address:
#   SITE_URL=https://example.org make deploy-check
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

# The site is built from one bundle of pairs (openspec pairs-site). A rehearsal of the
# public build from the small bundle the tests use: needs no Cloudflare account and
# publishes nothing. CI runs it.
deploy-ci-check: site/node_modules
	PAIRS_BUNDLE=tests/bundle node site/scripts/deploy.mjs --dry-run

# One pull request's copy of the site, on its own Worker thenwhat-pr-<number> at a
# workers.dev address. Never production. GitHub runs this for every pull request.
#   PR_NUMBER=12 make pr-preview-check
pr-preview-check: site/node_modules
	node site/scripts/pr-preview.mjs --dry-run

# Whether the pull request's copy is already this commit's. Needs no dependencies.
pr-preview-state:
	node site/scripts/pr-preview.mjs --state

pr-preview: site/node_modules
	node site/scripts/pr-preview.mjs

# Everything a deployment does except publishing (task 4.4). Reads the current bundle
# version of PAIRS_DATABASE (the production store by default, read only), exports it,
# builds the site from it and has Wrangler check the Worker.
PAIRS_DATABASE ?= thenwhat-store
deploy-check deploy-pairs-check: site/node_modules
	PAIRS_BUNDLE= PAIRS_DATABASE=$(PAIRS_DATABASE) node site/scripts/deploy.mjs --dry-run

# Publish to Cloudflare at SITE_URL's domain, from PAIRS_DATABASE's current bundle version.
# Refuses a local address, and refuses to publish without the operator's word:
#   make deploy ARGS=--cutover
deploy: site/node_modules
	PAIRS_BUNDLE= PAIRS_DATABASE=$(PAIRS_DATABASE) node site/scripts/deploy.mjs $(ARGS)

# The site with its registry search, on this machine only: http://localhost:8787
# Reads the model settings from .env and builds from PAIRS_BUNDLE (the tests' small bundle unless named).
lookup-dev: site/node_modules
	node site/scripts/dev-vars.mjs
	PAIRS_BUNDLE=$(or $(PAIRS_BUNDLE),tests/bundle) LOOKUP_URL=/api/lookup ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site run build
	pnpm --dir site exec wrangler dev --port 8787
