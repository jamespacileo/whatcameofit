# Test fixtures

Responses recorded from the public registries on 2026-11-11 with a generic client name. Tests replay them; nothing here is fetched at test time.

| File | Request |
|---|---|
| `clinicaltrials/study_NCT02586935.json` | `GET /api/v2/studies/NCT02586935` |
| `clinicaltrials/search_tideglusib_page{1,2,3}.json` | `GET /api/v2/studies?query.intr=tideglusib&pageSize=5&fields=…`, following `nextPageToken` |
| `clinicaltrials/search_broad_count.json` | `GET /api/v2/studies?query.intr=CAR-T cell therapy&pageSize=3&countTotal=true&fields=…` |
| `clinicaltrials/search_broad_with_condition.json` | the same with `query.cond=Stiff person syndrome` |
| `clinicaltrials/titles_surmount5.json` | `GET /api/v2/studies?query.titles="SURMOUNT-5"&pageSize=20&countTotal=true&fields=…` (2026-11-12) |
| `clinicaltrials/study_NCT06497504_conditions.json` | `GET /api/v2/studies/NCT06497504` as stored by the pipeline on 2026-11-11, trimmed to its identification, conditions and condition MeSH terms |
| `europepmc/paper_nejmoa2206038.json` | `GET /search?query=DOI:"10.1056/NEJMoa2206038"&resultType=core` (2026-11-12) |
| `openai/decisions_three_records.json` | `POST /v1/decisions` with three made-up trial records as questions; the request and its response (2026-11-12) |
| `europepmc/paper_srep39654.json` | `GET /search?query=DOI:"10.1038/srep39654"&resultType=core` |
| `europepmc/citing_srep39654_page1.json` | `GET /search?query=CITES:28067250_MED&resultType=core&pageSize=3` |
| `crossref/work_retracted_lancet_1998.json` | `GET /works/10.1016/S0140-6736(97)11096-0` |
| `crossref/work_srep39654.json` | `GET /works/10.1038/srep39654` |
| `openalex/search_median_nerve_tourette.json` | `GET /works?search=("median nerve stimulation") AND "Tourette syndrome"&per_page=3&select=id,doi,title,publication_year,publication_date,type,primary_location,authorships,abstract_inverted_index,ids` (2026-11-14) |
| `openalex/search_nothing.json` | the same search for made-up words that no paper holds (2026-11-14) |
| `openalex/work_704541.json` | `GET /works/doi:10.64898/2026.02.07.704541?select=…` (2026-11-14) |
| `ror/affiliation_university_of_nottingham.json` | `GET /v2/organizations?affiliation=University of Nottingham` (2026-11-14) |
| `ror/affiliation_unknown.json` | the same for a made-up name: ROR lists near misses and marks none as chosen (2026-11-14) |
| `mesh/descriptor_obesity.json` | `GET id.nlm.nih.gov/mesh/2026/D009765.json` (2026-11-14) |
| `mesh/concept_obesity.json` | `GET /mesh/2026/M0015159.json`, the descriptor's preferred concept, which holds the definition (2026-11-14) |
| `mesh/descriptor_unknown.json` | `GET /mesh/2026/D999999.json`: an unknown identifier answers 200 with an empty object (2026-11-14) |
| `mesh/label_obesity.json` | `GET /mesh/lookup/descriptor?label=Obesity&match=exact&limit=10&year=2026` (2026-11-14) |
| `mesh/label_obesity_contains.json` | the same with `match=contains`, which the client never asks; it lists "Anti-Obesity Agents" first (2026-11-14) |
| `mesh/label_none.json` | the exact lookup for "Knee osteoarthritis pain", which no label equals (2026-11-14) |

Changes made to the recordings, for copyright and size:

- Europe PMC citing papers, `europepmc/paper_srep39654.json` and `europepmc/paper_sciadv_abf1798.json`: each `abstractText` is replaced by a placeholder sentence.
- `europepmc/paper_nejmoa2206038.json`: `abstractText` is replaced by a placeholder that keeps only the paper's registry number; subject headings, grants, links and all but two authors are removed.
- OpenAlex works: each `abstract_inverted_index` is replaced by a placeholder sentence. The key was sent in a header and is in no recording.
- MeSH: none. The records are NLM's own and are kept whole, re-indented.
- ROR: only the first two items of each answer are kept.
- Crossref works: `abstract` removed; `reference` removed from `work_srep39654.json`.
- `openai/decisions_three_records.json`: the model's name is replaced by `example-model` in the request and the response. The input is synthetic.

Never add news article text here. Article fixtures must be synthetic.
