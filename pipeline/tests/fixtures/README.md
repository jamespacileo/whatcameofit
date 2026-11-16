# Test fixtures

Responses recorded from the public registries on 2026-11-11 with a generic client name. Tests replay them; nothing here is fetched at test time.

| File | Request |
|---|---|
| `clinicaltrials/study_NCT02586935.json` | `GET /api/v2/studies/NCT02586935` |
| `clinicaltrials/search_tideglusib_page{1,2,3}.json` | `GET /api/v2/studies?query.intr=tideglusib&pageSize=5&fields=…`, following `nextPageToken` |
| `clinicaltrials/search_broad_count.json` | `GET /api/v2/studies?query.intr=CAR-T cell therapy&pageSize=3&countTotal=true&fields=…` |
| `clinicaltrials/search_broad_with_condition.json` | the same with `query.cond=Stiff person syndrome` |
| `clinicaltrials/titles_surmount5.json` | `GET /api/v2/studies?query.titles="SURMOUNT-5"&pageSize=20&countTotal=true&fields=…` (2026-11-12) |
| `clinicaltrials/search_too_complicated.txt` | the body of the 400 answer to `GET /api/v2/studies?query.intr=<a thirteen-word search phrase>&query.cond=Periodontal bone defect` (2026-11-14) |
| `clinicaltrials/condition_too_complicated.txt` | the body of the 400 answer to `GET /api/v2/studies?query.intr=Pembrolizumab plus pemetrexed and platinum chemotherapy&query.cond=Previously untreated metastatic nonsquamous non-small-cell lung cancer without sensitizing EGFR or ALK alterations` (2026-11-15); the registry names the refused field `Conditions or disease` |
| `clinicaltrials/study_NCT06497504_conditions.json` | `GET /api/v2/studies/NCT06497504` as stored by the pipeline on 2026-11-11, trimmed to its identification, conditions and condition MeSH terms |
| `europepmc/paper_nejmoa2206038.json` | `GET /search?query=DOI:"10.1056/NEJMoa2206038"&resultType=core` (2026-11-12) |
| `openai/decisions_three_records.json` | `POST /v1/decisions` with three made-up trial records as questions; the request and its response (2026-11-12) |
| `europepmc/paper_srep39654.json` | `GET /search?query=DOI:"10.1038/srep39654"&resultType=core` |
| `europepmc/citing_srep39654_page1.json` | `GET /search?query=CITES:28067250_MED&resultType=core&pageSize=3` |
| `crossref/work_retracted_lancet_1998.json` | `GET /works/10.1016/S0140-6736(97)11096-0` |
| `crossref/work_srep39654.json` | `GET /works/10.1038/srep39654` |
| `clinicaltrials/list_page_{1,2}.json` | `GET /api/v2/studies?filter.advanced=<phase 3 drug or biological, migraine, updated since 2026-11-10>&pageSize=3&fields=…`, following `nextPageToken`: four trials over two pages (2026-11-14) |
| `clinicaltrials/phase3_sample_trials.json` | the identifiers, conditions and interventions of the 200 phase 3 trials sampled on 2026-11-14 (`docs/research/phase3-article-hit-rate`), read from `GET /api/v2/studies?filter.ids=…` |
| `mediacloud/story_list.json` | synthetic: the shape of `GET /api/search/story-list` as Media Cloud's own client reads it, with made-up stories. Never recorded from the service, so it holds no real headline |
| `openalex/search_median_nerve_tourette.json` | `GET /works?search=("median nerve stimulation") AND "Tourette syndrome"&per_page=3&select=id,doi,title,publication_year,publication_date,type,primary_location,authorships,abstract_inverted_index,ids` (2026-11-14) |
| `openalex/search_nothing.json` | the same search for made-up words that no paper holds (2026-11-14) |
| `openalex/search_at_kings_college_london.json` | `GET /works?search="Lab-grown teeth" OR "tooth regeneration"&filter=authorships.institutions.ror:https://ror.org/0220mzb33,from_publication_date:2023-04-14,to_publication_date:2025-05-15&per_page=3&select=…`: papers on the terms with an author at King's College London (2026-11-14) |
| `openalex/work_704541.json` | `GET /works/doi:10.64898/2026.02.07.704541?select=…` (2026-11-14) |
| `ror/affiliation_university_of_nottingham.json` | `GET /v2/organizations?affiliation=University of Nottingham` (2026-11-14) |
| `ror/affiliation_unknown.json` | the same for a made-up name: ROR lists near misses and marks none as chosen (2026-11-14) |
| `ror/affiliation_crispr_therapeutics.json`, `affiliation_ulster_university.json`, `affiliation_goteborg_university.json`, `affiliation_university_college_london_hospitals.json` | the same for names ROR answered with a chosen record that is another organisation (2026-11-14, openspec organisations task 6.2) |
| `ror/affiliation_food_and_drug_administration.json`, `affiliation_us_food_and_drug_administration.json` | the same for the US agency's name without and with its country: without it, ROR chose Thailand's agency, whose name is exactly "Food and Drug Administration" (2026-11-14) |
| `ror/affiliation_neuron.json`, `affiliation_the_new_york_times.json` | the same for a journal and a newspaper a report named: ROR chose "NeurON : Interface Neuro-machine" and "New York Times", typed "other" (2026-11-14) |
| `europepmc/pmid_35658024_trial_report.json` | `GET /search?query=EXT_ID:35658024 AND SRC:MED&resultType=core`: a Phase 3 randomised trial's report, with its subject headings (2026-11-14) |
| `europepmc/pmid_9500320_retracted.json` | the same for 9500320, a paper the index marks "Retracted Publication" (2026-11-14) |
| `europepmc/pmid_41363554_humans_animals.json` | the same for 41363554, a review indexed with both "Humans" and "Animals" (2026-11-14) |
| `europepmc/pmid_unknown.json` | the same for a number no paper has: `hitCount` 0 (2026-11-14) |
| `europepmc/paper_preprint_299164.json` | `GET /search?query=DOI:"10.1101/2020.09.15.299164"&resultType=core`: a preprint, with no journal and no subject headings (2026-11-14) |
| `mesh/descriptor_obesity.json` | `GET id.nlm.nih.gov/mesh/2026/D009765.json` (2026-11-14) |
| `mesh/concept_obesity.json` | `GET /mesh/2026/M0015159.json`, the descriptor's preferred concept, which holds the definition (2026-11-14) |
| `mesh/descriptor_unknown.json` | `GET /mesh/2026/D999999.json`: an unknown identifier answers 200 with an empty object (2026-11-14) |
| `mesh/label_obesity.json` | `GET /mesh/lookup/descriptor?label=Obesity&match=exact&limit=10&year=2026` (2026-11-14) |
| `mesh/label_obesity_contains.json` | the same with `match=contains`, which the client never asks; it lists "Anti-Obesity Agents" first (2026-11-14) |
| `mesh/label_none.json` | the exact lookup for "Knee osteoarthritis pain", which no label equals (2026-11-14) |
| `gsrs/search_baxdrostat.json` | `GET gsrs.ncats.nih.gov/api/v1/substances/search?q=root_names_name:"^baxdrostat$"&top=5&fdim=0` (2026-11-14) |
| `gsrs/names_baxdrostat.json` | `GET /api/v1/substances(d050debb-84b5-4703-90a9-afc4fd2c21c6)/names`: twelve names, three of the kind `cd` (2026-11-14) |
| `gsrs/search_cin_107_spaced.json` | the search for `"^cin 107$"`, which GSRS answers with the substance coded "CIN-107"; the client refuses it (2026-11-14) |
| `gsrs/search_nothing.json` | the search for `"^faecal microbiota transplant$"`: `total` 0 (2026-11-14) |
| `rxnorm/rxcui_elevidys.json`, `rxnorm/properties_2641681.json`, `rxnorm/related_in_2641681.json` | `GET rxnav.nlm.nih.gov/REST/rxcui.json?name=Elevidys&search=0`, then `GET /REST/rxcui/2641681/properties.json` and `GET /REST/rxcui/2641681/related.json?tty=IN`: a brand of one ingredient (2026-11-16) |
| `rxnorm/rxcui_advair.json`, `rxnorm/properties_301543.json`, `rxnorm/related_in_301543.json` | the same three for "Advair": a brand of two ingredients (2026-11-16) |
| `rxnorm/rxcui_corbevax.json` | the exact search for "Corbevax", which RxNorm does not list: an empty `idGroup` (2026-11-16) |
| `rxnorm/rxcui_aspirin.json`, `rxnorm/properties_1191.json` | the exact search for "aspirin" and its concept's record: an ingredient, not a brand (2026-11-16) |
| `mesh/term_ketogenic_diet.json` | `GET /mesh/lookup/term?label=Ketogenic Diet&match=exact&limit=10&year=2026`: an entry term of a descriptor labelled otherwise (2026-11-14) |
| `mesh/term_orforglipron.json`, `mesh/term_obesity.json` | the same lookup for "orforglipron" (the term of a supplementary record) and "Obesity" (2026-11-14) |
| `mesh/term_tirzepatide.json`, `mesh/owner_tirzepatide.json` | the term lookup and the owner query for "tirzepatide": the term belongs to a descriptor and to a withdrawn supplementary record labelled "[OBSOLETE] tirzepatide", whose own address answers an empty object (2026-11-14) |
| `mesh/term_ketogenic_word.json` | the same lookup for "Ketogenic", a word contained in an entry term: `[]` (2026-11-14) |
| `mesh/owner_ketogenic_diet.json`, `mesh/owner_orforglipron.json`, `mesh/owner_obesity.json` | `GET /mesh/sparql?query=…&format=JSON&year=2026&inference=false`, the query in `docs/sources.md` for one term each: the descriptor or supplementary record the term belongs to (2026-11-14) |
| `mesh/owners_three_terms.json` | the same query for the three terms at once (2026-11-14) |
| `mesh/owner_none.json` | the same query for a term identifier the vocabulary does not hold (`T999999999`): no row (2026-11-14) |
| `mesh/supplementary_orforglipron.json` | `GET /mesh/2026/C000729680.json`: a supplementary record, with its `note` and the `source` it was taken from (2026-11-14) |
| `mesh/concept_orforglipron.json` | `GET /mesh/2026/M000766720.json`, its preferred concept, which holds no definition (2026-11-14) |
| `opentargets/search_cxcr3.json` | `POST api.platform.opentargets.org/api/v4/graphql` with the target search in `sources/opentargets.py` for the word "CXCR3": equal to an approved symbol (2026-11-14) |
| `opentargets/search_usag_1.json`, `opentargets/search_apoe4.json` | the same for "USAG-1" and "APOE4": each equal to a listed synonym of one gene (2026-11-14) |
| `opentargets/search_tms.json` | the same for "TMS": a synonym of two genes, among eight genes whose symbols only start with it (2026-11-14) |
| `opentargets/search_tmsb1.json` | the same for "TMSB1": seven hits, none with an equal symbol or synonym (2026-11-14) |
| `opentargets/search_ctx310.json` | the same for "CTX310": no hit (2026-11-14) |
| `opentargets/target_cxcr3.json` | the same address with the target query for `ENSG00000186810`: three function descriptions (2026-11-14) |
| `opentargets/drugs_tirzepatide.json` | the same address with the drug search in `sources/opentargets.py` for "tirzepatide": one drug, two mechanisms (2026-11-14) |
| `opentargets/drugs_orforglipron.json` | the same for "orforglipron": the drug with no mechanism, and a salt of it under another name (2026-11-14) |
| `opentargets/drugs_semaglutide.json` | the same for "semaglutide": the drug with one mechanism naming one protein, and another drug of its class (2026-11-14) |
| `opentargets/drugs_trastuzumab_deruxtecan.json` | the same for "Trastuzumab deruxtecan": two mechanisms, one with a target that is no human gene product (2026-11-14) |
| `opentargets/drugs_salpingectomy.json` | the same for "Salpingectomy", a procedure: no hit (2026-11-14) |
| `opentargets/drug_tirzepatide.json`, `opentargets/drug_unknown.json` | the drug query for `CHEMBL4297839`, and for `CHEMBL0000000`, which the platform does not hold (2026-11-14) |
| `opentargets/target_unknown.json` | the target query for `ENSG00000000000`, which the platform does not hold (2026-11-14) |

Changes made to the recordings, for copyright and size:

- Europe PMC citing papers, `europepmc/paper_srep39654.json` and `europepmc/paper_sciadv_abf1798.json`: each `abstractText` is replaced by a placeholder sentence.
- `europepmc/paper_nejmoa2206038.json`: `abstractText` is replaced by a placeholder that keeps only the paper's registry number; subject headings, grants, links and all but two authors are removed.
- The five Europe PMC recordings of 2026-11-14: `abstractText` is replaced by a placeholder sentence, all but two authors are removed from `authorList`, and grants, chemicals, keywords, data links and comment lists are removed. `authorString` and `affiliation` are kept so that a test can show they are not stored.
- OpenAlex works: each `abstract_inverted_index` is replaced by a placeholder sentence. The key was sent in a header and is in no recording.
- MeSH: none. The records are NLM's own and are kept whole, re-indented.
- GSRS: none. The data is CC0 and the records are kept whole, re-indented.
- RxNorm: none. The answers are NLM's own and are kept whole, re-indented.
- Open Targets: none. The answers are kept whole, re-indented. Function descriptions are UniProt's (CC BY 4.0); a drug's kind of molecule and mechanisms are ChEMBL's (CC BY-SA 3.0 Unported).
- ROR: only the first two items of each answer are kept.
- Crossref works: `abstract` removed; `reference` removed from `work_srep39654.json`.
- `openai/decisions_three_records.json`: the model's name is replaced by `example-model` in the request and the response. The input is synthetic.

Never add news article text here. Article fixtures must be synthetic.
