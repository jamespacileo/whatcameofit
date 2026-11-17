# Tasks

Write steps run on the one writer only. Every sample judged by an assistant is recorded as an assistant's, and the operator spot-checks a share.

## 1. Decisions and records before any build

The operator's answers of 2026-11-17 are in `design.md`, "What the operator decided".

- [ ] 1.1 Write the ADR that a sponsor's, an investor page's or a university's own release may be a source article, marked as on that organisation's website where a rule can say so; verify it names the outlet rule of screening it changes for route-found leads
- [ ] 1.2 Write the dated entry for the second headline corpus in `docs/sources.md`: its licence, the five fields asked for by name, that its files hold article text which is never read, and the operator's decision; verify it is written before its loader
- [ ] 1.3 Read the subscription's current terms on automated use and the search tool's documentation and write the dated entry in `docs/sources.md` with the pages read and the operator's decision of 2026-11-17 to use it at modest volume; verify the entry exists before section 4 starts
- [ ] 1.4 Ask the operator for the search route's daily allowance and for the monthly ceiling for model spend within the free credit; record both here; verify no setting is changed before the answer
- [ ] 1.5 Ask the operator whether the filings index is wanted; record the answer in `design.md`
- [ ] 1.6 Apply sections 2 to 4 only after `trial-first-route` has built the fingerprint and fit acronyms (its task 8.3); verify that task is done on `main`
- [ ] 1.7 Add headline file, kept headline, story group and agent search to `GLOSSARY.md`; verify the terms match the specs word for word
- [ ] 1.8 Note in this change's records which tasks wait for `registry-drafted-claims`: what makes a trial due for the search route, and the share of reads that join a claim that exists; verify `design.md` names that change

## 2. Phase 1: the carry and the headline route

- [ ] 2.1 Let a link lead hold a list of reasons (shared, kept from a headline file on a term, returned by the news search for a trial, reported by a search for a trial) in a new migration; verify a test of a lead with two reasons and that existing leads read as shared
- [ ] 2.2 Carry each article lead's address into a link lead with its reason (`specs/article-leads`); verify tests for one address found for two trials, an address already a lead, an address already a source article, a second run that adds nothing, and one success and one refusal of the command
- [ ] 2.3 Write the dated entry for the article list in `docs/sources.md`: terms, the fields read, a file a minute named by its time, no listing, the redirect to the secure address, what was observed on 2026-11-17; verify it is written before the script
- [ ] 2.4 Write the script that fetches a span of files and reduces each row to the five fields as it arrives; verify a test on a synthetic file that the staged file holds no description, author or other field, and that a missing minute is not an error
- [ ] 2.5 Add `thenwhat backfill load-headlines`: read staged files, send no request, record source and span, add nothing on a second load, count rows in another language; verify tests for each and one success and one refusal of the command
- [ ] 2.6 Build candidate terms by rule with the word list and inflected forms, count how many headlines each term would keep, and choose the share ceiling with the operator from that report; verify tests for an invented name, an ordinary word, a plural, a code without its hyphen and an empty ceiling that keeps nothing; record here the ceiling and the twenty most common terms it excludes
- [ ] 2.7 Load one week and record here the figures of `design.md`'s first table for each day; stop to tell the operator if the kept share differs from the measured day by more than a factor of two
- [ ] 2.8 Let a lead a trial route found go on to scoring though its outlet is on no list (`specs/lead-screening`), then screen the week's kept leads and record here how many are on each outlet kind and the twenty hosts that hold the most; verify tests for a route-found lead, a lead that was only shared, and a paper index; show the operator before anything is scored
- [ ] 2.9 Print the plan for the headline route by source and span (`specs/trial-coverage`); verify tests of a span not loaded, a route that is off, and a source with no dated entry
- [ ] 2.10 Score one day's kept leads with triage, then judge forty it passed and twenty-five it rejected; record the table here, and stop to tell the operator if fewer than half of the passed are treatment reports
- [ ] 2.11 Read one batch of about 200 through the loop of `docs/backfill-loop.md`: read, `thenwhat prepare --pending`, audit, clear; record here the reads, failures on the page, claims drafted and joined, trials newly cited, cost and hours
- [ ] 2.12 Record on the fault sheet that stored search names include ordinary words, add a regression test with a synthetic registry record at the seam that works out a search name, and stop the news search sending such a name; verify the count of trials whose name changed is recorded here
- [ ] 2.13 Mark by rule a source article on the website an approved organisation record gives for the sponsor of one of the claim's approved trials (`specs/site-publishing`); verify tests for a subdomain of that website, a company page with no organisation record, and that an agent's hint sets no mark
- [ ] 2.14 Load the second headline corpus for the months the article list is not loaded for, asking for the five fields by name; verify a test that fails if any other column is read, and record here the leads kept by outlet kind

## 3. Phase 2: story groups

- [ ] 3.1 Add the settings that name the measure's model and its version, with no model name in code, and note in `docs/sources.md` where the model comes from and that it runs on the writer's machine; verify `.env.example` holds them
- [ ] 3.2 Group leads by the measure of their titles and their dates, storing each group with the version; verify tests for one event told by several outlets, one treatment with two events months apart, a lead alike to none, and a new version that groups again
- [ ] 3.3 Draw 200 pairs across the measure's range from phase 1's leads, judge each as the same story or not, and choose the threshold with the operator; record here the threshold, the sample's size and the share placed rightly; verify nothing is grouped while the threshold is empty
- [ ] 3.4 Read within a group in the set order of outlet kinds and stop once the claim holds enough articles; verify tests that an unread lead is not rejected and keeps its score, that the next lead is read when the first reads made no claim, and that raising the setting makes unread leads due
- [ ] 3.5 Add `thenwhat backfill story-groups` and its report; verify one test of its figures and one of its message when grouping is off
- [ ] 3.6 Verify with a test that grouping changes no triage score, claim, match, event or export

## 4. Phase 3: the search route

- [ ] 4.1 Build the service with its two actions and its holds; verify tests for two agents asking at once, a hold that runs out, a report under a dead hold, nothing due, and what an agent is handed for a trial a pending claim names
- [ ] 4.2 Refuse by rule and store the rest; verify tests for an address that is not a web address, a registry page, a headline over the length, an unnamed field, and a field carrying words of an article
- [ ] 4.3 Store reported addresses as link leads with their reason and the model's name from the settings, and write the ledger entry; verify tests for nothing found, an address a headline file already gave, an address already a source article, and that a hint sets no outlet kind
- [ ] 4.4 Count trials handed out against the route's daily allowance and refuse to hand out with no dated entry in `docs/sources.md`; verify a test of each
- [ ] 4.5 Verify with a test that the service answers on the loopback address only, and that it offers no action but the two
- [ ] 4.6 Write the runner that starts agents with the index-only search tool in a sandbox that cannot write, then measure one trial a task against five a session on 100 trials each: leads, a judged sample of forty, tokens and time; record the table here and keep the cheaper only if its judged share is not lower
- [ ] 4.7 Add the route to the order and the plan (`specs/trial-coverage`); verify tests that a trial an earlier route sufficed for is not handed out, and that the route is listed as off until turned on
- [ ] 4.8 Run the route for 500 industry-sponsored phase 2 and 3 trials, judge forty leads, and record here the trials with a lead, the leads by outlet kind, the judgement and the hours; stop to tell the operator if fewer than half name the right treatment for the right condition
- [ ] 4.9 Verify with a test that a run creates link leads and ledger entries only, that a rejected lead is not read, and that a claim drafted from one is held awaiting audit

## 5. Records

- [ ] 5.1 Add the routes, their commands and their order to `docs/backfill-loop.md`, and say in `docs/daily-run.md` that the daily run starts none of them; verify `make scripts-test` fails if it would
- [ ] 5.2 Add every new setting to `.env.example` with its meaning and that the share ceiling and the group threshold have no default
- [ ] 5.3 Run `make check` and `openspec validate headline-funnel --strict`; verify both pass
