# 6. Whether and how a site is asked is the page reader's decision

Date: 2026-11-15. Status: accepted; takes effect when `openspec/changes/firecrawl-page-reader` is applied. Until then the pipeline reads robots.txt itself, as `CLAUDE.md` says. Change: `openspec/changes/firecrawl-page-reader`.

## Context

The project's rule was: respect robots.txt and published rate limits, and identify the client with a contact User-Agent. The pipeline carried that out itself for every article: it read each outlet's robots.txt, kept its crawl delay, spaced its requests per outlet, and refused where the rules refused. `docs/sources.md` recorded, on 2026-11-12, which social platforms were not read and why.

The operator runs a self-hosted Firecrawl service as the project's page reader (ADR 0005), with a router that reads X, Bluesky, YouTube, Reddit and Meta's platforms by their own routes. The operator wants the rules about individual sites held in that one service and the handling of particular addresses pruned from this project.

The operator decided on 2026-11-15, in three answers:

- "we'd be delegating handling of any rules around handling individual domains to the service, in cases where we want to return a not allowed, rate limited or other limitations the service would return that in the response, so we can handle them accordingly on our end".
- "allow X, Reddit, Meta, Youtube and others, it'll be the responsibility of the service to decide how to handle these, in worst case we may get markdown based off open graph cards".
- Asked whether robots.txt on ordinary news sites should also be left to the service to decide: "Service decides".

## Decision

- Whether an address is fetched, whether a site's robots.txt is followed, how often a site is asked and how the request is made are decided by the page reader. The project holds no rule about an individual site for fetching, and checks none.
- The project acts on what the reader answers: a page read, not allowed, not now, or not served.
- The social and video platforms recorded as not read on 2026-11-12 may be read through the reader.
- The assistant's reading, not the operator's words: this covers the contact User-Agent and proxies for page fetches, since they are part of how a site is asked.

## What does not change

- No article text and no post text is kept, by the pipeline or by the reader. The reader is checked for this and the dated result is in `docs/sources.md`.
- A post's author is never kept, logged or exported.
- Registries and literature indexes (`pipeline/src/thenwhat/sources/`) are still asked directly, within their published limits, with the contact User-Agent, and their terms are still read before a client is written.
- A post is a way to an article and its claim. It is never evidence, and nothing found through one is presented as a treatment option.

## Consequences

- The project no longer promises that robots.txt is followed. No page of the site, the README or the method text may say that it is.
- An outlet the pipeline refused before may now be read. The first outlets report after the change lists each one.
- What the 2026-11-12 reading found about each platform's terms and robots.txt stays in `docs/sources.md` beside the decision, for whoever revisits it. This is the operator's decision and not a legal reading.
- The reader's requests come from the operator's home connection. A site or platform that objects to how it was asked will act against that connection and that service.
- The guardrail in `CLAUDE.md` and `openspec/config.yaml` is reworded when the change is applied.
