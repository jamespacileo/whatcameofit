# Lookup: from a piece of text to trial records

`thenwhat lookup` takes the address of a news article, or pasted text, and returns the ClinicalTrials.gov records it is most likely about, likeliest first. It is the engine for answering "what came of this?" for an article the site does not track yet. Behaviour is specified in `openspec/changes/live-lookup`.

```sh
docker compose exec pipeline thenwhat lookup https://example.org/news/some-article
pbpaste | docker compose exec -T pipeline thenwhat lookup --paste        # a post, a headline, a paywalled article
docker compose exec pipeline thenwhat lookup --json https://example.org/news/some-article
```

The answer is a list of candidates for a person to check. It is not a status and nothing in it has been reviewed. No claim, match, article or text is stored.

There are two copies of the engine, kept in step by hand: the pipeline's (`thenwhat lookup`, Python, the operator's tool and the one measured below) and the site's (`site/worker/`, JavaScript, the one readers reach). The site's copy answers at `/api/lookup`, shows its answer on the home page marked as an automatic search, and stores nothing. Try it locally with `make lookup-dev`.

## How it works

1. **Read the page.** When the lookup starts from an address, the page is read for more than its visible text: the headline, summary and date from the tags it carries for other software, the article itself where the page carries it as structured data, and its links to papers (by DOI or PubMed number) and to registry records. The headline, summary and date are put before the article in what the model is shown.
2. **Read the text.** One model call names the treatment, the other names the text gives it, the condition, and up to three search phrases for a treatment with no product name. It also says what the text gives away about the trial itself: its name, its number of participants, who ran it. The model may add names it knows the treatment by; those are reported apart.
3. **Find.** Any registry number in the text or in a link is looked up directly. A linked paper (three at most) is looked up in Europe PMC, and the registry number in its abstract is looked up too. A trial the text names is searched for by that name. Every name of the treatment, every part of a combination ("A and B"), and every phrase is searched on ClinicalTrials.gov within the condition.
4. **Score.** Each record found (60 at most) is scored with the question used for a claim's candidates: is this a trial of this treatment for this condition? The same treatment for another condition is ranked below.
5. **Tell the trial from its siblings.** A treatment often has dozens of trials and the article is about one. Each record is compared by rule, not by the model, with what the text says of the trial: it carries the trial's name, its registered enrolment is within a tenth of the reported number of participants, its sponsor or a collaborator carries the named sponsor's words. A record the article gives the number of comes first. Then, among the records that read as trials of the treatment, those that agree with more come first. Each record lists why.
6. **Recognise.** A claim already tracked under one of the names is named.

## How well it works (measured 2026-11-12)

Test: for each of the 84 tracked claims, the lookup read the claim's earliest article by its address and its likely candidates (score 0.5 or more) were compared with the trials approved for that claim. The approvals were the assistant's, made with search names it added by hand, so this is a stand-in for a reviewed test set, not one.

| | First run | Second run (with names the model knows) |
| --- | --- | --- |
| Articles read (of 84) | 80 | 80 |
| Claims with approved trials whose article was read | 32 | 32 |
| At least one approved trial among the likely candidates | 23 (72%) | 23 (72%) |
| Every approved trial among them | 13 | 14 |
| The top candidate is an approved trial | 17 (53%) | 19 (59%) |
| Approved trials found | 114 of 152 (75%) | 111 of 152 (73%) |
| Seconds per lookup, middle value | 23 | 9 |

Four articles could not be read at their address (robots.txt or no response).

**Where it found more than the tracked pipeline:** search phrases found likely trials for claims that have none approved because their treatment has no product name: the wrist device for Tourette syndrome ("median nerve stimulation"), the diabetes diet and exercise programme, the spinal cord implant.

**Why it misses**, from the nine claims where no approved trial was found:

- **The registry uses a name the article does not give** (solengepras, mebufotenin, CTX310): the article has the generic name, the registry the development code. Letting the model add names it knows made no difference with the present model. A drug-name source that maps one to the other is the real fix.
- **A combination given as one name** ("cabamiquine and pyronaridine") found nothing. Each part is now searched as well. Checked live once: the parts were searched and 44 records came back, all correctly ranked low (another combination with pyronaridine). The claim's own trials were still missed, because the registry lists cabamiquine under its development code: the first cause again.
- **A broad name** (vitamin C, GLP-1 receptor agonists): hundreds of trials, and the condition as the article words it does not narrow them to the right ones.
- **The article is about more than one drug.** A patient feature on pancreatic cancer was read as being about a different drug than the claim's.
- **The model reads the condition strictly.** A trial in "overweight" was not counted for a claim about muscle loss, though it is the study the article reports.
- The two runs disagree on some claims: the model does not answer the same way twice.

## With the page's own signals (measured 2026-11-12, later the same day)

`thenwhat outlets --with-lookup` now makes this measurement and keeps it: [outlets.md](outlets.md) per outlet, [outlets-articles.csv](outlets-articles.csv) per address. It runs a lookup on every article that could be read and whose claim has approved trials, not only on each claim's earliest article, so its numbers are per article and are not the same count as the table above.

| | Per article |
| --- | --- |
| Addresses asked for | 104, at 57 outlets |
| Read | 96 (4 refused by robots.txt, 3 answered 403, 1 answered 429) |
| Lookups run | 43 |
| An approved trial among the likely records | 32 (74%) |
| The first record listed is an approved trial | 29 (67%) |

What the pages carried, of the 96 read: a headline 96, a summary 93, a date 74, a link to a paper 41, the article as structured data 11, a registry number 3.

The eleven misses are the same kinds as before: the registry lists the drug under a code the article does not give (solengepras, cabamiquine), a broad name (GLP-1 drugs), a treatment with no product name (stem cell therapy for heart failure).

## How long a lookup takes, and where the time goes

Measured on 2026-11-12 with the site's engine, the same articles each way:

| Article | Records scored | General model | Decisions API |
| --- | --- | --- | --- |
| Cancer vaccine (CNN) | 17 | 54 s | 37 s |
| GLP-1 drugs and ageing (CNN) | 60 | 60 s | 26 s |
| Parkinson's pill (Independent) | 5 | 10 s | 13 s |
| Stem cells for heart failure (Independent) | 2 | 11 s | 13 s |

Scoring is what the Decisions API speeds up (`DECISION_BACKEND=openai-decisions`, see `docs/sources.md`): sixty records took 3.2 seconds in one request, where the general model takes three calls of ten to twenty seconds each. A lookup with few records gains nothing, because scoring was never its slow part.

With scoring out of the way, one lookup's seconds went, in a run split by host:

| Step | 12 records | 60 records | 5 records |
| --- | --- | --- | --- |
| The article's own site | 64.1 | 8.8 | 1.3 |
| The model reading the article | 7.1 | 10.9 | 4.4 |
| ClinicalTrials.gov searches | 6.0 | 11.3 | 0.8 |
| Scoring (Decisions API) | 1.0 | 3.2 | 0.4 |

So what is left is the outlet's own speed (one site took a minute to answer after being asked several times that day), the one model call that reads the article, and the registry searches, which are kept to one at a time on purpose.

The model now reads the article while the linked papers and any stated registry numbers are looked up. `thenwhat outlets` checks four outlets at a time (`--workers`), with one shared turn-taker per registry so the registry's rate is kept however many lookups run.

## Before it can serve readers

- **A reviewed test set.** The numbers above rest on the assistant's approvals. A few hundred article and trial pairs checked by a person, across many outlets, would make them trustworthy. Which outlets can be read is now recorded in [outlets.md](outlets.md), for the outlets that have a tracked article.
- **Drug-name synonyms** from an open source, checked for its terms first.
- **Reading social media posts by their address**, and following the article a post links to. Not built; tasks 4c in the change.
- **The five decisions in `openspec/changes/live-lookup/design.md`:** whether an unreviewed answer may be shown publicly, where the lookup runs, how a blocked article is read, social posts by address, and the promise that a pasted link is not tracked.
