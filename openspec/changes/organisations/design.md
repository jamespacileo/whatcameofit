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

**The rule asks for strong evidence, not only the registry's choice.** First built as "a match with `chosen: true` is approved by rule". The measured run (task 6.2) found 15 of 269 such matches pointed to another organisation (5.6%), above the one-in-twenty stop, and the operator chose to raise the bar (14 November 2026). A match is now approved by rule only when ROR chose it **and** the name given equals one of the record's own names, labels, aliases or acronyms (ignoring case, accents, punctuation, a leading "The" and a closing bracket); a one-word name must also match letter for letter with its capitals; the record is not typed only as ROR's catch-all "other"; the name is not a journal title held in the paper records; and a government body's name states its country, because such names are reused from country to country. Anything else stays a pending match and the organisation unidentified. No looser second match is tried, under the operator's rule against lower-quality fallbacks. The registry's score is still stored and shown and is not thresholded: ten of the fifteen wrong matches scored 1.00. Country agreement with the report is not used because nothing records a report's country. Alternative considered: a decision step asking a model whether the record is the organisation meant. Rejected: the evidence the rule needs is in the registry's record, and no model is needed.

**Identity is the registry record.** Two entities with approved matches to the same record are one organisation in the export, under the registry's display name, with the union of their roles. Entities without an approved match are never merged, even when their names look alike.

**The export carries five registry fields and no more.** Display name, kinds (the registry's types as lower-case codes), country, website (https only, as the Worker requires), record link. Plus the score and the fetch time of the record. The registry also gives founding year, aliases, parent and child organisations and identifiers in other registries; none is exported. Each would be a step towards a profile.

**The publisher mark is a comparison of hosts.** An article is marked when its host equals an identified organisation's website host, ignoring a leading `www.`, or ends with a dot followed by it. The comparison is pure and needs no list of public suffixes, because it only ever matches against a specific organisation's own host. It runs at export over the claim's own identified organisations. Alternative considered: a table of outlet kinds (newspaper, press office, journal news). Rejected: it needs a person to classify every outlet, and the label reads as a judgement on the outlet. The mark states only where a report is.

**Wording says where and who, never what it implies.** "This report is on Kyoto University's website" and "Sponsor of 3 trials on this page". The section keeps the Worker's sentence that the registry identifies an organisation and does not verify its part. Kinds and roles are codes worded in one site module with the usual unworded-code and verdict checks.

**Order is by role, then name.** Organisations named in a report first, then sponsors, each group alphabetical. Any other order (by trials sponsored, by registry score) reads as a ranking.

**People are excluded at three points.** Person entities are never looked up (`related-research`). A sponsor that is a person never becomes an entity, by the rule `trial-facts` already applies. And the export refuses an organisation whose name equals a person entity of the claim, in case a report's person was recorded as an institution.

## Risks / Trade-offs

- [The registry chooses the wrong record for a common name] → the name must equal one of the record's names, a public body must name its country, and a one-word name must match letter for letter; what still gets through is linked with its score, an operator rejects it and it stays rejected, and the organisation is then listed by its given name. The measured residual after raising the bar was 1 of 205 ("Marie Curie", the UK charity, for the EU's Marie Skłodowska-Curie Actions).
- [The stricter rule leaves correct organisations unidentified] → accepted: 49 matches read as right under the first rule are unidentified under this one (schools and departments matched to their university, public bodies without a country, spelling and legal-suffix differences). Each is listed by its given name as not matched, which is true.
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

## Decisions made while building

Recorded on 2026-11-14 for the operator to confirm.

- **The registry record is kept in its own table.** The export needs the record's name, kinds, country, website and the time it was read, and a match holds only a one-line summary. `organisation_record` keeps ROR's `organization` object once per identifier with its fetch time, like `term_record` does for vocabulary terms. The match score stays on the match, since it is ROR's answer for one name. The same migration as `entity.named_by`.
- **An organisation remembers which reports named it.** The role "named in a report" gives the report's address, and an entity did not record which of its claim's articles it was read from. `entity_article` links an institution or company to each article that named it; extraction now records the link, and matches an organisation by name across institution and company so that one name is one entity. The migration links existing organisations on claims with one article to that article. On the 14 claims with several articles (12 of them name organisations, 57 entities on 14 November) which article named an existing organisation is not known and is not guessed: those organisations carry the role with no address. Recording it would need the articles read again, which no command does for an approved claim.
- **What "registry chooses none" stores in practice.** The rule leaves any match the registry did not choose pending, as specified and tested with a registry that returns near misses. The ROR client from `related-research` returns only the record ROR marks chosen ("Name the registry does not know": no candidate is stored), so with ROR a name with no chosen record stores nothing rather than pending near misses. Both specs hold; the queue does not fill with near misses.
- **Pending matches stored before the rule are approved when ROR's answer meets the bar on a later run.** 112 ROR matches on the real database were stored pending by `related-research` before this rule existed. A later `resolve` asks ROR again and applies the rule to them. An approved or rejected match is never changed.
- **Journals, news outlets and banks.** Extraction is now asked not to record them as institutions or companies (a `claim-extraction` delta), which acts on articles read from now on. For those already recorded, the approval rule keeps a journal title held in the paper records, and a record ROR types as "other" (the New York Times), from being identified. No rule can recognise a bank by its name alone: none was approved in the measured run (RBC Capital Markets and William Blair stayed unidentified), and one that ROR held under exactly that name and typed as a company would be approved.
- **Export shape.** Each claim gains `organisations`: `name` (the registry's name when identified, else the name a source gave), `identified`, `record` (source, identifier, record address, name, kinds, country, https website, score, date read; null when not identified) and `roles` (`named_in_report` with `article_urls`, `sponsor` with `trial_ids`). Each article gains `published_by`, the record address of the organisation whose website holds it, so the site and the data file can join the two. Kinds are carried as ROR's own lower-case types and not as a closed list, so a type ROR adds stops the site build with its name rather than the export.
- **One record, several names, one score.** When two names are tied to one record, the entry shows the lowest of their scores, so a merged entry never claims a better name match than its weakest name had.
- **The publisher mark uses only the website the entry shows.** ROR's `domains` list is not consulted, and a website that is not https is neither shown nor compared, so a report is never marked as on a site the page does not name.
- **A sponsor is recorded only for a trial with approved events**, as the spec says, so that every sponsor entity has a trial on the claim page; the export still derives the sponsor role from the trials it lists, so an entity whose trial later leaves the page has no sponsor role.

## Open Questions

- Whether an organisation's entry should later link to the site's other claims that name it. Deferred with the page-per-organisation question; it needs the operator's wording decision and no schema change.
