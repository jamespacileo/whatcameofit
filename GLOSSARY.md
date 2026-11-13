# Glossary

Domain terms for thenwhat. Behavior is specified in `openspec/`; this file only fixes the words.

| Term | Meaning |
|---|---|
| **Claim** | One intervention for one indication, as reported in the news. The unit the site tracks. Many articles can report the same claim. |
| **Intervention** | The drug, device or method a claim is about. Stored as the claim's intervention entity, with synonyms for its other names. |
| **Indication** | The condition the intervention is claimed to treat. With the intervention it makes a claim's identity. |
| **Source article** | A news article that reported a claim. Stored as URL, outlet, title and date. Its text is never stored. |
| **Promise** | A timeline stated in a source article ("human trials by 2025"). A claim can have several, each tied to its article. |
| **Vertical** | The topic area a claim belongs to, for example gum disease. Each claim has exactly one. |
| **Group** | The body system or disease area a vertical is filed under, for example mouth and teeth. Every vertical has exactly one group. Each group is anchored, in the pipeline's configuration only, to the HRCS health categories it covers. |
| **General vertical** | The vertical that shares its group's slug and title. A claim that fits a group but none of its specific verticals goes here. |
| **Approach** | The kind of intervention a claim reports, such as drug, gene therapy or transplant. Optional, at most one per claim, and never part of status. |
| **Entity** | Something a claim names: an intervention, paper, person, institution or company. Has a name and synonyms. |
| **Search phrase** | Words a registry or a paper would use for an intervention that has no product name, such as "median nerve stimulation". Searched for within the claim's indication only. Not a name, and never shown as one. |
| **Origin paper** | The publication the first news reports of a claim were about. At most one per claim. |
| **Match** | A proposed link between an entity and a record in a public registry (a trial, a DOI). Approved by rule when its score is in the high band; a person can reject it afterwards. |
| **Evidence event** | A dated, sourced fact about a claim, such as a trial being registered or a follow-up paper appearing. Status comes from approved evidence events; the evidence stage matters only when no trial is found. |
| **Follow-up paper** | A paper that cites the origin paper and either shares an author with it or names the intervention. |
| **Review state** | Pending, approved or rejected. Applies to draft claims, matches and evidence events. A decision is made by a rule, a human, the seed loader or an assistant; approval by rule publishes. |
| **Archived** | Taken off the public site by the operator. The address answers 410; the database keeps the record. Not a review state. |
| **Confidence** | A match's score shown as a word and a percentage, such as "High match · 92%", with its reasons. An automatic estimate of matching the reported treatment and condition, never a verdict on the treatment. |
| **Source** | An article or post the pipeline read: its address, outlet, title and date, never its text. Has a page listing its claim or up to five candidates. |
| **Status** | Where a claim stands, derived by fixed rules from its approved evidence events: preclinical only, no trial record found, trial registered, Phase 1 to 3, approved, failed, terminated or retracted. With no trial found, the confirmed evidence stage decides between the first two: a study in people is "no trial record found", laboratory or animal work is "preclinical only". |
| **Standing trial** | A trial that is neither terminated nor withdrawn and carries no failure flag. Status comes from the furthest standing trial that has started. |
| **Failure flag** | A human-set marker that a trial missed its primary endpoint, with a source link. The only way a claim becomes "failed". |
| **Overlay** | Extra text on a status, not a status itself. The no-signal overlay says how many years have passed without a new evidence event. |
| **Decision step** | A bounded classification made through the `decide` interface, such as scoring a match. Always advisory. |
| **Human label** | The operator's review decision recorded against a decision step's suggestion. Used later to evaluate and calibrate. |
| **Export** | The JSON file of approved data that the site is built from. |
| **Seed** | A checked-in claim loaded as already reviewed so a fresh checkout has a page. Its decisions are marked as the seed loader's, not an operator's. |
| **Operator** | The person who runs the pipeline, corrects decisions and archives wrong items. |
