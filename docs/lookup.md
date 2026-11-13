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
