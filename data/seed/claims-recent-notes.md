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

## What the first live run showed (2026-11-11)

Five claims were imported, drafted and searched with `openai:gpt-6-luna`.

- **Intervention names must be plain.** The registry search sends the whole name as the search term, so "Bepirovirsen (Hibsago)" and "VDPHL01 (oral minoxidil formulation, Veradermics)" found nothing. With "Bepirovirsen" and "VDPHL01" the same search found 13 and 4 trials. Twenty-three names in the CSV were shortened to the name alone; maker and mechanism stay in the summary.
- **Descriptive synonyms add noise.** The model recorded phrases such as "one-time CRISPR treatment" as other names for CTX310, and the search for them returned 84 unrelated trials. Match scoring ranked them all near zero, so nothing wrong was suggested, but each cost a model call.
- **Match scoring separated cleanly.** CTX310: 1 of 85 trial candidates scored above 0.5. Compound 991 (worms and flies only): 0 of 23, which is right.
- **Cost.** 140 model calls for five claims came to about $0.014.

## Assistant review for the local preview (2026-11-11)

The operator was away and asked the assistant to keep going until the proof of concept worked. Every decision below was recorded with the decider **assistant**, never as the operator's. Assistant-decided claims are left out of a normal export; they appear only in a preview export, where each page says no person has checked it. To make a decision your own, repeat it without `--as-assistant`.

### What the assistant did

- Imported all 46 claims, had the model read each article, and searched the registries for each claim.
- Approved a trial match when the model scored it 0.90 or more **and** the trial is for the claim's own condition. Rejected matches scored 0.10 or less, and strong matches for another condition. Left the rest pending.
- Read the registries for approved matches, confirmed the model's suggested evidence stage, and approved the claim.
- Entered two FDA approvals by hand from the FDA's own announcements, read on the day: bepirovirsen (2026-10-20) and zilganersen (2026-09-03).
- Gave nine claims an extra search name from its own knowledge, not from the article (for example CVN424 for solengepras, BPL-003 for mebufotenin, GS030 for the optogenetic therapy). They only widen the search; the matches they found were then judged like any other.

### What you should check first

- **The condition check is the assistant's, not the pipeline's.** Match scoring looks only at the treatment. For the Alzheimer's sleep finding in mice it proposed 31 trials of the laboratory drug (pexidartinib) in tumours, all scored 0.99; score alone would have shown a mouse finding as Phase 3. The assistant compared condition words by script, with a small list of lay and registry synonyms. This needs to become part of match scoring: a claim is one treatment for one condition.
- **"Preclinical only" on claims with human studies.** The status means no trial was found in the registries checked. It reads wrongly for `drug-resistant-epilepsy-gene-therapy` (three patients treated), `type-2-diabetes-remission-diet-exercise`, `bacterial-infection-ai-designed-phage` and `peanut-allergy-microneedle-stamp`. In each the treatment has no name a registry can be searched for. **Fixed 2026-11-12:** such a claim now has its own status, "No trial record found" (`no_trial_found`), decided by the confirmed evidence stage. "Preclinical only" is kept for laboratory and animal work. See `openspec/changes/no-trial-found-status`.
- **`dementia-lymphatic-venous-surgery` shows Phase 3** because one registered surgical trial carries that label. The rule is working as written; whether a phase label on a procedure should count is a question for the rules. **Checked 2026-11-12:** two registered trials of this surgery for Alzheimer's disease (NCT06530732, started, and NCT07060391) are labelled Phase 3 by their own sponsors, so the status repeats the registry. Left as it is.
- **Follow-up papers.** The assistant approved two low-confidence follow-up paper events without close reading (events 57 and 59) and rejected one that looked unrelated (58). They do not affect any status.
- **Left pending for you:** matches scored between 0.10 and 0.90, combination trials (for example `hepatitis-b-bepirovirsen` match 144, `ptsd-personalised-magnetic-stimulation` matches 454 and 458), basket trials, and one trial in women on the male-pattern-baldness claim (146).
- **Five articles were not read by the model.** The US Sun's robots.txt forbids automated reading and the pipeline respected it (three claims); two other pages would not load. Those claims have only what the CSV gave them.

### Not finished

Eight claims with broad names were still being searched when this was written, or their search was cut off: `biological-ageing-glp-1-drugs`, `pre-leukaemia-vitamin-c`, `stiff-person-syndrome-car-t`, `heart-failure-ipsc-heart-muscle-cells`, `type-2-diabetes-glucose-catalyst-implant`, `kidney-failure-pig-kidney-transplant`, `knee-osteoarthritis-genicular-artery-embolisation`, `muscle-loss-atr-258`. A broad name returns hundreds of loosely related trials and each is scored by a model call, one at a time. They are imported and pending.

Model use for the whole run: about 2,400 calls, $0.22.

### Outcome per claim

Columns: review state, status, evidence stage at announcement, approved matches, pending matches, approved events.

| Claim | State | Status | Stage | Matches | Pending | Events |
| --- | --- | --- | --- | --- | --- | --- |
| alexander-disease-zilganersen | approved | approved | late_human | 2 | 0 | 4 |
| hepatitis-b-bepirovirsen | approved | approved | late_human | 12 | 1 | 29 |
| cholesterol-crispr-ctx310 | approved | phase_1 | early_human | 2 | 0 | 2 |
| retinitis-pigmentosa-optogenetic-therapy | approved | phase_1 | early_human | 2 | 0 | 2 |
| depression-mebufotenin-nasal-spray | approved | phase_2 | early_human | 3 | 0 | 6 |
| malaria-cabamiquine-pyronaridine | approved | phase_2 | early_human | 2 | 1 | 8 |
| refractory-angina-coronary-sinus-reducer | approved | phase_2 | early_human | 12 | 1 | 24 |
| respiratory-viruses-inna-051-nasal-spray | approved | phase_2 | early_human | 3 | 0 | 7 |
| dementia-lymphatic-venous-surgery | approved | phase_3 | early_human | 13 | 3 | 17 |
| endometrial-cancer-sac-tmt | approved | phase_3 | late_human | 2 | 4 | 4 |
| hair-regrowth-vdphl01 | approved | phase_3 | late_human | 3 | 1 | 6 |
| low-back-pain-rexlemestrocel-l | approved | phase_3 | late_human | 2 | 0 | 6 |
| melanoma-mrna-vaccine-intismeran | approved | phase_3 | late_human | 3 | 1 | 6 |
| parkinsons-solengepras | approved | phase_3 | late_human | 4 | 0 | 14 |
| primary-aldosteronism-baxdrostat | approved | phase_3 | early_human | 3 | 0 | 7 |
| visceral-fat-cbl-514 | approved | phase_3 | early_human | 12 | 0 | 30 |
| alzheimers-nano-eraser | approved | preclinical_only | animal | 0 | 0 | 0 |
| alzheimers-nasal-spray-extracellular-vesicles | approved | preclinical_only | animal | 1 | 0 | 0 |
| alzheimers-sleep-microglia-removal | approved | preclinical_only | animal | 1 | 0 | 1 |
| bacterial-infection-ai-designed-phage | approved | preclinical_only | early_human | 0 | 0 | 0 |
| cell-rejuvenation-blood-to-neural-stem-cells | approved | preclinical_only | in_vitro | 1 | 0 | 0 |
| diffuse-midline-glioma-b-sync-car-t | approved | preclinical_only | animal | 1 | 0 | 0 |
| drug-resistant-epilepsy-gene-therapy | approved | preclinical_only | early_human | 0 | 0 | 0 |
| hair-regrowth-electric-comb | approved | preclinical_only | animal | 0 | 0 | 0 |
| heart-failure-temporary-gene-instructions | approved | preclinical_only | animal | 0 | 0 | 0 |
| lifespan-ampk-activator-991 | approved | preclinical_only | animal | 0 | 0 | 0 |
| mash-dt-109 | approved | preclinical_only | animal | 1 | 0 | 1 |
| multiple-sclerosis-kamuvudine-k-9 | approved | preclinical_only | animal | 0 | 0 | 0 |
| peanut-allergy-microneedle-stamp | approved | preclinical_only | early_human | 0 | 0 | 0 |
| senescent-cells-senomune-0257 | approved | preclinical_only | animal | 0 | 0 | 0 |
| spinal-cord-injury-engineered-implant | approved | preclinical_only | animal | 0 | 0 | 0 |
| superbugs-ancestral-antimicrobial-peptides | approved | preclinical_only | in_vitro | 1 | 0 | 0 |
| tauopathy-cxcr3-antibody | approved | preclinical_only | animal | 1 | 0 | 0 |
| type-2-diabetes-glp-1-secreting-bacteria | approved | preclinical_only | animal | 0 | 0 | 0 |
| type-2-diabetes-remission-diet-exercise | approved | preclinical_only | early_human | 1 | 3 | 0 |
| vre-vancomycin-click-chemistry-molecule | approved | preclinical_only | in_vitro | 0 | 0 | 0 |
| infertility-testicular-tissue-transplant | approved | trial_registered | early_human | 2 | 1 | 4 |
| ptsd-personalised-magnetic-stimulation | approved | trial_registered | early_human | 5 | 5 | 14 |
| biological-ageing-glp-1-drugs | pending | preclinical_only | - | 0 | 0 | 0 |
| heart-failure-ipsc-heart-muscle-cells | pending | preclinical_only | - | 0 | 0 | 0 |
| kidney-failure-pig-kidney-transplant | pending | preclinical_only | - | 0 | 439 | 0 |
| knee-osteoarthritis-genicular-artery-embolisation | pending | preclinical_only | - | 0 | 338 | 0 |
| muscle-loss-atr-258 | pending | preclinical_only | - | 0 | 0 | 0 |
| pre-leukaemia-vitamin-c | pending | preclinical_only | - | 0 | 0 | 0 |
| stiff-person-syndrome-car-t | pending | preclinical_only | - | 0 | 0 | 0 |
| type-2-diabetes-glucose-catalyst-implant | pending | preclinical_only | - | 0 | 399 | 0 |

## After the fixes (later on 2026-11-11)

- All 46 claims now have a status in the preview; the eight broad-name claims were searched again within their condition.
- Match scoring now asks about the treatment **and** the condition, and the search drops names that identify nothing. The assistant's word comparison is no longer needed for new searches. Candidates scored before the change are marked in the queue as scored without the indication.
- Measured on the same data: 78 candidates scored in 77 s (was 198 s); a typical claim searched and scored in 10 to 25 s; five claims read, searched and fetched side by side in 68 s. The first run took over an hour for 46 claims and never finished eight of them.
- Still the assistant's judgement, and worth your eye: which of several same-condition trials belong to a broad claim (`biological-ageing-glp-1-drugs`, `pre-leukaemia-vitamin-c`, `stiff-person-syndrome-car-t`, `knee-osteoarthritis-genicular-artery-embolisation`).
