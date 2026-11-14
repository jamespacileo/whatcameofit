# 2. Share-alike drug facts are shown on claim pages and kept out of the data file

Date: 2026-11-14. Status: accepted. Change: `openspec/changes/knowledge-cards`, task 6.1.

## Context

A background card for a named drug says what kind of molecule it is and what it acts on. Open Targets Platform gives both, and draws them from ChEMBL, whose licence is CC BY-SA 3.0 Unported: anyone may share and adapt the material with credit, and adaptations must be offered under the same licence (`docs/sources.md`, "Open Targets Platform"). The site's open data file is offered under CC BY 4.0 (`LICENSE-DATA`), which is not share-alike. A share-alike fact inside that file would either break ChEMBL's terms or change the file's licence.

Whether such a fact may be shown on a page at all, beside a file that leaves it out, was left to the operator (design.md, "Licences are checked by the export"). Until the answer, the list of sources marked ChEMBL not accepted and no drug field was asked of the source.

## Decision

On 14 November 2026 the operator answered, in their words: "Yes, accept ChEMBL for drug cards." The answer reached the building session through the coordinating session, which quoted it.

- ChEMBL-derived facts (a drug's kind of molecule and its mechanisms of action, each an action and a target's name) are accepted for drug cards on claim pages. That a drug's record names one single protein as its target, which gives a target card, is such a fact too.
- Each is shown with ChEMBL's credit and its licence, CC BY-SA 3.0 Unported, on the card.
- None of them enters the open data file. The file stays CC BY 4.0, leaves out every card that rests on a ChEMBL fact, and names ChEMBL and its licence as the source left out.
- The list of sources (`pipeline/src/thenwhat/sources/terms.py`) marks `chembl` accepted and not allowed in the data file. The export and the data file read that list; no other code decides it.

## What does not change

A drug card is made only for a drug whose own name in the source equals the intervention's name or one of its other names. It carries no phase, approval or indication: the source's view of how far a drug has got can contradict the status on the same page. A card describes the drug in its source's terms and never recommends it. Cards are never an input to a status.

## Consequences

- Pages that show a drug card carry material under two licences: the site's own and ChEMBL's share-alike one, each credited where it is shown. Someone copying a drug card from a page takes it under ChEMBL's terms; someone taking the data file takes none of it.
- A reader of the data file sees fewer cards than a reader of the page, and the file says which source was left out and why.
- If the data file's licence ever became share-alike compatible, the one setting to change is `in_data_file` for `chembl`.
- If ChEMBL's licence changes, `docs/sources.md` is read again and this decision revisited.
