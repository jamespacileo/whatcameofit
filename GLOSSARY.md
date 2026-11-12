# Glossary

Domain terms for thenwhat. Behavior is specified in `openspec/`; this file only fixes the words.

| Term | Meaning |
|---|---|
| **Claim** | One intervention for one indication, as reported in the news. The unit the site tracks. Many articles can report the same claim. |
| **Intervention** | The drug, device or method a claim is about. Stored as the claim's intervention entity, with synonyms for its other names. |
| **Indication** | The condition the intervention is claimed to treat. With the intervention it makes a claim's identity. |
| **Source article** | A news article that reported a claim. Stored as URL, outlet, title and date. Its text is never stored. |
| **Promise** | A timeline stated in a source article ("human trials by 2025"). A claim can have several, each tied to its article. |
| **Vertical** | The topic area a claim belongs to, for example dental regeneration. |
| **Group** | The broader area a vertical is filed under, such as a body system or disease area, for example mouth and teeth. Set in the pipeline's configuration; a vertical has at most one, and may have none. |
| **Entity** | Something a claim names: an intervention, paper, person, institution or company. Has a name and synonyms. |
| **Origin paper** | The publication the first news reports of a claim were about. At most one per claim. |
| **Match** | A proposed link between an entity and a record in a public registry (a trial, a DOI). Always confirmed by a human. |
| **Evidence event** | A dated, sourced fact about a claim, such as a trial being registered or a follow-up paper appearing. Status comes from approved evidence events; the evidence stage matters only when no trial is found. |
| **Follow-up paper** | A paper that cites the origin paper and either shares an author with it or names the intervention. |
| **Review state** | Pending, approved or rejected. Applies to draft claims, matches and evidence events. |
| **Status** | Where a claim stands, derived by fixed rules from its approved evidence events: preclinical only, no trial record found, trial registered, Phase 1 to 3, approved, failed, terminated or retracted. With no trial found, the confirmed evidence stage decides between the first two: a study in people is "no trial record found", laboratory or animal work is "preclinical only". |
| **Standing trial** | A trial that is neither terminated nor withdrawn and carries no failure flag. Status comes from the furthest standing trial that has started. |
| **Failure flag** | A human-set marker that a trial missed its primary endpoint, with a source link. The only way a claim becomes "failed". |
| **Overlay** | Extra text on a status, not a status itself. The no-signal overlay says how many years have passed without a new evidence event. |
| **Decision step** | A bounded classification made through the `decide` interface, such as scoring a match. Always advisory. |
| **Human label** | The operator's review decision recorded against a decision step's suggestion. Used later to evaluate and calibrate. |
| **Export** | The JSON file of approved data that the site is built from. |
| **Seed** | A checked-in claim loaded as already reviewed so a fresh checkout has a page. Its decisions are marked as the seed loader's, not an operator's. |
| **Operator** | The person who enters claims and reviews matches and events. |
