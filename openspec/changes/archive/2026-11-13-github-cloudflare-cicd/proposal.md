# GitHub checks and Cloudflare deployment

## Why

The operator requested a complete Cloudflare and GitHub CI/CD setup. The site is already deployed manually, but the local repository has no remote and GitHub cannot safely read the private review database.

## What changes

- Private GitHub repository with checks on pull requests and main; production deployment only after checks succeed on main.
- A committed, explicitly staged public snapshot. Staging refuses preview, unchecked, empty or malformed data and preserves the previous snapshot on failure.
- Locked Wrangler and pinned GitHub Actions, encrypted deployment credential, serialized deployments and live smoke checks.
- Public address defaults to https://whatcameofit.com. HTTPS and www redirects and contact forwarding are configured at Cloudflare.
- Method-page wording describes Cloudflare operational request/error counts and the absence of added reader analytics. Worker request logging remains disabled.

## Boundaries

No new review approvals, pipeline hosting, model-provider spending, extension-store publication, or changes to the concurrent health-area work.
