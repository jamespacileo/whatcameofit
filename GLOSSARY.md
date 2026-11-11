# Glossary

Domain terms for thenwhat. Behavior is specified in `openspec/`; this file only fixes the words.

| Term | Meaning |
|---|---|
| **Claim** | One intervention for one indication, as reported in the news. The unit the site tracks. Many articles can report the same claim. |
| **Source article** | A news article that reported a claim. Stored as URL, outlet, title and date. Its text is never stored. |
| **Promise** | A timeline stated in a source article ("human trials by 2025"). A claim can have several, each tied to its article. |
| **Vertical** | The topic area a claim belongs to, for example dental regeneration. |
| **Entity** | Something a claim names: an intervention, paper, person, institution or company. Has a name and synonyms. |
| **Origin paper** | The publication the first news reports of a claim were about. At most one per claim. |
| **Match** | A proposed link between an entity and a record in a public registry (a trial, a DOI). Always confirmed by a human. |
| **Evidence event** | A dated, sourced fact about a claim, such as a trial being registered or a follow-up paper appearing. The only input to status. |
| **Follow-up paper** | A paper that cites the origin paper and either shares an author with it or names the intervention. |
| **Review state** | Pending, approved or rejected. Applies to draft claims, matches and evidence events. |
| **Status** | Where a claim stands, derived by fixed rules from its approved evidence events: preclinical only, trial registered, Phase 1 to 3, approved, failed, terminated or retracted. |
| **Standing trial** | A trial that is neither terminated nor withdrawn and carries no failure flag. Status comes from the furthest standing trial that has started. |
| **Failure flag** | A human-set marker that a trial missed its primary endpoint, with a source link. The only way a claim becomes "failed". |
| **Overlay** | Extra text on a status, not a status itself. The no-signal overlay says how many years have passed without a new evidence event. |
| **Decision step** | A bounded classification made through the `decide` interface, such as scoring a match. Always advisory. |
| **Human label** | The operator's review decision recorded against a decision step's suggestion. Used later to evaluate and calibrate. |
| **Export** | The JSON file of approved data that the site is built from. |
| **Operator** | The person who enters claims and reviews matches and events. |
