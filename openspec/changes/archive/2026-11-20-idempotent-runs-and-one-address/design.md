# Design

## Context

A link lead is kept once per address key (`link_lead.url_key`, unique). The key is made by `pipeline/src/thenwhat/backfill/address.py`, which is the site's `site/src/lib/article-key.mjs` in Python; the extension's build copies the site's file. One cases file (`site/tests/fixtures/article-key-cases.json`) is read by the site's test and the pipeline's test, so the two cannot drift. The work ledger (`backfill/ledger.py`, `backfill/runner.py`, table `work_entry`) holds one entry per record, step and step version with a fingerprint of what the step read; a record is due when it has no entry at the current version, when its entry is stale, or when it failed with attempts left.

All counts below were taken on 2026-11-16 from the working database with `SELECT` only, in a session opened read-only. Addresses are the only thing quoted.

## What was measured

### Leads that share an article

Stored key against the key recomputed from the stored address, with the rules as they were: 0 of 612,148 differ. The forms the key already folds are common and make no second lead:

| Form of the stored address | Leads |
| --- | --- |
| `www.` host | 417,821 |
| trailing slash | 177,011 |
| `http` scheme | 91,222 |
| `bbc.co.uk` | 10,619 |
| a listed tracking parameter | 7,046 |
| a fragment | 4,397 |
| `m.`, `mobile.`, `amp.` or `edition.` host | 3,693 |
| an AMP path | 669 |

With the stricter key of this change, 21,946 leads get another key and 5,756 of them meet a lead that already has it (4,773 articles):

| Kind | Articles | Leads too many | Examples |
| --- | --- | --- | --- |
| tracking parameter not known to the key | 4,392 | 5,367 | `axios.com/2025/05/28/ai-jobs-white-collar-unemployment-anthropic` with and without `?trk=feed_main-feed-card_feed-article-content`; `newyorker.com/books/page-turner/a-guide-to-thesis-writing-that-is-a-guide-to-life` and `?intcid=mod-latest`; `nytimes.com/2016/11/10/science/wireless-brain-spine-connection-paralysis.html` and `?hp&action=click&pgtype=Homepage&clickSource=story-heading&module=first-column-region&region=top-news&WT.nav=top-news`; `statnews.com/2020/05/19/vaccine-experts-say-moderna-didnt-produce-data-critical-to-assessing-covid-19-vaccine/` and `?mod=article_inline`; `en.andros.dev/blog/54572bc7/finger-the-1971-social-network-that-never-died/` and `?_hsenc=…&_hsmi=436773493` |
| edition, text or renamed host, or a stray dot | 297 | 302 | `www.reuters.com./technology/…-2026-11-12/` and `www.reuters.com/…`; `old.reddit.com/r/ClaudeCode/comments/1w3rxkj/…` and `www.reddit.com/…`; `uk.businessinsider.com/startup-pitch-deck-front-fundraising-venture-2018-6` and `www.businessinsider.com/…`; `motherboard.vice.com/en_us/article/8xyq8v/how-to-unlock-icloud-stolen-iphone` and `www.vice.com/…`; `edition-m.cnn.com/2019/01/11/asia/university-california-china-wechat-intl/index.html` and `www.cnn.com/…` |
| doubled slash, or letter case of an escape | 81 | 81 | `politico.com/news/magazine/2025/04/02//trump-musk-leaving-political-liability-00265784` and `…/02/trump-…`; `arstechnica.com/science/2019/06/…-ocean-co%e2%82%82/` and `…co%E2%82%82/`; `arstechnica.com/science/2018/06/splitting-water-for-fuel-while-removing-co%E2%82%82-from-the-air/` in both cases; `politico.com//magazine/story/2015/08/how-google-could-rig-the-2016-election-121548.html` and `politico.com/magazine/…`; `technologyreview.com//news/543511/…` and `technologyreview.com/news/543511/…` |
| two of the above | 3 | 6 | `krugman.blogs.nytimes.com//2015/04/10/apple-and-the-self-surveillance-state/`, the same with one slash, and with `?_r=0` |

AMP caches (`cdn.ampproject.org`, `google.com/amp/`) hold no lead. Of the hosts that say "mobile" in another way, `lite.cnn.com` has 1,134 leads, `www-m.cnn.com` 53 and `edition-m.cnn.com` 36.

What those duplicates cost: in 4,353 of the 4,773 articles two or more leads carry a triage score (5,313 scores bought twice). In 7 the page was read twice. In 2 the two reads made or joined two different claims.

Looked at and left alone, because two addresses that differ this way can be two articles:

- letter case in the path (52 leads): `github.com/kOlapsis/maintenant` and `github.com/kolapsis/maintenant`.
- a page suffix (116 leads): `softwaredoug.com/blog/2026/08/29/ai-team-mistakes` and `….html`.
- every parameter on a news outlet. `nytimes.com/movie/review?res=9B06…` and `wired.com/?p=1951313` name their article in a parameter, so parameters are dropped by name, and an outlet's own names (`mod` on wsj.com) only on that outlet.

### Source articles and article leads

- 1,897 source articles have 1,854 distinct keys.
- 38 articles are a source article of two claims (76 rows); in 3 both claims are live. Examples: `theatlantic.com/health/archive/2024/02/ozempics-muscle-loss-problem/677326/` on claims 472 and 509; `ctvnews.ca/health/article/health-canada-approves-ozempic-to-reduce-kidney-deterioration-in-people-with-diabetes/` and `cnbc.com/2025/01/28/novo-nordisks-ozempic-wins-fda-approval-for-chronic-kidney-disease.html` on 531 and 554; `finance.yahoo.com/news/shares-dialysis-providers-drop-ozempics-100259954.html` on 548 and 554; `biospace.com/novo-s-wegovy-shows-stronger-weight-loss-effects-in-women-than-men-study` on 533 and 550. One article reporting two claims is allowed; these are listed for the audit, not as errors.
- 2 of the 38 are under different address forms: `wired.com/2016/11/china-used-crispr-fight-cancer-real-live-human/` with and without `?mbid=social_fb`; `sciencealert.com/potential-new-vaccine-blocks-every-strain-of-hiv` with and without `?amp%3Butm_campaign=InArticleReadMore`.
- 5 claims hold one article twice: `www-m.cnn.com/2019/07/27/health/doug-lindsay-invented-surgery-trnd/index.html` and `www.cnn.com/…`; `statnews.com/2020/05/19/vaccine-experts-say-moderna-…/` and `?mod=article_inline`; `nytimes.com/2016/07/12/health/silver-diamine-fluoride-dentist-cavities.html` and `?_r=0`; `nytimes.com/2015/05/21/technology/a-bionic-approach-to-prosthetics-controlled-by-thought.html` and `?hp=&action=click…`; `nytimes.com/2016/11/10/science/wireless-brain-spine-connection-paralysis.html` and `?hp=&action=click…`. Each came from two leads that were both read.
- 115 trials hold one article twice among 44,166 article leads (121 rows too many), for example `dailymail.co.uk/health/article-2909895/….html` with and without `?ITO=1490&ns_mchannel=rss&ns_campaign=1490`, and `biospace.com/article/releases/merck-announces-fourth-quarter-and-full-year-2020-financial-results` with and without a trailing slash. `article_lead` is unique on the trial and the address as written.

### Shorteners, redirectors and archive links

| Kind | Leads | Examples |
| --- | --- | --- |
| an outlet's own shortener | 125 | `on.wsj.com/1P7ocsD`, `on.wsj.com/1dYGaRp`, `on.ft.com/1e7Dpg7`, `on.ft.com/2cb9xig` (74 and 51 leads) |
| a redirect that names where it leads | 3 | `google.com/url?q=https://amp.dw.com/en/…`, `google.com/url?q=https%3A%2F%2Fwww.crunchbase.com%2Forganization%2Fexxogen&sa=D…` |
| an archive copy that names the original | 68 | `web.archive.org/web/20170110111518/https://theintercept.com/2017/01/10/the-crimes-of-seal-team-6/`, `web.archive.org/web/20210831172631/http://playgo.to/iwtg/en/`, `web.archive.org/web/20190304060138/http://notes-taken.blogspot.com/2010/05/cahiers-pour-lanalyse-online-edition.html`, `web.archive.org/web/20100821132944/https://www.idc.iitb.ac.in/events/Indian_Rupee_Symbol.pdf`, `web.archive.org/web/20090708171122/https://michaelcrichton.sweb.cz/` |
| `t.co`, `bit.ly`, `lnkd.in`, `news.google.com`, `apple.news`, `archive.ph` and its other names | 0 | |

`archive.org/details/…` (62 leads) is an item of the archive itself, not a copy of a page. `news.yahoo.com` (946) and `msn.com` (64) republish articles under their own addresses and redirect nowhere.

## What a second run does today

"Spend" is a model call or a request that counts against an allowance.

| Step | A second run with the same or overlapping input | Where |
| --- | --- | --- |
| `load-links` | **Skips.** A post already stored adds nothing and is counted as already stored: the lead by its unique key, the share by lead, platform, community and time. The whole file is read again, a thousand posts to a transaction; no request, no spend. Two things depend on the order files are loaded in: the lead keeps the address of whichever share was loaded first, and a share's score is the one first loaded. An earlier share with another title changes the lead's title and makes it due for triage again, which is the ledger working as specified. | `backfill/link_load.py`, `store` |
| `load-trials` | **Repeats requests, writes nothing twice.** It asks the registry's API; pages are not cached, so a full reload asks for every page again within the allowance. Trials are stored once by registry and id; an unchanged trial is counted as "already stored". Only a trial whose search name or indication changed is due for `news_search` again. `--changes-only` asks from the last completed load; a load that was stopped starts at the first page. | `backfill/registry_load.py:118-135,159-187` |
| `link_screen` | **Skips** finished leads; no spend at all. It reads the stored claims and trials once per run, so a claim added later is seen by leads screened later, not by leads already screened. | `backfill/link_screen.py`, `LinkScreen` |
| `link_triage` | **Skips** every lead scored at the current step version. A lead is scored again only when its title, outlet or year of first share changed, or the version was raised. A batch whose transaction is lost after the model answered is asked again: 20 headlines at most. **It paid twice for 5,313 leads because one article had two leads**; this change removes the cause. | `backfill/link_triage.py`, `backfill/ledger.py:due_records`, `backfill/runner.py:process_batch` |
| `link_read` | **Skips** leads with a finished outcome. **Repeats spend** in three cases. (a) A read that fails is due again while attempts remain, and the next attempt asks the reader, the extraction and every decision again: nothing of the first attempt is kept. (b) When the reader says "not now" the request and its allowance are spent and nothing is recorded; within a run an outlet is left after three, across runs there is no limit. (c) A lead made due again (a raised version, `retry-outlet`) is read in full again unless its article became a source article, which is found before any request. An article with two leads was read twice (7 times); this change removes that cause. | `backfill/link_read.py:535-583,617,655,773`, `runner.py:_process_record` |
| `prepare` | `--pending` **skips** claims already decided. For a claim still pending it repeats registry searches (answered from the 24-hour request cache, real requests after that), and asks a model only for candidates, terms and readings it has no answer for. **Repeats spend** in one case: when a scoring call fails, every candidate of that run is withdrawn, including those earlier batches of the same run had scored, and the next run pays for them again. | `prepare.py:48-66,104-105`, `resolve/service.py:182-194,237-241`, `resolve/papers.py:189-193`, `resolve/named.py:125-129` |
| `audit clear` | **Refuses.** Clearing a claim that is not held writes nothing and says so. No request, no model. | `claims/entry.py:575-585`, `cli/audit.py:50-64` |
| `export` | **Same result**, apart from `generated_at`. The first export of a claim writes its `published_at`; a status that depends on the date can change on a later day, by rule. No request, no model. One query has no stated order: the claim's intervention entity is taken with `.first()`, which is the same row every time only while a claim has one. | `export/build.py:1224-1228,1244-1248,1346,1407-1409` |

Nothing in the decision layer answers from an earlier answer (`decide/core.py:113-225`, `llm/client.py:68-169`): reuse is each caller's, by ledger entry, by stored row or by input hash. `work-reuse-and-metrics` designs stored results under one key (its tasks 4.1 to 4.6, not built); cases (a) and (c) of `link_read` are answered there.

## Decisions

### 1. One comparison, stricter, with a version

The rules added, each in both files and in the cases file:

- **Tracking parameters by name**, everywhere: `_r`, `pgtype`, `wt.*`, `mbid`, `intcid`, `fsrc`, `trk`, `_hsenc`, `_hsmi`, `mkt_tok`, `gbraid`, `postshare`, `wpisrc`, `sharetoken` and the rest of the list in the code. Each was seen separating two leads of one article.
- **An outlet's own parameters, on that outlet only**: `action`, `module`, `region`, `version`, `hp`, `referer`, `nl`, `te`, `src`, `pagewanted` on nytimes.com; `mod` on wsj.com and statnews.com; `single_page` on theatlantic.com; `currentpage` on newyorker.com; `tid`, `noredirect` on washingtonpost.com; `frsc`, `cid1` on economist.com. On any other site `index.php?action=view` keeps its parameter.
- **A parameter name that kept the `amp;` of an `&amp;`** is read without it.
- **Hosts that serve one site under two names**, by a fixed list of pairs each seen serving one article at one path: editions (`uk.` and `nordic.businessinsider.com`, `us.cnn.com`, `eu.usatoday.com`, `europe.newsweek.com`), mobile and text forms (`lite.`, `www-m.`, `edition-m.cnn.com`, `text.npr.org`), earlier names (`motherboard.` and `tonic.vice.com`, `beta.` hosts of four outlets, `social.techcrunch.com`, `institutions.newscientist.com`, `prime.nautil.us`, `next.ft.com`, `x.com` for `twitter.com`, `old.reddit.com`). No rule for a label in general: `lite.` or `uk.` on a site not listed stays its own host. The table under "Evidence for each host pair" gives the count for every pair; a pair with no article seen at one path on both hosts is not on the list (`new.` and `np.reddit.com` were proposed and dropped: no lead is on either).
- **A leading or trailing dot on the host, doubled slashes in the path, and the letter case of an escape.** The dot is removed before anything else reads the host, so a YouTube address with one is still its video.
- **Two differences between the two files that no case covered**, found in review and closed here. Parameter names are now sorted by character code in both (the site used the locale's order, which puts `_` and `-` before digits; the pipeline used a caseless order). The path is now escaped alike: the site escapes `[ ] | ^`, which a browser leaves as they are, and the pipeline works out `.` and `..` parts and reads `\` as `/`, as a browser does. Each has a case in the shared file.

`KEY_VERSION` in `address.py` is raised with any change that gives a stored address another key. It is 2 with this change.

Alternative considered: dropping every parameter on listed news outlets. It folds 7,913 leads instead of 5,367 but would fold `nytimes.com/movie/review?res=…` pages into one. Not taken.

### Evidence for each host pair

Leads on the first host, and how many of their paths are also the path of a lead on the second (working database, 2026-11-16):

| Host | Counted as | Leads | Same path on both |
| --- | --- | --- | --- |
| `bbc.co.uk` | `bbc.com` | 10,482 | 8 |
| `us.cnn.com` | `cnn.com` | 40 | 14 |
| `lite.cnn.com` | `cnn.com` | 1,132 | 4 |
| `www-m.cnn.com` | `cnn.com` | 53 | 20 |
| `edition-m.cnn.com` | `cnn.com` | 36 | 10 |
| `uk.businessinsider.com` | `businessinsider.com` | 614 | 164 |
| `nordic.businessinsider.com` | `businessinsider.com` | 58 | 12 |
| `beta.washingtonpost.com` | `washingtonpost.com` | 23 | 12 |
| `beta.techcrunch.com` | `techcrunch.com` | 26 | 11 |
| `social.techcrunch.com` | `techcrunch.com` | 17 | 9 |
| `eu.usatoday.com` | `usatoday.com` | 54 | 13 |
| `text.npr.org` | `npr.org` | 244 | 10 |
| `motherboard.vice.com` | `vice.com` | 3,182 | 18 |
| `tonic.vice.com` | `vice.com` | 22 | 2 |
| `europe.newsweek.com` | `newsweek.com` | 36 | 3 |
| `institutions.newscientist.com` | `newscientist.com` | 4 | 4 |
| `beta.scmp.com` | `scmp.com` | 15 | 3 |
| `beta.latimes.com` | `latimes.com` | 18 | 2 |
| `next.ft.com` | `ft.com` | 55 | 1 |
| `prime.nautil.us` | `nautil.us` | 14 | 8 |
| `x.com` | `twitter.com` | 46 | 2 |
| `old.reddit.com` | `reddit.com` | 41 | 4 |

For example `social.techcrunch.com/2019/01/10/improbable-and-epic-games-establish-25m-fund-…` and `techcrunch.com/2019/01/10/…`; `institutions.newscientist.com/article/2219321-bees-are-better-at-counting-…` and `www.newscientist.com/article/2219321-…`; `prime.nautil.us/issue/22/slow/before-there-were-stars-rp` and `nautil.us/issue/22/slow/…`.

### Evidence for the tracking names applied on every host

Asked in review of eight names: does any carry an article's identity somewhere? In the stored leads each appears on one publisher's article pages only, never on a path too short to name an article, and where one article was shared with two values of a name the path was the same article:

| Name | Leads | Hosts | Articles seen with two values |
| --- | --- | --- | --- |
| `_r` | 3,771 | nytimes.com and its blogs | 141 |
| `hpid` | 336 | washingtonpost.com | 9 |
| `eventname` | 117 | nytimes.com and its blogs | 0 |
| `cndid` | 29 | wired.com, newyorker.com | 0 |
| `spreportid`, `spjobid`, `spuserid`, `spmailingid` | 12 each | newyorker.com | 0 |

This says they are not identity where they were seen. It cannot say so for a site that was never shared.

### 2. Stored leads follow the key, without paying again

`link_lead.url_key_version` records the form a lead was keyed under (migration `0027`: one column with a default, so the 612,148 rows are not rewritten). `thenwhat backfill rekey-links` works through the leads behind, five hundred to a transaction, in order of id, and can be stopped and run again:

- key unchanged: the version is set.
- key changed, no other lead has it: the key, outlet and outlet kind are set.
- key changed, another lead has it: the two are merged. **The lead kept is the one that has come furthest**: one that drafted a claim, else one that joined a claim, else read, scored, screened, else the older. Preparing a claim looks for the lead that drafted it (`prepare.py`, `decide_prepared_lead_claim`), and the funnel counts claims through it, so that pointer is never the one dropped while the other lead has none. Its shares gain the other's; a share both hold is kept once. The records screening found for the other lead move to it, each once: the kept lead's screening is usually still current and would not find them again. A label moves unless the same reader labelled both. A kept lead with a claim and no source article takes the other's when both point at one claim. The other lead's ledger entries are removed with it. The first share time becomes the earlier of the two. The kept lead keeps its own title and address.
- when both leads had made or joined different claims, the pair of claims is reported for the operator to compare. No claim, source article or match is changed.

**What is due again afterwards**: a step that asks nothing (screening) is due again when what it reads changed, because a new key can now match a tracked article and a new outlet can be on a list. A step that asks a source or a model keeps its entry, with its fingerprint rewritten for the lead as it now is: the article is the same article, and a lead whose host was `lite.cnn.com` is not a new headline. Without this, 21,946 leads would be due for triage and for reading again.

Loading and the link steps are refused while any lead is behind (`refuse_stale_keys`), because a lead keyed under the old form is not found under the new one and its article would be stored a second time.

### 3. Bringing the working database up to date (not run)

**The migration applies itself.** `pipeline/Dockerfile` starts the pipeline container with `alembic upgrade head`, and so does `compose.yaml`, so migration `0027` runs on the next `docker compose up` of an image built from this change, whatever else is planned. It is additive: one column with a default, no row rewritten, no key changed, nothing merged. What it does change at once is behaviour: from that start on, `load-links` and every step over link leads refuse to run until the rekey is done. So the image must not be rebuilt while a load or a run is wanted.

In this order:

1. Stop every loader and every run over link leads (`load-links`, `backfill run link_screen`, `link_triage`, `link_read`), and wait for them to end.
2. Back up the database (`~/automation/backup-services.sh` or `pg_dump`).
3. Rebuild and start the pipeline container, which runs `alembic upgrade head` and adds the column.
4. `thenwhat backfill rekey-links` to see the counts. Expected from the measurement: 612,148 behind, about 590,200 keep their key, about 16,190 get a new key, about 5,756 are merged. More leads will have been loaded by then.
5. `thenwhat backfill rekey-links --apply`. It refuses while the ledger shows a step working on a link lead in the last ten minutes. A load leaves no trace in the ledger, which is why step 1 comes first. It names the pairs of claims to compare.
6. `thenwhat backfill run link_screen` (no spend) for the leads whose key changed.
7. `thenwhat backfill plan link_triage` and `plan link_read` should show nothing newly due beyond leads that a listed outlet gained (a `lite.cnn.com` lead that was on no list and is now on cnn.com's).

To go back: restore the backup. `alembic downgrade 0026` drops the column but does not bring merged leads back.

When two merged leads had each drafted a claim, the claim of the lead that is removed has no lead pointing at it afterwards, and `prepare --pending` will not approve it by rule. That is the pair the command names: the operator compares the two claims and archives one.

Not covered by the command and left as tasks: the 5 claims that hold one article twice, and the 121 article leads too many.

### 4. Unfurling

Two kinds, kept apart because only one sends a request.

**By reading the address alone (no request).** An address that names where it leads is replaced by that address before the key is made: `web.archive.org/web/<time>/<address>`, `archive.ph` and its other names when followed by an address, `google.com/url?q=` and `?url=`. The lead stores the address as shared and the key of where it leads, so an archive copy and its original are one lead. 71 leads today. Not built: whether an archive copy should be one lead with the article it copies is the operator's (decision 4 below), because the page reader would then be asked for whichever address was shared first.

**By asking the shortener for its redirect (a request).** Only for hosts on a fixed list, and only the redirect: the `Location` header of the answer, never the page it leads to.

- **Who asks**: the pipeline, through a client of its own kind with registries and literature indexes (CLAUDE.md: asked directly, within their limits, with a contact User-Agent). A shortener is not a news site, so ADR 0006 is not touched: the request stops at the first address whose host is not on the list, and that address is never fetched by this client. Whether its page is read stays the page reader's decision.
- **Terms**: robots.txt of each host is read at the start of a run and obeyed; a host that disallows the path is skipped for that run. One request a second per host. Four redirects at most. No cookies, no referrer. The answer (status and `Location`) and the time are stored as the raw payload; nothing of any page is.
- **The list**: `bit.ly`, `trib.al`, `tinyurl.com`, `buff.ly`, `redd.it`, `nej.md` (robots read on 2026-11-12 and 2026-11-16 for the site's redirect reader, `site/worker/short.mjs`), and `on.wsj.com` and `on.ft.com` once their robots.txt has been read. **Never**: `t.co` (its robots.txt disallows every client but named search engines; only a reader's own browser opens it, in the extension), `lnkd.in`, `news.google.com` and `apple.news` (they answer with a page, not a redirect, and their terms have not been read).
- **Where it sits**: a ledger step over link leads on a listed host, before screening. It writes the address it leads to and the key of that address, merging with a lead that already has the key as `rekey-links` does. A second run asks nothing for a lead already unfurled.

Not built. 125 leads would be asked for today.

### 5. One article once per claim (not built)

`source_article` and `article_lead` get the key as a stored column, unique with the claim or the trial. `find_article` and `add_article` (`claims/entry.py`) compare by key. The address stored and published stays the address as shared, less tracking. Not built here: `find_article` is called by the read and extraction code that other work is changing, and a refusal it does not expect would fail a read after its spend.

## Risks

- **A host pair that is not one site.** Each pair was seen with one article at one path, but an edition can carry its own articles at other paths. Then two leads stay two leads (their paths differ), so the cost of a wrong pair is nil unless paths collide.
- **A merge drops the wrong lead.** The kept lead is the one that was paid for, and no claim is changed. The step is taken after a backup.
- **Another change adds migration `0027` at the same time.** Renumber on merge; the migration is one `ADD COLUMN`.
- **Fingerprints rewritten wrongly would hide real changes.** Only an entry that was current before the rekey is carried; a stale one stays stale.
