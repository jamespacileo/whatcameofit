# Design

## Context

See proposal.md for the motivation. What the code and the in-flight changes hold today:

- Institution and company entities are created from a draft in `extract/service.py`. `resolve/service.py` handles only the intervention and papers with a DOI; nothing resolves, exports or shows an organisation.
- `related-research` specifies "Organisations are looked up by name": institution and company entities go to an open registry, the candidate's record line is name, country and website, and the score is the registry's own, with no model. It specifies "People are not looked up". Its tasks 6.1 (terms in `docs/sources.md`) and 6.2 (client and candidate matches) are open. Its design names ROR and defers pages per organisation until the operator decides the wording.
- The public lookup Worker already calls ROR (`site/worker/research.mjs`): `GET /v2/organizations?affiliation=<name>`, keeps a record only when `chosen === true`, and keeps id, display name, country, website (https only) and score. Its page wording: "ROR identifies organisations named in the report. It does not verify their involvement or endorsement."
- `docs/sources.md` on ROR (checked 2026-11-13): metadata is CC0, no key or account, 2,000 requests per five minutes per address.
- `trial-facts` exports each trial's lead sponsor as a name and a kind, with no name when the sponsor is a person (the registry's class `INDIV`, or a responsible party that is a sponsor-investigator).
- `SourceArticle` holds url, outlet, title and date. Nothing records what kind of site an outlet is.
- The main spec's "Human confirmation" and "A rule SHALL never approve" lines are already superseded for trials by `auto-publish`; organisation matches have no approval rule in any change.

Measured read-only on 2026-11-14: 271 institution entities on 74 claims, 42 company entities on 25; 207 of 222 trials with an organisation as lead sponsor (108 classed industry, 95 other, 3 government, 1 network), 14 with a person.

## Goals / Non-Goals

**Goals:**

- One mechanism for every organisation, wherever its name came from: an entity, a candidate match, a rule, the review queue, the export.
- Everything shown about an organisation is either a role a source states or a field of its registry record.
- Nothing about a person leaves the pipeline.

**Non-Goals:**

- Telling a reader how much to trust an organisation. No score of standing, no size, no founding date, no count of claims.
- Pages per organisation. The wording question `related-research` left open stays open.
- Funders and journals. Funders are in one of three recorded paper fixtures and absent from all three Crossref fixtures; they would be a mostly empty field.
- Classifying outlets. Only the one checkable case is marked: a report on the site of an organisation its claim names.

## Decisions

**Sponsors become entities, not a second kind of record.** At fetch, each approved trial's lead sponsor that is an organisation is added to the claim's entities, as a company when the registry classes it industry and an institution otherwise. This sends sponsors through the lookup, the rule, the review queue and the archive that `related-research` builds for article-named organisations. Alternative considered: a separate table of sponsor lookups keyed by name. Rejected: two stores for the same thing, and no way for an operator to reject a wrong sponsor match.

**An entity records where it was named.** A new array column on `entity`, `named_by`, holding `article`, `registry` or both, defaulting to `article` for every existing row. The role "named in a report" is exported only for `article`; "sponsor" is derived from the trial facts by matching names, so it stays true if a sponsor changes.

**The rule is the registry's own choice.** A match with `chosen: true` is approved by rule; anything else is pending. This is the rule the Worker already applies when it decides what to show. The registry's score is stored and shown, and is not thresholded: ROR's affiliation matching returns its own verdict, and a second threshold on top would be this project's guess about someone else's scale. Alternative considered: a decision step asking a model whether the record is the organisation meant. Rejected: no model is needed to follow the registry's choice, and an operator can reject.

**Identity is the registry record.** Two entities with approved matches to the same record are one organisation in the export, under the registry's display name, with the union of their roles. Entities without an approved match are never merged, even when their names look alike.

**The export carries five registry fields and no more.** Display name, kinds (the registry's types as lower-case codes), country, website (https only, as the Worker requires), record link. Plus the score and the fetch time of the record. The registry also gives founding year, aliases, parent and child organisations and identifiers in other registries; none is exported. Each would be a step towards a profile.

**The publisher mark is a comparison of hosts.** An article is marked when its host equals an identified organisation's website host, ignoring a leading `www.`, or ends with a dot followed by it. The comparison is pure and needs no list of public suffixes, because it only ever matches against a specific organisation's own host. It runs at export over the claim's own identified organisations. Alternative considered: a table of outlet kinds (newspaper, press office, journal news). Rejected: it needs a person to classify every outlet, and the label reads as a judgement on the outlet. The mark states only where a report is.

**Wording says where and who, never what it implies.** "This report is on Kyoto University's website" and "Sponsor of 3 trials on this page". The section keeps the Worker's sentence that the registry identifies an organisation and does not verify its part. Kinds and roles are codes worded in one site module with the usual unworded-code and verdict checks.

**Order is by role, then name.** Organisations named in a report first, then sponsors, each group alphabetical. Any other order (by trials sponsored, by registry score) reads as a ranking.

**People are excluded at three points.** Person entities are never looked up (`related-research`). A sponsor that is a person never becomes an entity, by the rule `trial-facts` already applies. And the export refuses an organisation whose name equals a person entity of the claim, in case a report's person was recorded as an institution.

## Risks / Trade-offs

- [The registry chooses the wrong record for a common name] → the entry links the record and shows the score; an operator rejects the match and it stays rejected; the organisation falls back to its given name.
- [A report names an institution in passing and the page lists it as if it did the work] → the role says "named in the report" and nothing more; the section says the registry does not verify an organisation's part. Tightening which organisations a report "names" is an extraction change, and is not hidden here.
- [The publisher mark reads as a warning] → the wording states a location only, the build's verdict check covers it, and the method page explains what it is and is not.
- [A sponsor's name is a person the registry classed as an organisation] → the same two signs `trial-facts` uses apply before an entity is made; a name that slips through is one an operator can reject, and task 6.2 reads every sponsor name once before release.
- [About 520 lookups on the first run] → under the registry's stated limit by a wide margin at the client's paced rate; cached; only new names are asked afterwards.
- [Depends on tasks in another change] → task 1.1 is that dependency, stated as a gate, so the order is explicit.

## Migration Plan

1. `related-research` tasks 6.1 and 6.2 first.
2. One migration adds `entity.named_by` with the default `{article}`. Reversible by dropping the column.
3. Pipeline: sponsor entities at fetch, the approval rule, the export. A `thenwhat fetch` then a `thenwhat resolve` fills today's claims.
4. Site in the same deploy as the export field. An export without `organisations` builds as today.
5. Rollback: revert the deploy. Sponsor entities can stay; nothing else reads them.

## Open Questions

- Whether an organisation's entry should later link to the site's other claims that name it. Deferred with the page-per-organisation question; it needs the operator's wording decision and no schema change.
