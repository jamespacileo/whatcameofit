# Notes for claims.csv

Compiled 2026-11-11 by an AI assistant. Not reviewed by a human. Every row is a pending draft.

## Method

- Leads came from memory and web search, then each candidate page was fetched directly (HTTP 200 required).
- Title and publication date were read from the fetched page itself (visible date, `<time>` element, or the page's own metadata). Search-result snippets were never used for a title or a date.
- After writing the CSV, all 23 URLs were fetched again: all returned 200, and every `article_title` was found as text in its page.
- Summaries and headlines are paraphrases. No article text was copied.
- `promise` is filled only where the article states a timeline (3 rows).
- Validator run: `23 rows valid`.

## How each row was verified

One line per slug: page read, and where the date came from.

- `dentine-repair-tideglusib`: King's College London news page. Date from visible "09 January 2017" and JSON-LD datePublished.
- `enamel-regrowth-calcium-phosphate-gel`: ScienceAlert article. Date from visible "03 September 2019" and article:published_time. Promise is the researcher's quoted hope, as reported there.
- `enamel-remineralisation-amelogenin-peptide`: UW News release. Date from visible "April 12, 2018" and article:published_time.
- `pulp-regeneration-baby-tooth-stem-cells`: EurekAlert copy of the Penn release (the Penn Today page returned 403). Date from the EurekAlert `<time>` element, "11-Sep-2018".
- `regenerative-fillings-dentine`: University of Nottingham press release. Date from visible "01 Jul 2016".
- `dentine-repair-aspirin`: Queen's University Belfast news page. Date from `<time>` "7 September, 2017" and JSON-LD.
- `whole-tooth-germ-splitting`: RIKEN press release. Date from visible "Dec. 18, 2015".
- `enamel-regeneration-protein-scaffold`: Queen Mary University of London news page. Date from `<time>` "1 June 2018".
- `pulp-regeneration-peptide-hydrogel`: EurekAlert release from the American Chemical Society. Date from `<time>` "22-Aug-2018" and the dateline.
- `pulp-prefabricated-blood-vessels`: EurekAlert release from OHSU. Date from `<time>` "12-Jun-2017".
- `dentine-repair-dlk1`: University of Plymouth news page. Date from `<time>` "9 August 2019".
- `periodontal-polydopamine-membrane`: UCLA Newsroom release. Date from `<time>` "March 21, 2019" and JSON-LD.
- `periodontal-3d-bioprinting`: Griffith News article. Date from visible "30 March 2016" (the metadata timestamp is 2016-03-29 23:22 UTC, which is 30 March in Brisbane).
- `whole-tooth-bioengineered-germ-dog`: Okayama University research highlight. Date from the visible posting date "March 21, 2017" (the text also says "For immediate release: 19 March 2017").
- `dentine-regeneration-cpne7-peptide`: Korea Biomedical Review article. Date from visible "Published 2019.08.29" and article:published_time. The article says "first half of next year"; the promise states this as 2020.
- `periodontal-3d-printed-scaffold`: EurekAlert release from IADR/AADR. Date from `<time>` "29-Jun-2015".
- `pulp-regeneration-gelma-stem-cells`: Tufts Now release. Date from `<time>` "December 19, 2016".
- `periodontal-adipose-stem-cells`: Tohoku University research news page. Date from visible "2019-05-09".
- `periodontal-maresin-resolvin-stem-cells`: Forsyth Institute news page. Date from `<time>` "October 2, 2020".
- `enamel-regrowth-short-amelogenin-peptide`: USC Ostrow School of Dentistry news page. Date from the page metadata only (article:published_time and JSON-LD, 2018-04-05); no visible date was detected in the text.
- `periodontal-bone-adiporon`: Dental Tribune India article (reprint of a Tufts dental magazine feature). Date from visible "Sat. 2 September 2017" and article:published_time.
- `whole-tooth-pulp-cell-tooth-germ`: TU Berlin press release on idw-online (English). Date from visible "07/24/2019 13:47", read as 24 July 2019.
- `periodontal-zinc-oxide-membrane`: Dental Tribune International article. Date from visible "Tue. 5. December 2017" and article:published_time.

## Points for the reviewer

- `whole-tooth-bioengineered-germ-dog`: the 2017 dog study is new, but the underlying "organ germ" method was first reported in mice before 2015. Decide whether it is in scope.
- `enamel-regrowth-short-amelogenin-peptide`: the short peptide was reported in 2018, but the same USC lab reported an amelogenin-chitosan enamel gel in 2013. Decide whether it is a new claim. It is also close to the University of Washington row (different lab, different peptide).
- `periodontal-bone-adiporon`: a feature article about a research programme, not a study release. The regeneration claim is soft.
- `dentine-repair-dlk1` and `periodontal-maresin-resolvin-stem-cells`: mechanism-level findings in mice or in a dish, reported as possible treatments.
- `periodontal-3d-bioprinting`: a funded study plan, not a result.
- `whole-tooth-bioengineered-germ-dog`: the page title is a newsletter issue name, not a headline.
- Some summary details (for example "tested in rats", "tests in dogs", "40 children", "cells from extracted teeth") were confirmed from search summaries of the same page rather than from text I extracted directly. Check them against the page.
- Three rows share the indication "Missing teeth" and four share "Periodontitis"; interventions differ.

## Leads dropped

- Self-assembling peptide P11-4 for early caries: first reported 2011 to 2013, before 2015.
- Lithium or other GSK-3 inhibitors for dentine: only journal papers found (for example PLOS ONE 2015), no news article.
- Resolvins for pulp regeneration: the Forsyth release is dated December 2023, out of range. The 2020 Forsyth periodontal row was kept instead.
- Enamel-forming cell lines or organoids: University of Washington organoids are 2023; Tohoku iPS ameloblasts are 2012. Out of range.
- Anti-USAG-1 antibody: excluded by the brief.
- King's College London March 2020 follow-up: same intervention and indication as the tideglusib row.
- University of Washington lozenge coverage: dated 2021, out of range. The 2018 UW release on the same peptide was used.
- USC amelogenin-chitosan hydrogel (2019 grants story): first reported 2013.
- Penn Today page for the baby-tooth trial: returned 403. EurekAlert copy used.
- phys.org pages (enamel gel, zinc oxide membrane): returned 403. Other sources used.
- UCLA adhesive hydrogel, March 2020: regenerates bone around dental implants, not teeth. Out of scope.
- Penn Del-1 protein, 2015: inhibits bone loss, not regeneration; the EurekAlert URL returned 404.
- Penn complement C3 inhibitor, 2016: reverses inflammation, not regeneration.
- INSERM dental stem cell repair mechanism, 2015: no intervention named.
- University of Plymouth Notch and periodontal ligament, August 2019: mechanism only.
- Karolinska dental cell atlas, 2020: basic research, no intervention.
- Lankenau 1,4-DPCA drug for jaw bone: published 2022, out of range; one page returned 403.
- LANAP laser FDA clearance, 2016: the procedure and its regeneration claims predate 2015.
- Regroth (trafermin, FGF-2): first reported before 2015; no loadable 2016 source found.
- Nakashima pulp stem cell clinical study, 2017: journal paper only; the news coverage is from 2013.
- Fourth Military Medical University periodontal ligament stem cell trial, 2016: no news article found.
- Tokyo Women's Medical University periodontal ligament cell sheets: no news article found.
- University of Michigan nanofibrous microspheres: journal papers only.
- Stanford liposomal WNT3A for dentine: patents and papers only.
- Semaphorin 3A for dentine (Kyushu): journal paper only.
- Osaka University S100-A7 for pulp healing: journal paper only.
- University of Nebraska Medical Center simvastatin prodrug: journal papers only.
- University of Iowa miR-200c: grants and patents only.
- Tufts bioengineered tooth buds (Yelick): 2017 paper had no news article; the news coverage is from 2025.
- Rice and Baylor peptide hydrogel for pulp: news is from 2012.
- University of Illinois Chicago tooth reattachment with stem cells: 2010.
- University of Illinois Chicago exosomes for pulp: the page found showed no readable date.
- University of Hong Kong hypoxia-conditioned tooth stem cells: 2022.
- NJIT follow-up release: June 2022, out of range.
- Forsyth 3D-printed bone graft: 2025.
- Columbia tooth scaffold (2010), USC bio-root in minipigs (2006), UT Health San Antonio pulp regeneration (2012), King's College London bioteeth (2013): before 2015.

## Two rows added afterwards (2026-11-11)

Added by the main session to reach 25. Each page was fetched; title and date were read from the page.

- `periodontal-ligament-cell-sheet-implant`: EurekAlert release 795480. Title from the page heading; date from the page's "13-Jun-2018" stamp (a search summary said 11 June; the page says 13 June). The page mentions a dog and the journal. **Double-check:** it concerns ligament around an implant, which sits at the edge of the scope.
- `lab-grown-teeth-incisor-stem-cells`: USC Today. Title from the page; date 2015-04-21 from the page's published-time metadata. **Double-check:** this is a soft claim, a mechanism finding in rodents with a stated hope, not a treatment. The summary was written from the page's own description line, not from a full read.

Leads tried and dropped in this pass: trafermin (Regroth) approval in Japan, 2016 (only a regulator report and trial records found, no news report; the company site could not be reached); mobilized dental pulp stem cells pilot study, 2017 (journal paper only); periodontal ligament cell sheets in ten patients, 2018 (journal paper only).
