.PHONY: setup smoke-research check check-fast check-slow check-site check-site-build check-extension check-store scripts-test store-test site-test site-build-test site-search-test site-search-browser site-build extension-test extension-package-test extension extension-safari deploy-check deploy-pairs-check deploy deploy-staging deploy-ci-check kept-claims pr-preview-check pr-preview-state pr-preview lookup-dev

export SITE_URL ?= https://whatcameofit.com
STORE_TEST_CONCURRENCY ?= 1

# Everything CI runs: the fast set, then the slow set. No internet access is needed once
# dependencies are present.
check: check-fast check-slow

# The fast set, for every edit: under a minute. The site and extension tests that build
# nothing, and the scripts' tests.
check-fast: scripts-test site-test extension-test

# The slow set, before a commit is pushed: a few minutes. Every test that builds the
# site (the site's build tests and browser journeys), the store's pair tables, the
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

# The store's pair tables (store/ingest) on D1's local engine: no Cloudflare account, no
# network, nothing deployed. A bundle loaded and read back whole. Where the local engine
# cannot start, the tests are skipped and say why; in CI that is a failure, not a skip.
store/ingest/node_modules: store/ingest/pnpm-lock.yaml
	sh scripts/worktree-setup.sh store/ingest

store-test: store/ingest/node_modules
	cd store/ingest && node --test --test-reporter=dot --test-concurrency="$(STORE_TEST_CONCURRENCY)" tests/*.test.mjs

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
# The site is built from one bundle of pairs (openspec pairs-site). A rehearsal of the
# public build from the small bundle the tests use: needs no Cloudflare account and
# publishes nothing. CI runs it.
deploy-ci-check: site/node_modules
	PAIRS_BUNDLE=tests/bundle KEPT_CLAIMS_DIR=tests/kept-claims node site/scripts/deploy.mjs --dry-run

# The pages of claims no pair came from, kept as production built them (site/scripts/kept-claims.mjs):
# built once from production's claims commit and frozen into KEPT_CLAIMS_DIR. Staging and
# production are never published without them. About four minutes the first time; nothing after.
KEPT_CLAIMS_DIR ?= $(CURDIR)/site/.cache/kept-claims/4ea7f23613d9bd390c601b1ef00048c864064e81-format3
kept-claims: site/node_modules
	sh site/scripts/freeze-kept-claims.sh $(KEPT_CLAIMS_DIR)

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
deploy-check deploy-pairs-check: site/node_modules kept-claims
	PAIRS_BUNDLE= KEPT_CLAIMS_DIR=$(KEPT_CLAIMS_DIR) PAIRS_DATABASE=$(PAIRS_DATABASE) node site/scripts/deploy.mjs --dry-run

# Publish to Cloudflare at SITE_URL's domain, from PAIRS_DATABASE's current bundle version.
# Refuses a local address, and refuses to publish without the operator's word:
#   make deploy ARGS=--cutover
deploy: site/node_modules kept-claims
	PAIRS_BUNDLE= KEPT_CLAIMS_DIR=$(KEPT_CLAIMS_DIR) PAIRS_DATABASE=$(PAIRS_DATABASE) node site/scripts/deploy.mjs $(ARGS)

# Staging (docs/deploy.md, "Staging"): the same build, from the preview store's current bundle,
# to the thenwhat-staging Worker as a version and a deployment, every response noindex, then the
# smoke checks against STAGING_URL. Needs CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID and
# STAGING_PAIRS_DATABASE_ID. Rehearse with ARGS=--dry-run (no smoke check then).
STAGING_URL ?= https://staging.whatcameofit.com
STAGING_DATABASE ?= thenwhat-store-preview
deploy-staging: site/node_modules kept-claims
	PAIRS_BUNDLE= KEPT_CLAIMS_DIR=$(KEPT_CLAIMS_DIR) SITE_URL=$(STAGING_URL) PAIRS_DATABASE=$(STAGING_DATABASE) node site/scripts/deploy.mjs --staging $(ARGS)
	$(if $(findstring --dry-run,$(ARGS)),,node site/scripts/staging-smoke.mjs $(STAGING_URL) site/dist $(BUILD_REVISION))

# The pairs site on this machine as a deployment serves it, with the Worker and the bundle in
# D1's local engine: http://localhost:8788. Astro's dev server has no pair pages, since none is
# built (site/scripts/pairs-dev.mjs). PAIRS_BUNDLE names another bundle.
.PHONY: pairs-dev
pairs-dev: site/node_modules
	node site/scripts/pairs-dev.mjs

# The site with its registry search, on this machine only: http://localhost:8787
# Reads the model settings from .env and builds from PAIRS_BUNDLE (the tests' small bundle unless named).
lookup-dev: site/node_modules
	node site/scripts/dev-vars.mjs
	PAIRS_BUNDLE=$(or $(PAIRS_BUNDLE),tests/bundle) LOOKUP_URL=/api/lookup ASTRO_TELEMETRY_DISABLED=1 pnpm --dir site run build
	pnpm --dir site exec wrangler dev --port 8787
