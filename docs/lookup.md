# Lookup: from a piece of text to trial records

`thenwhat lookup` takes the address of a news article, or pasted text, and returns the ClinicalTrials.gov records it is most likely about, likeliest first. It is the engine for answering "what came of this?" for an article the site does not track yet. Behaviour is specified in `openspec/changes/live-lookup`.

```sh
docker compose exec pipeline thenwhat lookup https://example.org/news/some-article
pbpaste | docker compose exec -T pipeline thenwhat lookup --paste        # a post, a headline, a paywalled article
docker compose exec pipeline thenwhat lookup --json https://example.org/news/some-article
```

The answer is a list of candidates for a person to check. It is not a status and nothing in it has been reviewed. No claim, match, article or text is stored.

## How it works

1. **Read.** One model call names the treatment, the other names the text gives it, the condition, and up to three search phrases for a treatment with no product name. The model may also add names it knows the treatment by; those are reported apart.
2. **Find.** Any registry number in the text is looked up directly. Every name, every part of a combination ("A and B"), and every phrase is searched on ClinicalTrials.gov within the condition.
3. **Rank.** Each record found (60 at most) is scored with the question used for a claim's candidates: is this a trial of this treatment for this condition? The same treatment for another condition is ranked below.
4. **Recognise.** A claim already tracked under one of the names is named.

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
- **A combination given as one name** ("cabamiquine and pyronaridine") found nothing. Each part is now searched as well; tested, not yet measured again.
- **A broad name** (vitamin C, GLP-1 receptor agonists): hundreds of trials, and the condition as the article words it does not narrow them to the right ones.
- **The article is about more than one drug.** A patient feature on pancreatic cancer was read as being about a different drug than the claim's.
- **The model reads the condition strictly.** A trial in "overweight" was not counted for a claim about muscle loss, though it is the study the article reports.
- The two runs disagree on some claims: the model does not answer the same way twice.

## Before it can serve readers

- **A reviewed test set.** The numbers above rest on the assistant's approvals. A few hundred article and trial pairs checked by a person, across many outlets, would make them trustworthy and show which outlets can be read at all.
- **Drug-name synonyms** from an open source, checked for its terms first.
- **Two lookups at once can collide** when both fetch the same registry page for the first time: one fails with a duplicate-key error (seen once in 168 lookups run four at a time). The registry cache needs to write with an upsert.
- **The five decisions in `openspec/changes/live-lookup/design.md`:** whether an unreviewed answer may be shown publicly, where the lookup runs, how a blocked article is read, social posts by address, and the promise that a pasted link is not tracked.
