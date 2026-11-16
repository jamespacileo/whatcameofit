# 9. A reader's lookup leaves records, and a claim it starts is published by rule without the audit hold

Date: 2026-11-16. Status: accepted; not in effect until `openspec/changes/cloudflare-source-of-truth` turns records from lookups on. Change: `openspec/changes/cloudflare-source-of-truth`. Amends 0001 and 0007; touches 0005.

## Context

Until now a lookup, from the browser extension or the landing page, answered the reader and kept nothing (`openspec/changes/live-lookup`: "A lookup keeps nothing it read"). With the tracker's records in one store on Cloudflare (`0008`), the operator wants rows created and updated on demand as readers use the product.

Anyone can ask for a lookup. So whatever a lookup may start, a stranger may start. The operator was asked on 2026-11-16 what a lookup may create, with four answers offered: drafts held for audit like a read batch (the assistant's recommendation), publication by rule with no audit hold, leads only, or nothing. The operator chose publication by rule with no audit hold.

The operator was then asked whether the audit hold of `0007` should stay for backfill batches, given that choice, and answered that it stays for backfills only. And asked when a lookup's article is processed, answered: queued, within minutes, not while the reader waits.

## Decision

- A lookup of an article the tracker does not hold, on a listed outlet, leaves a link lead for the article and the registry trials it retrieved. It leaves nothing about the reader and no text.
- The lookup itself creates no claim and sets no status. It answers the reader as before, at once, marked as automatic and not a status.
- The lead is put on a queue and processed within minutes by the same steps and the same rules as any lead: read, drafted, registries searched, approved by rule.
- A claim drafted from a reader's lead is **not** marked awaiting audit. Once the rules approve it, the next export publishes it, marked as not checked by a person, like any claim approved by rule under `0001`.
- A claim drafted from a backfill's read batch is still marked awaiting audit and still waits for `thenwhat audit clear`, as `0007` says. `0007` is narrowed to that case, not withdrawn.
- A reader's lead that joins a claim the store already holds adds its article to that claim, as any lead does.

## Why the two cases differ

A backfill arrives hundreds of claims at a time, and `0007` was written after two such batches went live unaudited. A reader's lookup arrives one article at a time, behind the limits on searches by one reader and by all readers.

## What does not change

- Approval is by deterministic rules. A trial matches a claim only when it tests the intervention for the claim's indication; nothing is approved by score alone.
- No model decides a status. Every match shown carries its score and reasons.
- A wrong item is removed by archiving it, and an archived claim is never brought back by a later write.
- Only articles on listed outlets become leads.
- Nothing that identifies a reader is stored: no network address, no identifier, no pasted text, no image, no time finer than the day.

## Consequences

- A person who is not the operator can cause a claim to be published, by asking about an article on a listed outlet that the rules then approve. What stands between the asking and the publishing is the outlet list, the rate limits, the extraction and the rules. No person and no audit.
- That makes the outlet list and the rules the whole of the gate for this route. A change to either deserves the care a change to publishing would get.
- The operator can list, by day, the claims published from readers' leads, so a wrong one is seen and archived quickly. Proposed by the assistant and accepted by the operator on 2026-11-16. It is a report, not a gate.
- The promise the site makes beside a search changes from "the site keeps none of it" to saying what is kept: the article's address and the trial records found, and nothing about the reader.
- The page reader at home (`0005`) is now asked on a path that leads to publication, through the queue's consumer, not only on one that answers a reader.
- Model spend for processing readers' leads comes from the store-side share of the monthly ceiling, set by the operator on 2026-11-16 at 40 US dollars of 100; the cap on the lookups themselves is separate and unchanged.
- Leaving records is turned on by a setting that is off by default, so the old behavior is one switch away.
