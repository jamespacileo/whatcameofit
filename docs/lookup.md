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

## Before it can serve readers

- **A reviewed test set.** The numbers above rest on the assistant's approvals. A few hundred article and trial pairs checked by a person, across many outlets, would make them trustworthy and show which outlets can be read at all.
- **Drug-name synonyms** from an open source, checked for its terms first.
- **Two lookups at once can collide** when both fetch the same registry page for the first time: one fails with a duplicate-key error (seen once in 168 lookups run four at a time). The registry cache needs to write with an upsert.
- **The five decisions in `openspec/changes/live-lookup/design.md`:** whether an unreviewed answer may be shown publicly, where the lookup runs, how a blocked article is read, social posts by address, and the promise that a pasted link is not tracked.
