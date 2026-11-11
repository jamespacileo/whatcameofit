# Notes for claims-recent.csv

Compiled 2026-11-11 by an AI assistant and three research sub-agents. Not reviewed by a human. Every row is a pending draft.

## Brief

The operator asked for popular news articles from the last three months that report miraculous-sounding cures, across a wide range of conditions, including articles with clickbait titles. Window: 2026-08-11 to 2026-11-11.

## Method

- Leads came from web searches by condition, and from sub-agents that swept UK mainstream outlets (The Guardian, The Independent), popular-science sites (New Atlas, ScienceAlert, Futurism) and mass-market outlets (The US Sun, Daily Express, Fox News, LADbible, Daily Mail) through their feeds, sitemaps and section pages.
- Every candidate page was opened. Title and publication date were read from the page itself (visible date, `<time>` element or page metadata), never from a search-result snippet.
- After the CSV was written, a script fetched all 53 URLs again: all returned 200, every `article_title` was found in its page, and every `published_date` was found in its page.
- Headlines and summaries are paraphrases, written to describe what was done and in whom. No article text was copied. `article_title` is the outlet's own wording and is often stronger than the summary.
- `promise` is filled only where the article states a timeline (6 rows).
- Import check against a scratch database: `Imported 46 claims, 53 articles and 6 promises.`
- "Popular" was judged by the outlet and by how many outlets carried the story. No popularity figure was recorded: Reddit refused automated reads, so no scores were seen.

## Coverage

46 claims, 53 articles, 13 topics.

| Topic | Claims |
| --- | --- |
| Ageing | 4 |
| Allergies | 1 |
| Brain and nerves | 6 |
| Cancer | 4 |
| Dementia | 5 |
| Diabetes and metabolism | 6 |
| Hair loss | 2 |
| Heart and circulation | 5 |
| Infections | 6 |
| Mental health | 2 |
| Pain | 2 |
| Sight and hearing | 1 |
| Transplants | 2 |

Outlets (25): ScienceDaily, SciTechDaily, ScienceAlert, New Atlas, Medical Xpress, The Guardian, The Independent, CNN, Fox News, TIME, MIT Technology Review, VICE, LADbible, The US Sun, Daily Express, Futurism, ZME Science, Earth.com, Yahoo News, Medscape, Business Today, Courthouse News Service, Extra.ie, Inside Precision Medicine, American Friends of Tel Aviv University.

Not covered: BBC News (its article pages could not be reached through search or feeds), The Telegraph and The Times (blocked or paywalled), The Mirror, Daily Star, Metro and New York Post (little beyond lifestyle stories, or no way to scan by date).

## Daily Mail rows left out

The Daily Mail answered a sub-agent's first requests, then denied access (403) to it, to the checking script and to a normal browser. Three rows the sub-agent read could not be re-checked, so they are not in the CSV. The pipeline's own article fetch will probably be refused too. Add them by hand if wanted, after opening each page:

| Would attach to | Date seen | Title seen | URL |
| --- | --- | --- | --- |
| `primary-aldosteronism-baxdrostat` (would become its first report) | 2026-11-07 | Heart pill hailed as 'Holy Grail' after high blood pressure patients were effectively cured of deadly condition in pivotal trial | https://www.dailymail.co.uk/health/article-16271133/Heart-pill-hailed-Holy-Grail-high-blood-pressure-patients-effectively-cured-deadly-co |
| `lifespan-ampk-activator-991` (the original of the LADbible report) | 2026-09-30 | Scientists create anti-aging holy grail drug that extends lifespan by 25% in some animals - and they say it could work in humans too | https://www.dailymail.co.uk/sciencetech/article-16168953/anti-aging-holy-grail-drug-lifespan.html |
| new claim: ALKS 7290 for ADHD, early trial | 2026-09-26 | The breakthrough ADHD drug that can ease symptoms WITHOUT the risk of heart complications | https://www.dailymail.co.uk/health/article-16162309/adhd-breakthrough-drug-ease-symptoms-heart.html |

## Dates

- ScienceDaily rows use the page's "Date:" field. The date in the URL is one or more days earlier.
- New Atlas rows use the byline date. The page metadata is one day later because it is in UTC.
- `hair-regrowth-vdphl01`: the page shows 27 October 2026 in US Eastern time and 28 October in UTC. The local date was used.
- `vre-vancomycin-click-chemistry-molecule`: the page's structured data says 2026-09-05 and another metadata field says 6 September. The structured-data date was used.
- `heart-failure-temporary-gene-instructions`: the Extra.ie article is dated 2026-11-11, but The Telegraph ran the story on 2026-11-09 and could not be opened. The first-reported date is probably two days earlier than recorded.

## Promise dates set by hand

| Slug | Wording in the article | Date recorded |
| --- | --- | --- |
| `senescent-cells-senomune-0257` | human evaluation before the end of 2026 | 2026-12-31 |
| `diffuse-midline-glioma-b-sync-car-t` | trials could begin as early as April 2027 | 2027-04-30 |
| `respiratory-viruses-inna-051-nasal-spray` | asthma trial due to start in early 2027 | 2027-06-30 |
| `low-back-pain-rexlemestrocel-l` | result known by mid-2027 | 2027-06-30 |
| `primary-aldosteronism-baxdrostat` | could reach the NHS next year | 2027-12-31 |
| `parkinsons-solengepras` | could be prescribed within three years | 2029-10-07 |

"As early as" and "early 2027" are not deadlines. Decide whether each should carry a date at all.

## Points for the reviewer

Scope: is this a claim (one intervention for one indication)?

- `cell-rejuvenation-blood-to-neural-stem-cells`: a laboratory method presented as a research tool, not a treatment.
- `superbugs-ancestral-antimicrobial-peptides`: a family of reconstructed peptides, presented as clues for drug design.
- `biological-ageing-glp-1-drugs`: a class of drugs, two companies, and "ageing" is not a registered indication. The figures are the companies' own.
- `type-2-diabetes-remission-diet-exercise`: a lifestyle programme, not a product.
- `lifespan-ampk-activator-991`: yeast, worms and flies only. LADbible credits the Daily Mail for the story.
- `bacterial-infection-ai-designed-phage`: one unnamed patient, self-published by the company, infection not specified.
- `kidney-failure-pig-kidney-transplant` and `infertility-testicular-tissue-transplant`: single patients. The second has no result yet.
- `spinal-cord-injury-engineered-implant`: an announcement of preparation. The source is a university fundraising body's news page.

Evidence that needs a close look:

- `ptsd-personalised-magnetic-stimulation`: the 68% remission figure is the company's, and the full findings were unpublished. "FDA clearance" of a device is not a drug approval; check what the status rules make of it.
- `hepatitis-b-bepirovirsen` and `alexander-disease-zilganersen`: both articles report an FDA approval. These should resolve to regulator records and may reach the approved status.
- `pre-leukaemia-vitamin-c`: the survival figure is from an exploratory analysis.
- `endometrial-cancer-sac-tmt`: the summary is deliberately thin. The trial phase and survival figures were seen only in a search summary, not in the page text read.

Details not read directly from the article page:

- `depression-mebufotenin-nasal-spray`: "within a day" in the headline came from a search summary of the study.
- `melanoma-mrna-vaccine-intismeran`: "Phase 3" and "than with pembrolizumab alone" came from search summaries. The CNN page says "late-stage".
- `hair-regrowth-electric-comb`: "induced pattern hair loss" came from a search summary.
- `cell-rejuvenation-blood-to-neural-stem-cells` and `alzheimers-sleep-microglia-removal`: the journal names seen in search summaries were left out of the summaries for that reason.
- The ten Guardian and Independent rows, the eight New Atlas, ScienceAlert and Futurism rows and the six US Sun, Daily Express, Fox News and LADbible rows were read by sub-agents. Their titles and dates were re-checked by the script; the facts in their summaries were not re-read.
- `dementia-lymphatic-venous-surgery`, `peanut-allergy-microneedle-stamp` and `visceral-fat-cbl-514`: the sub-agent could not read trial sizes on every page; the summaries say only what it saw.

Possible overlap:

- `alzheimers-nano-eraser`, `alzheimers-nasal-spray-extracellular-vesicles`, `alzheimers-sleep-microglia-removal`, `tauopathy-cxcr3-antibody` and `dementia-lymphatic-venous-surgery` share the indication area but differ in intervention.
- `parkinsons-solengepras` has two reports of the same trial (The Independent and the Daily Express, which says it follows the Daily Mail).
- `heart-failure-temporary-gene-instructions` and `heart-failure-ipsc-heart-muscle-cells` are different interventions for heart failure.

## Leads dropped

- Outside the window: Gladstone spinal neurons in rats (2026-08-05); daraxonrasib for pancreatic cancer (2026-06-01); sugar gel for hair loss (2025 and June 2026 reprints); hair serum from Taiwan (2025); universal nasal vaccine (2026-03-04); OTOF deafness gene therapy (April 2026); HIV remission reports (May to July 2026).
- No single intervention: "hidden immune weapon" against small cell lung cancer (ScienceDaily and New Atlas); repurposed drugs for Sanfilippo syndrome (laboratory cells, several drugs, title overstates); phage therapy in general (Daily Mail, 2026-11-03).
- Intervention not identified: the Daily Mail's "Ozempic of autism" article (2026-10-26). The sub-agent could not read the drug's name before access was denied.
- No fitting topic, kept as a spare: acebilustat for leg lymphoedema (Daily Mail, 2026-10-01, 23 patients).
- Could not be dated or opened: Brock University Alzheimer's release (403); Telegraph and BBC leads listed under Coverage.
- Stage unclear from the text read: prime editing for Wilson disease (The Independent, 2026-10-23); niclosamide-based drug for endometriosis (The Independent, 2026-10-02); liver drug in ageing rats (ScienceAlert, 2026-11-07, drug not named).
- Not cure-shaped: late-window thrombectomy for stroke; AI exoskeleton for gait training; fetal tumour ablation (single case, no product to track).
- Unreliable source: a blog post claiming a thought-controlled walking implant in "12,000+ patients".
