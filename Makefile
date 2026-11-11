.PHONY: check lint types test site-build

# Everything CI runs. No network access is needed once dependencies are installed.
check: lint types test site-build

lint:
	uv run --directory pipeline ruff check .
	uv run --directory pipeline ruff format --check .

types:
	uv run --directory pipeline ty check

test:
	uv run --directory pipeline pytest -q

site/node_modules: site/package-lock.json
	npm --prefix site ci
	@touch site/node_modules

site-build: site/node_modules
	ASTRO_TELEMETRY_DISABLED=1 npm --prefix site run build
