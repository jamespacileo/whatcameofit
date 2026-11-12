# Deploying the site

The public site is static files on Cloudflare Workers: Cloudflare serves the files that `npm run build` writes to `site/dist`. The one address that runs code is `/api/lookup`, the optional registry search. The pipeline and the database are never deployed; they stay on the private machine.

Deploy only with `make deploy`. Do not run `wrangler deploy` by itself: the make target checks the export first, and Wrangler alone would upload whatever is in `site/dist`, including a preview build.

## Once

1. **Install Wrangler and sign in.** `wrangler login` opens a browser. Sign in to the Cloudflare account that holds the domain.
2. **Have the domain in that account.** A domain registered through Cloudflare already is. On the first deploy Wrangler attaches the domain to the Worker and Cloudflare creates the DNS record and the certificate.
3. **Decide the address.** It is given as `SITE_URL` on every command below, for example `https://example.org`. It is not stored in the repository until you put it in `site/site.config.mjs`.
4. **Check what Cloudflare counts.** The method page says "Nothing is counted." Cloudflare shows request counts for a Worker and a domain in its dashboard without any script on the page. Before the first deploy, read what your plan shows and make the "What is counted" section say exactly that. The `site-measurement` spec requires it.

## Each time

```sh
SITE_URL=https://example.org make deploy-check   # the checks, a public build, Wrangler's dry run
SITE_URL=https://example.org make deploy         # the same, then publish
```

Both first write a normal export from the running pipeline to `site/data/public-export.json` (reviewed claims only, whatever `EXPORT_PREVIEW` is set to locally), so the pipeline must be up (`docker compose up -d`).

`SUGGEST_URL` and `CORRECTIONS_URL` are read by the same build; see `docs/launch.md`.

## The registry search (optional)

The site can offer a registry search for an article it does not track (`docs/lookup.md`). It is off unless you give its settings:

```sh
wrangler secret put OPENAI_API_KEY        # once, in site/; you paste the key, it is not kept in the repository
SITE_URL=https://example.org LLM_MODEL=<model> CONTACT_EMAIL=<address> make deploy
```

With `LLM_MODEL` and `CONTACT_EMAIL` set, the build offers the search and the Worker answers at `/api/lookup`. Without them the button is not drawn and the address answers "not set up". Limits are in `site/wrangler.jsonc`: five searches a minute for one reader, thirty in all. Set a monthly spending limit with the model's provider as well.

To try it on this machine first: `make lookup-dev`, then open <http://localhost:8787>. It reads the same settings from `.env`.

## What stops a deploy

The command prints every reason at once and publishes nothing.

| Reason | What to do |
| --- | --- |
| The export is a preview | It never should be: `make deploy` writes its own export. If you set `EXPORT_FILE` yourself, point it at a normal export. |
| A claim has not been checked by a person | Approve it yourself, without `--as-assistant`: `thenwhat review approve claim ID`. This includes the seeded sample claim. |
| The export holds no claims | Review and approve claims first. |
| `SITE_URL` is missing, local, not `https://`, or has a path | Set it to the site's address alone. |
| The built site is a preview or has no sitemap | The build did not run as a public build. Report it; do not work around it. |

## After the first deploy

- Open five claim pages at the public address and check each against its sources.
- Build the browser extension for the same address: `SITE_URL=https://example.org make extension`. The extension asks only that address for its data.
- Put the address in `site/site.config.mjs` so that every build uses it without the variable.

## Undoing a deploy

`wrangler rollback` (run in `site/`) returns to the version before. `wrangler delete` removes the Worker and its domain attachment; the domain itself is untouched.

## What is in the repository

- `site/wrangler.jsonc`: the Worker's name, the files directory, the 404 page, and addresses without a trailing slash (as the canonical links and sitemap write them). No `workers.dev` address and no per-version preview addresses are created.
- `site/scripts/deploy.mjs` and `deploy-checks.mjs`: the checks and the two commands.
