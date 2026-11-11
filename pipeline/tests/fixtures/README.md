# Test fixtures

Responses recorded from the public registries on 2026-11-11 with a generic client name. Tests replay them; nothing here is fetched at test time.

| File | Request |
|---|---|
| `clinicaltrials/study_NCT02586935.json` | `GET /api/v2/studies/NCT02586935` |
| `clinicaltrials/search_tideglusib_page{1,2,3}.json` | `GET /api/v2/studies?query.intr=tideglusib&pageSize=5&fields=…`, following `nextPageToken` |
| `europepmc/paper_srep39654.json` | `GET /search?query=DOI:"10.1038/srep39654"&resultType=core` |
| `europepmc/citing_srep39654_page1.json` | `GET /search?query=CITES:28067250_MED&resultType=core&pageSize=3` |
| `crossref/work_retracted_lancet_1998.json` | `GET /works/10.1016/S0140-6736(97)11096-0` |
| `crossref/work_srep39654.json` | `GET /works/10.1038/srep39654` |

Changes made to the recordings, for copyright and size:

- Europe PMC citing papers: each `abstractText` is replaced by a placeholder sentence.
- Crossref works: `abstract` removed; `reference` removed from `work_srep39654.json`.

Never add news article text here. Article fixtures must be synthetic.
