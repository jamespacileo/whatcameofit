# Lookup: from a piece of text to trial records

`thenwhat lookup` takes the address of a news article, or pasted text, and returns the ClinicalTrials.gov records it is most likely about, likeliest first. It is the engine for answering "what came of this?" for an article the site does not track yet. Behaviour is specified in `openspec/changes/live-lookup`.

```sh
docker compose exec pipeline thenwhat lookup https://example.org/news/some-article
pbpaste | docker compose exec -T pipeline thenwhat lookup --paste        # a post, a headline, a paywalled article
docker compose exec pipeline thenwhat lookup --json https://example.org/news/some-article
```

The answer is a list of candidates for a person to check. It is not a status and nothing in it has been reviewed. No claim, match, article or text is stored.

There are two copies of the engine, kept in step by hand: the pipeline's (`thenwhat lookup`, Python, the operator's tool and the one measured below) and the site's (`site/worker/`, JavaScript, the one readers reach). The site's copy answers at `/api/lookup` and marks its answer as an automatic search. The visible-content change adds bounded image input and expiring structured results; see the current section below. Try it locally with `make lookup-dev`.

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

| | General model, one at a time | Decisions API, four outlets at a time |
| --- | --- | --- |
| Addresses asked for | 104, at 57 outlets | the same |
| Read | 96 (4 refused by robots.txt, 3 answered 403, 1 answered 429) | the same |
| Lookups run | 43 | 43 |
| An approved trial among the likely records | 32 (74%) | 35 (81%) |
| The first record listed is an approved trial | 29 (67%) | 30 (70%) |
| Time for the whole run | 21 minutes | 10 minutes 26 seconds |

The two runs gave the same found-or-not answer for 40 of the 43 articles. The second found three that the first missed and lost none; on one article an approved trial moved from first place to lower in the list. One run each way: the model does not answer the same way twice, so three articles is within what two runs of the same setup can differ by. The second run also had the registry's answers cached from the first, which is part of why it was faster. The files kept are from the second run.

What the pages carried, of the 96 read: a headline 96, a summary 93, a date 74, a link to a paper 41, the article as structured data 11, a registry number 3.

The misses (eleven in the first run, eight in the second) are the same kinds as before: the registry lists the drug under a code the article does not give (solengepras, cabamiquine), a broad name (GLP-1 drugs), a treatment with no product name (stem cell therapy for heart failure).

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

## Posts on social media

The address of a post works in place of an article's, on the platforms that offer posts to software without signing in: Bluesky, Hacker News and Mastodon servers. The post is read, the first article it links to is read as any article, and the two are looked up together. The answer says where it read from. If the article cannot be read, the lookup goes on from the post alone. On the site, a post that links to an article we track is answered with that claim's page, with no automatic search.

Tried on 2026-11-12 through the site's engine, one real post each:

| Platform | Linked article at | Result | Time |
| --- | --- | --- | --- |
| Bluesky | statnews.com | Read as gene therapy for Parkinson's disease; 54 records found, 10 likely | 20 s |
| Hacker News | broadinstitute.org | Read as an siRNA for prion disease. The article gives two registry numbers; the trial it names came first, agreeing on the trial's name and who ran it | 13 s |
| Mastodon server | doi.org | Read; not about a treatment, so the registry was not searched | 6 s |

X, Reddit, Facebook, Instagram, Threads, LinkedIn, Telegram, TikTok and YouTube are not read: their terms forbid it or they need an account the operator has not registered. For those the site names the platform, asks nothing of it, and offers to take the post's text or the article's address. The findings and the pages they rest on are in `docs/sources.md`.

Who wrote a post is never read out, and nothing of a post is stored.

### Through the browser extension

The extension covers what the site cannot read. On a page that is not tracked it offers a registry search of the open page: the reader's own browser reads the page, and the text and the links in it go to the same service. The site asks the platform nothing, and the page's address is not sent. This works for a post on any platform and for an article behind a paywall the reader subscribes to. Text the reader selects first is all that is sent of the page's words.

Tried on 2026-11-12 with the extension's page reader run on a real post on X: the post's words, its link card's headline and the outlet's name came through in three lines, without the writer's name, the time or the view count. The service answered in 8 seconds.

**Shortened links.** A post often links through a shortener, sometimes through two. The service follows one where the shortener's robots.txt allows (bit.ly, trib.al, tinyurl.com and buff.ly did on 2026-11-12), asking only for the redirect. X's own shortener (`t.co`) refuses software, but answers a browser with a small page that names the address. So the extension opens that one link in the reader's browser, without cookies or a referrer, and sends the address it names. It has permission for that host and the site's, and no other.

Tried on the same real post: X's shortener named a second, the publisher's; the service followed that to the article at statnews.com and read it. 21 seconds in all.

Limits: Reddit could not be opened in the browser used for this try, so its page is read by the general rule and has not been seen working. The popup has not yet been pressed in a real Chrome or Safari. A post on X pasted into the site, without the extension, is still turned back: only a browser can open X's links.

## Before it can serve readers

- **A reviewed test set.** The numbers above rest on the assistant's approvals. A few hundred article and trial pairs checked by a person, across many outlets, would make them trustworthy. Which outlets can be read is now recorded in [outlets.md](outlets.md), for the outlets that have a tracked article.
- **Drug-name synonyms** from an open source, checked for its terms first.
- **Posts on X and Reddit.** Both need the operator to register: Reddit an approved app, X a paid developer account. Until then a reader pastes the post's text.
- **The five decisions in `openspec/changes/live-lookup/design.md`:** whether an unreviewed answer may be shown publicly, where the lookup runs, how a blocked article is read, social posts by address, and the promise that a pasted link is not tracked.

## Visible content and on-demand results (13 November 2026)

Opening the extension still checks reviewed claims first. For untracked pages it checks a browser-local result and the shared service cache before a paid lookup. Visible media with too little useful text, or media accompanying a text reading that identifies no treatment, triggers one screenshot lookup automatically. This follows the operator's explicit preference. Selected text suppresses automatic capture.

The browser captures only the active tab and checks its identity before and after capture. It prefers the largest visible image/video/canvas, crops within the viewport, preserves aspect ratio, and reduces to at most 1600 pixels on either side and one megapixel. JPEG output is capped at 750,000 bytes. A video supplies one frame, not audio. Visible password/editing fields, overlapping embedded documents, private windows, internal/local addresses, tab switches and closing the popup prevent capture or sending. Browser restrictions still apply; this is not a guarantee of reading every app or protected video.

The Worker validates bounded PNG/JPEG input and passes it through the existing configured model's Chat Completions image input with high detail for embedded text. It neither fetches Reddit to obtain pixels nor follows raw image files as articles. Reading remains a bounded identification of what a report claims, never proof it works; a patch is not silently identified as a different antibody treatment for the same condition.

Local results expire after 24 hours and are capped at ten. Content changes/selection invalidate reuse; results display the earlier check time, and Search again bypasses reuse. Images and submitted text are never saved. Clear recently checked also clears the result cache.

`LOOKUP_RESULTS` is an optional Cloudflare KV binding. Shared entries expire after 24 hours and contain structured findings/source links, never copied report text, images, model gist or reader identity. Keys hash cleaned report addresses. Only content independently read anonymously by the service may seed the shared cache. Browser-only content, including Reddit screenshots that the service cannot independently verify as public, remains local. Website URL lookups populate the shared library on demand; no crawler or automatic human approval is introduced. A cache outage falls back to normal lookup. `/api/lookup` accepts `{pageUrl, cacheOnly:true}` to check without calling a model. Rate limits and the existing dedicated $13 project allowance apply; images use the same configured model and there are no paid retries.

The installed store build must be updated after these changes. Apple privacy disclosures must mention screenshot content before submission.

Before the first untracked lookup, the extension asks the reader to allow text, cleaned URLs and automatic screenshot fallback to be sent through the service to OpenAI. This choice is stored locally and can be withdrawn in Automatic search settings; reviewed claim matching remains available without it. Apple review guideline 5.1.2(i) requires explicit permission before third-party AI data sharing: https://developer.apple.com/app-store/review/guidelines/#data-use-and-sharing .

## Search phrases in resolution (13 November 2026)

Resolution, not the lookup. Until this date `thenwhat resolve` searched the registry only for an intervention's name and other names. A treatment that an article describes and does not name was searched for as described.

The claim `tourette-syndrome-wrist-nerve-stimulation` was the case that showed it. Its intervention is "Wrist-worn median nerve stimulation device". That search found three trials, none of them of the treatment (two nausea bands and a tremor device, scored 0.01 to 0.03 and rejected by rule), and the page said "No trial record found".

After the claim was given the search phrase "median nerve stimulation" with `thenwhat entity phrase`, one run of `thenwhat resolve` found three more trials within "Tourette syndrome":

| Trial | Sponsor | Score |
| --- | --- | --- |
| NCT05269953 | Nottingham University Hospitals NHS Trust | 0.98 |
| NCT05016765 | Washington University School of Medicine | 0.98 |
| NCT04731714 | Washington University School of Medicine | 0.80 |

All three are pending review; none is approved, so the page is unchanged. The report was of the Nottingham device. The two Washington University trials test the same kind of stimulation for the same condition with other equipment, and whether they belong to this claim is the reviewer's decision.

Limits: one claim, one run. A claim that is already decided is never read again, so it has a search phrase only when an operator gives it one. On this date no other decided claim had been given one.

### Search phrases for the claims already decided (13 November 2026)

`thenwhat entity phrases --missing` asked the model for search phrases for each of the 83 claims that had none, from what each claim says of itself (headline, summary, intervention, condition), not from its article. Each claim given a phrase was then resolved again with `--rescore`.

| | Count |
| --- | --- |
| Claims asked | 83 |
| Claims given at least one phrase | 50 |
| Claims where a phrase found a trial not found before | 15 |
| New trial candidates | 138 |
| Candidates approved by rule (0.8 or more) | 3, on 2 claims |
| Claims whose status changed | 0 |

The three approvals: two trials for `dementia-lymphatic-venous-surgery`, which already stood at Phase 3, and one for `type-2-diabetes-remission-diet-exercise`, which already had a registered trial. Most of the 138 new candidates scored low: a phrase such as "bacteriophage therapy" within a condition brings back trials of other treatments of the same kind, and the score for the claim's indication sorts them out.

Limits: one run, with one model. The phrases were not read one by one. Many are longer and more specific than a registry's own wording ("Autologous induced pluripotent stem cell-derived cardiomyocyte transplantation") and so found nothing; a shorter phrase might. Thirty-three claims were given none, most of them named drugs. The Tourette claim remains the only one whose status a phrase has changed.

## Related papers: the first measured run (14 November 2026)

`thenwhat resolve` was run on the real database for every approved claim whose status was "preclinical only" (43) or "No trial record found" (4): 47 claims, one after another, between 18:19 and 18:23 UTC, with the code at `main` 9a2e13b. Change `related-research`, tasks 8.1 and 8.2. A dump of the database from just before is kept outside the repository.

| | |
|---|---|
| Claims run | 47 |
| Completed | 46 |
| Stopped before the paper search | 1 (`periodontal-3d-printed-scaffold`: ClinicalTrials.gov answered 400 to its registry search) |
| Paper search found nothing | 25 |
| Paper search found papers | 21 |
| Paper candidates stored | 273 |
| Approved by rule (0.8 or more) | 33 |
| Rejected by rule (under 0.05) | 215 |
| Left pending | 25 |
| Approved with no reason found by rule | 4 |
| **Claims that gained an approved paper** | **14**, all "preclinical only" |
| **Claims that gained a trial candidate** | **0** |
| Claims whose status changed | 0 |
| Origin paper asked about | 6 claims |
| Origin paper set by rule | 4 (`alzheimers-nano-eraser`, `lifespan-ampk-activator-991`, `multiple-sclerosis-kamuvudine-k-9`, `obesity-tofa`) |
| Organisations matched in ROR | 110 of 179 institution and company entities, all pending |

**Spend.** 46 OpenAlex searches, one per claim: 0.046 US dollars of the day's free dollar, with 0.947 left at the end. The model answered 293 paper decisions and 7 origin-paper decisions in 29 calls for 0.0173 US dollars; both figures include the trial claim below. No prepaid credit was drawn on.

**What it shows.**

- None of the four "No trial record found" claims gained a paper, and no claim gained a trial candidate, so the run moved no claim off its status.
- Some approved papers report studies in people for claims whose status is "preclinical only": a first-in-human study for `dentine-regeneration-cpne7-peptide`, and a double-blind randomised trial for `periodontal-adipose-stem-cells`. Neither gave a registry number that Europe PMC's abstract holds, so neither became a trial candidate. A paper does not change a status; these two claims are worth the operator's look.
- One approved paper is a retracted one: its title begins "RETRACTED:" (`periodontal-maresin-resolvin-stem-cells`). The score does not know about retraction. It was not chosen as an origin paper, so no retraction event follows from it.
- Some approvals at 1.00 are about a neighbouring thing: papers on resolvin E1 alone for a claim about maresin and resolvin with stem cells, and a chitosan peptide paper for an amelogenin peptide claim. The titles were read once, by the assistant, not by the operator.
- More than half the searches (25 of 46) found nothing. The search asks for the intervention's names and phrases as exact phrases together with the indication as an exact phrase, and many of these claims have a long descriptive name and no search phrase that a paper would use. The remedy is a better search phrase (`thenwhat entity phrase`), not a looser search.
- Where papers were found, most were not about the claim: 215 of 273 scored under 0.05. Eleven claims had all twenty slots filled, mostly by rejected papers.
- The four origin papers set by rule let `thenwhat fetch` look for follow-up papers and retractions for claims whose article gave no DOI. `fetch` was not run here.
- The one claim that stopped did so in the registry search that comes first, on a term ClinicalTrials.gov refused. It has no paper candidates. That is a fault in the registry search, not in the paper search.

**The claim that stopped, later the same day.** The cause was one search phrase of thirteen words, which ClinicalTrials.gov answers with "Too complicated query". With the fix that reports such a term and searches the rest, `periodontal-3d-printed-scaffold` resolved: 3 paper candidates (1 approved by rule, 1 rejected, 1 pending) and 1 organisation matched. It is a "No trial record found" claim, so with it 15 of the 47 claims have an approved paper, one of them among the four with that status; its status did not change. The figures in the table above are the run as it happened and do not include it. The long phrase is still on the claim, not yet reworded.

**Before the run**, one claim was resolved alone to see the two new decision steps answer for the first time: `tourette-syndrome-wrist-nerve-stimulation`, whose status is "trial registered". It gained 20 paper candidates: 9 approved, 7 rejected and 4 pending. The reports of the Nottingham and Washington University trials scored 1.00; a commentary and unrelated neurophysiology papers were rejected. Its origin paper was left unset: "none" was the likeliest answer at 0.43.

**Approved by rule, rejected afterwards (task 8.2).** The rule approved 33 papers on the run (42 with the trial claim). The operator has rejected none yet, because none has been looked at. Nothing from the run is published: papers and organisations stay out of the export until they have their own section.

## Trial facts in the export (14 November 2026)

Openspec `trial-facts`. The export was built from the real database with the new code and every write rolled back, so the database was not changed. No request was made: the facts are read from the registry records already stored with each trial's events.

| | Count |
| --- | --- |
| Published claims | 84 |
| Claims with at least one trial | 37 |
| Trials listed | 222 |
| Trials with facts | 221 (the other is the seed claim's jRCT trial, entered by hand) |
| Trials with posted results for a primary outcome | 34 |
| Posted primary outcomes carried | 56 |
| Of those, reported in one row, so carried with their values | 43 |
| Of those, with a posted comparison | 16 |
| Registry records that raised no fact | 0 |
| Trials that state no number of participants | 2 |
| Lead sponsors that are a person, exported without a name | 14 |
| Events with a confidence below 1 (follow-up papers) | 3 |
| Export size before | 948,864 bytes |
| Export size after | 1,365,759 bytes |

What the trials state: 127 randomised, 25 not randomised, 69 with no allocation (one arm); 120 open label; 48 compared with placebo, 37 with another treatment, 18 with a sham procedure, 14 with no treatment, 1 with both a sham procedure and no treatment, and 103 with no comparator arm. State: 97 under way, 70 completed, 30 not started, 12 not given, 6 withdrawn, 4 terminated, 3 suspended. Sponsors: 108 companies, 95 universities, hospitals or other bodies, 14 individuals, 3 government bodies, 1 network.

Checked by hand against the registry's records as fetched the same day, number by number: NCT04494425 (866 participants; median 13.2 against 8.1 months; "<0.0001" by log rank), NCT05870540 (196 participants; two outcomes; "0.0033" by mixed models) and NCT02412735 (404 participants; three groups; two comparisons posted with no p value). Every participant count, group title, number analysed, value, spread, interval, p value and method agreed. The 74 distinct names of sponsors classed "other" were read: none is a person's.

Limits: the export grew by 44%, more than the quarter of a megabyte the design estimated. A trial's facts are as old as its newest stored record; the oldest was not measured. Thirteen of the 56 outcomes are reported in several rows and show a title and a row count only.

## Paper facts: the first fetch (14 November 2026)

Openspec `paper-facts`. Run on a copy of the real database made the same day (`thenwhat_paperfacts`), not on the real one: when it was run the change's migration was numbered 0009, as were two other branches' migrations, and the real database is shared between them (it is 0010 since the merge with `knowledge-cards`). The real database's `paper_record` table is filled by the first `thenwhat fetch` of each claim after this change is merged and migrated. The copy was fetched claim by claim, all 84 published claims, with the 24-hour HTTP cache as copied.

| | Count |
| --- | --- |
| Published claims fetched | 84 (none failed) |
| Paper records stored | 137 |
| Of those, held by Europe PMC | 136 |
| Of those, not held | 1 (an origin paper published in 2026, asked for by its DOI) |
| Europe PMC requests for a paper's record | 123 |
| Other Europe PMC requests in the run (citing papers of origin papers) | 6 |
| Time for the whole fetch, registry and Crossref requests included | 101 seconds |
| New evidence events the fetch also recorded | 4 |

What the 136 held records state:

| | Papers |
| --- | --- |
| Carry "Humans" or "Animals" | 108 (79%) |
| "Humans" | 99 |
| "Animals" | 30 |
| Both | 21 |
| Neither, or no subject headings yet | 28 |
| First kind other than article | 59: randomised trial 28, review 18, clinical trial 8, comment 3, observational study 1, preprint 1 |
| First kind article | 77 |
| No kind at all | 0 |
| Marked retracted | 0 |
| Marked open access | 63 |

More than half carry one of the two headings, so the claim page keeps its count of records in people and in animals as specified.

What the export built from the copy lists: 134 papers on 38 of the 84 claims. By role: 124 results papers of trials (49 listed by a sponsor, 75 linked by the registry), 19 origin papers and 3 follow-up papers; 2 papers play two roles and are listed once. No related paper: the copy was made before the literature search was first run on the real database, later the same day. The claim with the most papers has 29, all named by its trials' records. The export grew from 1,365,759 to 1,524,788 bytes.

Limits. Eight origin papers of claims with no trial are indexed with "Humans" as well as "Animals", which the index applies to work on human cells too: the page words the heading as how the index files the paper, not as a finding. A registry-linked paper may or may not be about its trial, in the registry's own words (`docs/sources.md`), and the page says so. The requests figure is lower than the papers stored because a DOI asked for in the last 24 hours was answered from the HTTP cache.

### Five built entries against their index pages (14 November 2026)

Openspec `paper-facts`, task 7.1, after `make check` passed. Five papers were picked from the export built from the copy, one for each of five first kinds, and each built entry was compared field by field with the paper's Europe PMC page and, for the fields that page does not display (publication types and subject headings), with its PubMed page, which shows the same NLM indexing.

| Paper | Title | Journal and year | Kind shown | People or animals | Open access |
| --- | --- | --- | --- | --- | --- |
| PubMed 26048637 | same | Drug and alcohol dependence, 2015: same | Report of a randomised trial: "Randomized Controlled Trial" | people: "Humans" | not marked; the page offers free full text, which is not an open access licence |
| PubMed 37499870 | same | Annals of oncology, 2023: same | Editorial, letter or comment: "Letter", "Comment" | people: "Humans" | not marked: none offered |
| PubMed 41325201 | same | Journal of visualized experiments, 2025: same | Journal article | animals: "Animals" | not marked; free full text |
| PubMed 33004510 | same | Science, 2020: same | Review: "Review" | both: "Animals", "Humans" | not marked; free full text |
| PubMed 36778375 | same | medRxiv, 2023: same | Preprint: "Preprint" | nothing said: no subject headings | marked open access |

No field differed, so no failing test was added. Two things a reader may notice: the entry gives a journal's name as the index record writes it ("Science (New York, N.Y.)", "Drug and alcohol dependence"), where the index's page capitalises or shortens it; and "open access" is the record's own mark, so a paper that is free to read at the index without an open access licence is not marked. None of the five is retracted, and none of the 136 records is, so the retracted mark was checked only on the recorded fixture of a known retracted paper.
