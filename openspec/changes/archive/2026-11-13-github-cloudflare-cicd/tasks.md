# Tasks

- [x] Inspect existing deployment/review guards and current Cloudflare documentation.
- [x] Create public `whatcameofit` repository and isolate changes from concurrent local work.
- [x] Implement safe snapshot staging, CI/CD workflow, locked deployment dependency and smoke checks.
- [x] Test staging refusal and preservation of the previous snapshot.
- [x] Enable Always Use HTTPS.
- [x] Complete all project checks and public deployment rehearsal.
- [x] Verify contact destination and enable both forwarding rules.
- [x] Configure and verify www redirect.
- [x] Store scoped deployment credential and production variables in GitHub.
- [x] Push main, observe a successful GitHub production deployment, and verify the live site.
- [x] Integrate setup changes into the working checkout without changing concurrent work.

Verified on 12 November 2026: [production run 43305145870](https://github.com/jamespacileo/whatcameofit/actions/runs/43305145870), 577 pipeline tests, 151 site tests, 24 extension tests, production rehearsal, deployment and live checks. HTTPS, www path/query preservation, retired topics and contact links also checked externally. Dependency audit: zero known vulnerabilities. Browser UI tests and store publication are owned by the parallel extension chat.
