# Design

## Context

The export already carries every published claim's source articles (outlet, title, date, address), so the home page can list recent reports without any change to the pipeline or the export's shape.

## Decisions

### D1. The headline opens the claim page; the outlet opens the article

A reader arrives remembering a headline and wants to know what became of it. The headline is therefore the way into the site's own page, and the outlet's name beneath it is the one-click check of the source.

Alternative considered: link the headline to the article. Rejected because the list would then send readers away before they see the status.

### D2. Headlines are quotations

An outlet's title is shown in quotation marks with the outlet named, next to the status derived from the evidence. The site adds no comment on the title. This keeps the "no editorial verdicts" rule while still showing the wording readers remember, including overstated wording.

### D3. No popularity figure

Nothing in the data model records how widely an article was read, and the one source tried (Reddit scores) refused automated reads. The list is ordered by publication date only. Popularity decides which articles become candidates, not how they are shown.

### D4. Topics are configured first and listed later

A claim needs its vertical to exist before it can be imported, but a topic with no published claim would show as an empty entry. The site therefore filters topic lists and the menu to verticals that have a published claim. The filter lives in the site because it depends only on what the export contains.

### D5. A separate candidate file

`data/seed/claims-recent.csv` is kept apart from `data/seed/claims.csv` so the dental backfill's count and notes stay as they were, and each batch can be imported and reviewed on its own.

## Risks

- **A quoted headline reads as the site's claim.** Mitigation: quotation marks, the outlet's name, and the status in the same row. Checked by hand in task 3.4.
- **Some outlets refuse automated reads.** The Daily Mail denied access during collection. The article fetch in `extract` may be refused for some candidates; those claims would need their draft entered by hand.
- **Recent claims have little registry history.** Most will show an early status. That is accurate, and the promise column records what to check later.
