# From a URL to a claim

How an article or post address becomes, or joins, a claim. Two routes take an address.
Route A (the backfill's link leads) is the only one that makes or changes a claim today.
Route B (a reader's live lookup) answers the reader and stores nothing; its hand-off into
Route A is decided in `adr/0009` and is not in effect until
`openspec/changes/cloudflare-source-of-truth` turns it on.

Behavior is defined in `openspec/` (link-leads, lead-screening, lead-triage, lead-reading,
claim-extraction, live-lookup). This page is a map of the code, not a specification.

```mermaid
flowchart TD
    subgraph B["Route B: live lookup"]
        direction TB
        b1["Reader's URL<br/>article or post"]
        b2["Unwrap post<br/>first linked article"]
        b3["Model reading<br/>treatment, condition, names"]
        b4["Registry search<br/>records scored and ranked"]
        b5(["Answer to reader<br/>nothing stored, never a status"])
        b1 --> b2 --> b3 --> b4 --> b5
    end

    subgraph A["Route A: link lead to claim"]
        direction TB
        a1["Load links<br/>platform bulk file to link leads,<br/>one lead per article key"]
        a2["Screen<br/>rules and stored data only"]
        a3["Triage<br/>model scores the title"]
        a4["Read<br/>page reader, one model read,<br/>text hashed and dropped"]
        a1 --> a2 --> a3 --> a4

        subgraph ALLOC["Allocate to a claim (under one lock)"]
            direction TB
            c1["Find candidate claims<br/>names, substance, title, rule slug"]
            c2{"Same-claim decision<br/>likely enough, and one<br/>candidate has the majority?"}
            c3{"Names overlap<br/>an existing claim?"}
            c1 --> c2
            c2 -- no --> c3
        end

        a4 --> c1
        j(["Added to claim<br/>article becomes a source article"])
        n["New claim, pending<br/>vertical chosen, claim drafted"]
        c2 -- yes --> j
        c3 -- no --> n

        a5["Prepare<br/>resolve, fetch, readings, terms,<br/>then the rule for drafts"]
        a6["Audit<br/>held until thenwhat audit clear"]
        a7(["Export<br/>published, status derived by rule"])
        n --> a5 --> a6 --> a7
    end

    x2(["Stops<br/>unlisted outlet, already tracked"])
    x3(["Not read<br/>rejected, or held and off topic"])
    x4(["No claim<br/>no page, a class of treatments,<br/>not one treatment, business news"])
    xc(["Left for the operator<br/>identity unresolved"])
    xv(["Left for the operator<br/>needs a vertical"])
    x5(["Rejected by rule<br/>a description, or a twin claim<br/>that takes its articles"])
    x6(["Archived<br/>wrong items removed at audit"])

    a2 -.-> x2
    a3 -.-> x3
    a4 -.-> x4
    c3 -. yes .-> xc
    n -.-> xv
    a5 -.-> x5
    a6 -.-> x6

    b5 -. "ADR 0009, not in effect:<br/>listed outlet leaves a link lead,<br/>no audit hold" .-> a2

    classDef exit stroke-dasharray: 4 3
    class x2,x3,x4,xc,xv,x5,x6 exit
```

Solid arrows are the path to a published claim. Dashed arrows are where a lead leaves it.

## Where each step lives

| Step | Code | Notes |
| --- | --- | --- |
| Load links | `pipeline/src/thenwhat/backfill/link_load.py`, `link_readers.py`, `address.py` | Keeps address, community, time, score and title. Nothing about who posted. |
| Screen | `backfill/link_screen.py` | No request, no model. Links to claims and trials are candidates only. |
| Triage | `backfill/link_triage.py` | Stores a score. Passed, held or rejected comes from two operator thresholds each time it is asked. |
| Read | `backfill/link_read.py` (`LinkRead.run`, `_read`) | Refused until triage has been measured. Reads passed leads, and held leads whose title names an operator topic. |
| Allocate | `backfill/link_read.py` (`_claim_it_reports`, `_join`), `extract/service.py` | With no candidate the decision is skipped. An unresolved read is never retried: the operator attaches or dismisses it. |
| Prepare | `pipeline/src/thenwhat/prepare.py` | `thenwhat prepare --pending`. Approved when the intervention is a name and no other claim has its substance, form and condition. |
| Audit, export | `cli/audit.py`, `export/build.py` | `adr/0007`: a backfill claim waits for `thenwhat audit clear`. |
| Live lookup | `site/worker/lookup.mjs`, `pipeline/src/thenwhat/lookup/service.py`, `extract/post.py` | Two implementations kept in step. Posts are unwrapped on this route only. |
