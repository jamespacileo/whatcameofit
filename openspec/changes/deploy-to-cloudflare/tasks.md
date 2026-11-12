# Tasks

## 1. Checks

- [x] 1.1 Check Cloudflare's current documentation for serving a static site from Workers (files directory, 404 page, trailing slashes, custom domains, dry run) before writing the configuration
- [x] 1.2 Refuse a preview export, an unchecked claim, an empty export and an unusable address; verify the ten deploy tests pass

## 2. Commands

- [x] 2.1 Add the Workers configuration and the deploy script; verify a dry run with the reviewed test fixture builds a public build and uploads nothing
- [x] 2.2 Add `make public-export`, `make deploy-check` and `make deploy`; verify `deploy-check` on the real database refuses and names the seeded claim
- [x] 2.3 Write `docs/deploy.md` and link it from the launch notes and the README

## 3. For the operator

- [ ] 3.1 Sign in with `wrangler login` and run `SITE_URL=https://<domain> make deploy-check` once the claims to publish are approved
- [ ] 3.2 Make the method page's "What is counted" section true for Cloudflare hosting, then run `make deploy`
- [ ] 3.3 Put the address in `site/site.config.mjs` and build the extension for it
