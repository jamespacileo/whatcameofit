# Design

## What is built

`look_up(session, llm, backend, trials, *, text, now)` in `thenwhat.lookup.service`. One model call reads the text into a small shape (treatment, other names, search phrases, condition, one-line gist). The registry client and the decision backend are the ones match scoring uses, with the same question, so a lookup and a claim's candidates are judged alike. The command fetches an article through the existing retriever, which obeys robots.txt and falls back to an archived copy.

The engine takes text, not an address. Where the text comes from is the open part.

## Decisions for the operator

These change what readers see or what the project promises. None is taken here.

1. **May an unreviewed answer be shown publicly?** The project rule is that nothing reaches the public site unless approved in review. A live lookup is by nature unreviewed. Options: (a) show it, clearly marked as an automatic search result and never as a status; (b) show only a pointer to a tracked claim when there is one, and otherwise offer to suggest the article; (c) keep lookup as the operator's tool for adding claims fast. The answer decides whether this is a reader feature or an intake tool.
2. **Where it runs.** The public site is static files and the pipeline stays private. A reader-facing lookup needs a public endpoint holding a model key: a Cloudflare Worker (the search and scoring would be ported to JavaScript, or the Worker would call a hosted copy of this code), with rate limits and a spending cap.
3. **How a blocked article is read.** Measured on 2026-11-12: The Telegraph, Reuters, Sky News and The Times refuse or paywall automated reading; the Daily Mail varies. Options: (a) the browser extension reads the page the reader already has open and sends its title and text to the lookup; (b) a page-to-text service, which reaches more sites, sees every address, and may ignore a site's robots.txt; (c) accept the gap and ask the reader to paste the headline. The project rule today is to respect robots.txt.
4. **Social media posts by address.** X, Reddit, Facebook and others do not serve a post to an automated reader, and their terms restrict it. The engine already accepts a post's text. Reading a post by its address needs each platform's terms checked first.
5. **The promise that a pasted link is not tracked.** The `site-measurement` spec says so. Sending a pasted address to a server changes what that sentence can claim.

## Risks

- A wrong candidate shown as an answer is the failure this product exists to prevent. The score is a model's opinion; a score is never worded as a finding.
- A treatment with no searchable name still finds little. Search phrases help; how much is measured in task 3.
- Cost per lookup is small but unbounded if the endpoint is public and unprotected.
