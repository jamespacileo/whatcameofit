# Review site

A private site for the operator to review what staging and production serve: the models the site reads, the pages it answers for, and (in later phases) how the two environments differ. OpenSpec change `review-dashboard`; plan at https://claude.ai/artifact/LW8fruJG6wwLEApLiVGyBy.

- `worker/`: the Worker. It checks the reader's Cloudflare Access token on every request (`access.mjs`) and sends a store only the statements in `reads.mjs`, each one SELECT.
- `src/`: the pages, from [satnaing/shadcn-admin](https://github.com/satnaing/shadcn-admin) (MIT, `LICENSE-shadcn-admin`), trimmed to a read-only shell.
- `tests/`: the Worker on Miniflare, in front of a local D1 holding the site's test bundle.

```sh
make review-test     # the Worker's tests, no network
make review-build    # the pages, to review/dist
pnpm --dir review dev   # the pages alone, without the API
```

Settings the Worker needs, given at deployment and never written here: `ACCESS_TEAM_DOMAIN` (`https://<team>.cloudflareaccess.com`), `ACCESS_AUD` (the Access application's AUD tag), `OPERATOR_EMAILS` (comma separated). With any missing it answers 503 to everyone. It is not deployed until the Access application for review.whatcameofit.com exists.
