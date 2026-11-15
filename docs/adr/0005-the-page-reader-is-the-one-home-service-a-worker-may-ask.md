# 5. The page reader runs at home, and the lookup service may ask it

Date: 2026-11-15. Status: accepted; not in effect until a change moves `site/worker` onto the reader. Change: `openspec/changes/firecrawl-page-reader`.

## Context

The project's rule is that nothing public is served from the home network: the pipeline and the database stay private, and the site is static files and a Worker on Cloudflare.

The operator runs a Firecrawl service at home as the project's page reader. It is reachable over Tailscale, which is how the pipeline asks it, and through a Cloudflare Tunnel, so that a Worker can ask it. A public lookup that asks the reader through the tunnel puts a reader-facing answer behind the home network.

The operator decided on 2026-11-15. On hosting: "it's an education/academic project and have no reasources I wish to invest into this as it's not a commercial endevour". Asked whether the public lookup worker may depend on the home-hosted reader through the tunnel: yes.

## Decision

- The page reader is the one service on the home network that a public Worker may ask.
- The tunnel's hostname refuses every request that does not carry a credential only the project's Worker holds, checked at Cloudflare before the request reaches the service, with the service's own key as a second check.
- Only the reader is reachable through the tunnel. The pipeline and the database are not, and no route to them is added.
- The reader is never called from a reader's browser or from the extension. The project's backend makes the calls.
- When the reader's machine cannot be reached, a lookup shows a service-overloaded error (the operator's wording, 2026-11-15). No second reader stands in for it.
- No money is spent on hosting. A proposal that needs paid hosting is out of scope for this project.

## What does not change

The pipeline and the database stay private. The published site is still static files built from the export. The reader keeps no article text (`openspec/changes/firecrawl-page-reader`, design decision 8).

## Consequences

- A lookup of a page the site has no answer for fails whenever the home connection or the machine is down. Answers already published are not affected.
- The tunnel is a way into the home network. Its credential is a secret of the Worker's and is rotated if it leaks; an unauthenticated request being refused is checked whenever the tunnel's configuration changes.
- Outlets see the reader's requests coming from the home connection, as they already see the pipeline's.
- The guardrail in `CLAUDE.md` now names this exception.
