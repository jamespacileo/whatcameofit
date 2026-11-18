# site-publishing Specification

## Purpose
Publishes reviewed claims as a static public site on which every status is shown with the sourced evidence that produced it.

## Requirements

### Requirement: Publication gate
The export that feeds the site SHALL contain only claims that are approved, by any decider, and not archived, and for each of them only approved evidence events. Pending, rejected and archived items SHALL NOT appear in the export in any form, except that pending candidate matches of a published claim SHALL appear with their scores, marked as candidates.

#### Scenario: Claim with mixed events
- **WHEN** an approved claim has three approved events and two pending events
- **THEN** the export contains the claim with three events

#### Scenario: Draft claim
- **WHEN** a claim is still a pending draft, or a draft rejected by rule
- **THEN** the export does not contain it

#### Scenario: Archived claim
- **WHEN** an approved claim is archived
- **THEN** the export does not contain it and lists its slug as archived

### Requirement: Build from the export alone
The site SHALL be built from the export only, with no access to the database or to external services.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that has the export and no network or database
- **THEN** the build succeeds

### Requirement: Claim page
Each published claim SHALL have a page at `/{slug}` that shows its headline, summary, status with any no-signal overlay, date first reported, promises next to what actually happened, and its evidence events. Each event SHALL show its date, summary and a link to its source.

#### Scenario: Reader opens a claim
- **WHEN** a reader opens the page of a claim with four approved events
- **THEN** the page shows the status and four dated events, each linking to its source

#### Scenario: Unknown slug
- **WHEN** a reader opens a slug that no published claim has
- **THEN** a not-found page is shown

### Requirement: Status explanation on the page
A claim page SHALL identify the evidence events that produced the current status, and SHALL mark only those events.

#### Scenario: Status produced by one trial
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the page marks that trial's registered and started events as the reason for the status, and does not mark its completed or results-posted events

#### Scenario: Trial registered with three trials
- **WHEN** a claim's status is Trial registered and three standing trials have thirteen events between them
- **THEN** the page marks the three registered events and no other

### Requirement: Source articles are linked, not reproduced
A claim page SHALL list its source articles by outlet, title and date with a link to each. The site SHALL NOT display article text.

#### Scenario: Claim with two articles
- **WHEN** a claim has two source articles
- **THEN** the page lists both with links and shows no text from either

### Requirement: Topic index
Each vertical SHALL have an index page at `/topic/{vertical}` that lists its published claims with their statuses.

#### Scenario: Vertical with claims
- **WHEN** a reader opens the index of a vertical that has 30 published claims
- **THEN** 30 claims are listed with their statuses

### Requirement: Home page
The home page SHALL offer a search over published claims and SHALL list the claims whose status changed most recently.

#### Scenario: Search by intervention name
- **WHEN** a reader searches for a synonym of an intervention
- **THEN** the claim for that intervention is among the results

#### Scenario: Search with no result
- **WHEN** a reader searches for a term that matches no claim
- **THEN** the reader is told nothing was found

### Requirement: Approved claims page
The page at `/it-happened` SHALL list every published claim whose status is approved.

#### Scenario: No approved claims
- **WHEN** no published claim has the status approved
- **THEN** the page says that no tracked claim has reached approval yet

### Requirement: Status card image
Each published claim SHALL have a status card image that shows its headline, date first reported, latest promise as a date, and current status. The image SHALL be the claim page's link preview image and SHALL NOT show a count of days.

#### Scenario: Claim promised for 2025
- **WHEN** a claim's latest promise has the parsed date 31 December 2025
- **THEN** the card reads "promised by 2025" and shows no day count

#### Scenario: Claim with no promise
- **WHEN** a claim has no promises
- **THEN** the card omits the promise line

### Requirement: Footer notices
Every page SHALL carry a footer stating that the site gives no medical advice, that a registered trial is not a treatment option, which data sources are used, and when the data was last checked.

#### Scenario: Any page
- **WHEN** a reader opens any page of the site
- **THEN** the footer shows the two notices, the data sources and the last-checked date

### Requirement: Neutral wording
Status labels, status glosses, overlay text and the topic summary sentence SHALL describe evidence only. The site SHALL NOT describe a claim as dead, abandoned, a scam or any similar verdict. A gloss or summary clause that carries verdict wording SHALL fail the site build.

#### Scenario: Long-quiet claim
- **WHEN** a preclinical-only claim has had no evidence event for six years
- **THEN** the page reads "no signal for 6 years" and uses no verdict wording

#### Scenario: Gloss with verdict wording
- **WHEN** the site is built and a status gloss contains the word "abandoned"
- **THEN** the build fails and quotes the gloss

#### Scenario: Summary of a topic with ended trials
- **WHEN** a topic lists a claim whose status is Trials ended early
- **THEN** the summary sentence states that its trials were stopped early and uses no verdict wording

### Requirement: A page explains the method
The site SHALL have one page that explains, in plain words, how a claim's status is derived from approved evidence events by fixed rules, that no model and no editor decides a status, what each status means, what the no-signal note does and does not mean, what the site never says (verdicts, medical advice, that a registered trial is a treatment option), where the data comes from, and how to report an error. Every claim page SHALL link to it. The wording of each status's meaning SHALL be the same wording the claim pages use.

#### Scenario: Reader doubts a status
- **WHEN** a reader follows the method link from a claim page
- **THEN** they can read how that status is derived and what it does not mean

#### Scenario: Wording stays in step
- **WHEN** the wording of a status's meaning is changed
- **THEN** the method page and the claim pages show the new wording from the same source

### Requirement: A page for each year
For each year in which at least one published claim was first reported, the site SHALL have a page listing every published claim first reported in that year with its current status, and showing how those claims are spread across statuses. The page SHALL state counts only and SHALL NOT rank, grade or characterise the year, the claims or the outlets. A year with no published claim SHALL have no page and SHALL NOT be linked.

#### Scenario: Claims first reported in 2021
- **WHEN** three published claims were first reported in 2021
- **THEN** the page for 2021 lists the three with their current statuses and the number at each status

#### Scenario: A year with nothing
- **WHEN** no published claim was first reported in 2020
- **THEN** the site has no page for 2020 and no link to one

### Requirement: Pages can be found and cited
Every public page SHALL state its canonical address, built from the site's configured public address. Every claim page SHALL carry structured data that names the page, describes it, the date the claim was first reported, the date the registries were last checked, its card image and the site as publisher. The home page SHALL carry structured data naming the site and its publisher with a logo. Claim, topic, source and year pages SHALL carry a breadcrumb trail as structured data. The data page SHALL describe the open dataset, its licence and its download. The site SHALL NOT use fact-check, review or rating markup, because each states a verdict. The site SHALL publish a sitemap listing every public page except embed pages, and a `robots.txt` that names the sitemap. Every page SHALL announce the site's feeds. A preview build SHALL ask search engines not to index any page, SHALL publish no sitemap, and its `robots.txt` SHALL disallow every page.

#### Scenario: Claim page read by a search engine
- **WHEN** a search engine reads a claim page of a public build
- **THEN** it finds the canonical address, the first-reported and last-checked dates, a breadcrumb trail, and no rating or review markup

#### Scenario: Crawler arrives
- **WHEN** a crawler reads `robots.txt` of a public build
- **THEN** it is allowed every page and told where the sitemap is

#### Scenario: Preview build
- **WHEN** the site is built as a preview
- **THEN** every page asks not to be indexed, no sitemap is published, and `robots.txt` disallows every page

#### Scenario: Public address not configured
- **WHEN** a public build is made while the configured address is a local one
- **THEN** the build stops and says that the public address must be set

### Requirement: Approach on the claim page
A claim page SHALL show the label of the claim's approach when it has one, in the site's own wording, and SHALL show nothing in its place when it has none. The label SHALL describe the kind of intervention only, and SHALL NOT suggest that the intervention works or is available.

#### Scenario: Claim with an approach
- **WHEN** a reader opens a claim whose approach is gene therapy
- **THEN** the page shows the label for gene therapy

#### Scenario: Claim without an approach
- **WHEN** a reader opens a claim with no approach
- **THEN** the page shows no approach label and no placeholder

#### Scenario: Approach code without site wording
- **WHEN** the export carries an approach code that the site has no label for
- **THEN** the site build fails and names the code

### Requirement: Topics page lists every group with claims
The topics page SHALL list each group that has at least one published claim, with that group's verticals that have published claims under it. A group or vertical with no published claim SHALL NOT be listed.

#### Scenario: Group with one listed vertical
- **WHEN** the group "Kidneys and bladder" has one published claim, filed under its general vertical
- **THEN** the topics page lists "Kidneys and bladder" with that one vertical

#### Scenario: Empty group
- **WHEN** no published claim is filed under "Pregnancy and fertility"
- **THEN** the topics page does not list that group

### Requirement: A tracked article is answered with its status
When a reader pastes the address of an article the site tracks, the home page SHALL show, for each claim the article reports, the status in words, its place on the path when the status is on the path, the no-signal note when it applies, what the status means, the date first reported, and a link to the claim's records. The status SHALL NOT be conveyed by the path alone. Close matches to an untracked article SHALL keep the plain list, so a guess never looks like an answer.

#### Scenario: Tracked article
- **WHEN** a reader pastes the address of an article reporting a claim whose status is a Phase 2 trial
- **THEN** the answer shows "Phase 2 trial", the fourth of six places marked, what that status means, and a link to the records

#### Scenario: Untracked article with close claims
- **WHEN** a reader pastes an address the site does not track and two tracked claims share words with it
- **THEN** the claims are listed as a guess, without the status panel

### Requirement: Approvals are counted, not characterised
The approved-claims page SHALL state how many tracked claims have an approval on record out of all tracked claims. Each year page SHALL state the same for the claims first reported in that year. The statement SHALL be a count and SHALL NOT carry an adjective, a percentage or a comparison.

#### Scenario: One approval among three claims
- **WHEN** three claims are published and one has an approval on record
- **THEN** the approved-claims page says "Approvals on record: 1 of 3 tracked claims."

### Requirement: A pasted address stays out of the page's address
The home page SHALL NOT write a pasted article address into its own address, so that reloading or sharing the page sends no article address to the site's host. Typed search words MAY be kept in the page's address.

#### Scenario: Reader pastes an article address
- **WHEN** a reader pastes an article's address into the main box and the answer is shown
- **THEN** the page's address carries no part of the pasted address

#### Scenario: Reader types search words
- **WHEN** a reader searches for "tooth"
- **THEN** the page's address carries the words, so the search can be reloaded

### Requirement: The promise is beside the status on the claim page
A claim page for a claim with a dated promise SHALL show the year promised by in the status panel, on the site's pale amber, linked to that year in the timetable. A claim with no dated promise SHALL show no such line.

#### Scenario: Claim with a dated promise
- **WHEN** a claim's latest promise names 2025
- **THEN** the status panel shows "Promised by 2025" and the year leads to the 2025 row

### Requirement: Claim lists lead with the intervention name
Each row of a claim list SHALL lead with the claim's intervention name as the link to the claim page. The claim's full headline SHALL remain in the same row, with less visual weight than the name.

#### Scenario: Row for a named intervention
- **WHEN** a topic index lists a claim whose intervention is "Trontinemab"
- **THEN** the row's link reads "Trontinemab" and the row also shows the claim's full headline

#### Scenario: Two claims for one intervention
- **WHEN** a list holds two claims that share an intervention name
- **THEN** both rows show the same name and each shows its own headline

### Requirement: Every status carries a plain-language gloss
The site SHALL hold one fixed gloss for every status code: a short phrase that states what the status means without trial-phase vocabulary. Wherever a claim list or a claim page shows a status label, it SHALL show that status's gloss with it. The precise meaning of each status SHALL remain on the claim page and the method page.

#### Scenario: Gloss in a list
- **WHEN** a topic index lists a claim whose status is Phase 3 trial
- **THEN** the row shows the label "Phase 3 trial" and its gloss

#### Scenario: Gloss on the claim page
- **WHEN** a reader opens a claim whose status is Preclinical only
- **THEN** the page shows the label, its gloss and the precise meaning

#### Scenario: Status code without a gloss
- **WHEN** the site is built and a status code has no gloss
- **THEN** the build fails and names the code

### Requirement: Topic index opens with a summary of where its claims stand
A topic index SHALL open with one sentence that gives the number of claims listed and, for each status its claims hold, the number of claims with that status in plain language. The sentence SHALL be built by fixed rules from the counts alone. Statuses SHALL be named in path order, then the statuses off the path.

#### Scenario: Topic with two statuses
- **WHEN** a topic lists 7 claims, 5 Preclinical only and 2 Phase 3 trial
- **THEN** the page opens with a sentence that gives 7, then 5 with the preclinical wording, then 2 with the Phase 3 wording

#### Scenario: Topic with one claim
- **WHEN** a topic lists one claim
- **THEN** the sentence is in the singular and states that claim's status in plain language

#### Scenario: Topic with more than four statuses
- **WHEN** a topic's claims hold six different statuses
- **THEN** the sentence names the four statuses with the most claims and gives the count of the remaining claims without naming their statuses

#### Scenario: Vertical with no published claims
- **WHEN** a topic lists no claims
- **THEN** no summary sentence is shown

### Requirement: Current brand assets
The site SHALL generate browser and home-screen icons from the selected canonical
artwork, including a conventional multi-size ICO. Changing that artwork SHALL change
the URLs advertised for browser, launcher and share images. Maskable icons SHALL keep
the symbol within the central safe area.

#### Scenario: Returning reader after a rebrand
- **WHEN** new artwork is deployed
- **THEN** the page advertises a new revision of each brand asset

### Requirement: Resilient source icons
Source attribution SHALL use locally stored publisher icons, with a same-size letter
tile when no icon is stored or an image fails to load. Outlet names and domains SHALL
remain distinguishable and wrap within narrow viewports.
Transparent publisher marks SHALL remain legible against light and dark reading
surfaces. Corrected image bytes SHALL produce a new local asset URL. A generic
hosting-platform logo SHALL use the letter fallback until a publisher icon is available.

#### Scenario: An icon request fails
- **WHEN** a stored publisher image cannot load
- **THEN** its letter tile remains and the source name and article link remain usable

#### Scenario: Dark reading surface
- **WHEN** a publisher supplies a transparent dark mark
- **THEN** a light backing preserves the mark's contrast without changing its colours

#### Scenario: Publisher artwork corrected
- **WHEN** the stored image changes
- **THEN** the rendered source uses a different asset URL so a cached image cannot hide the correction

### Requirement: The latest lookup owns the answer
The home page SHALL ignore the success or failure of an article lookup after the reader submits a newer search, including an empty search. An ordinary current lookup SHALL still display its result.

#### Scenario: Old lookup finishes after a new submission
- **WHEN** an earlier article lookup resolves or fails after the reader submits a shortened link or clears the search
- **THEN** the newer answer or cleared result remains visible

### Requirement: Live candidates show their confidence
Each live trial candidate SHALL show its own match confidence or explicitly say it is unavailable. Its supporting explanation and the confidence limitation SHALL be available in a collapsed disclosure. The label SHALL not imply treatment effectiveness or trial quality. Titles and disclosures SHALL fit a 320-pixel viewport.

#### Scenario: Mixed confidence availability
- **WHEN** one candidate has a valid confidence and another does not
- **THEN** their separate disclosures show the valid score and unavailable label respectively, without copying a score between records

### Requirement: Reminders do not contradict results
The check-again reminder SHALL invite another check without asserting that no record exists.

#### Scenario: Live candidates found
- **WHEN** live lookup finds trial candidates for an untracked article
- **THEN** the reminder does not claim that nothing is on record

### Requirement: Every page has a complete link preview
Every page SHALL state, for link previews, its title, description, canonical address, the site's name, the locale `en_GB`, an image with its width, height, type and text alternative, and a large-image card for X with the same alternative. Claim pages SHALL be typed as articles with the date first reported as published time and the date last checked as modified time; every other page SHALL be typed as a website. Every page SHALL state the site's theme colour.

#### Scenario: Claim link pasted into a chat
- **WHEN** a claim page's address is pasted into a messenger that reads link previews
- **THEN** it finds the wide card with its size and alternative, the page's own address and the article's dates

#### Scenario: Home page shared
- **WHEN** the home page's address is shared
- **THEN** its preview is typed as a website and shows the site's card

### Requirement: Long lists are read a page at a time
Each of the home page's four tabbed lists SHALL show ten rows at a time; its day-by-day list is opened as its own requirement says. Every other list of claims SHALL show 25 rows at a time. A list longer than one page SHALL have, directly under it, a control to step to the next and the previous page and a line saying which rows are shown and how many there are. A list that fits one page SHALL show no such control. Where a list can be narrowed by status, the narrowing SHALL apply to the whole list and SHALL return the reader to its first page.

Every row of every other list of claims SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. The home page's tabbed lists hold their first ten rows as built. With scripting off, and in print while the rest are not in the page, each SHALL show those rows and SHALL say how many of its rows are shown and that every claim is also listed under its topic, with a link to the topics. The page in view SHALL be recorded in the page's address, and an address naming a page that does not exist SHALL show the nearest page that does.

#### Scenario: More rows than one page
- **WHEN** published claims have 104 source articles between them
- **THEN** the home page's Headlines list shows the ten newest, says "1–10 of 104 headlines", and the next step shows the eleventh to the twentieth

#### Scenario: A list that fits one page
- **WHEN** a topic has four published claims
- **THEN** all four are shown and no paging control is shown

#### Scenario: A page that does not exist
- **WHEN** the address names page 99 of a list with eleven pages
- **THEN** the eleventh page is shown

#### Scenario: Narrowing by status
- **WHEN** a reader on the second page of a year's claims picks a status
- **THEN** the claims at that status across the whole year are listed from their first page

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off and its Headlines list has 104 rows
- **THEN** the ten newest headlines are listed, and the list says that the first 10 of 104 headlines are shown and links to the topics, where every claim is listed

#### Scenario: Scripting off on a topic page
- **WHEN** a topic page with 60 claims is opened with scripting off
- **THEN** all 60 claims are listed

#### Scenario: A filter changes while Next is pending

- **WHEN** the reader presses Next and selects Phase 3 before the outstanding rows arrive
- **THEN** the filtered list opens on rows 1–10 of 702 and its stored page number matches the visible page

### Requirement: The home page offers the claims in five lists
Under the day-by-day list, under a heading of their own, the home page SHALL offer these lists of published claims, in this order, and SHALL show one at a time, the first unless the address names another:

1. Headlines: every source article, newest first.
2. Claims: every published claim once, by the date it was first reported, newest first.
3. Status changes: every change from one status to another, newest first, each with the day, the status from that day and the status before it. A claim's first status is not a change.
4. Promises: every claim with a dated promise, in order of its latest promised date, earliest first, with the promise beside the status now.
5. No signal: every claim carrying the no-signal overlay, the most years first.

A list with no rows SHALL NOT be offered, except Headlines. Each list SHALL show how many rows it has. Every order SHALL be a date or a count from the record: the page SHALL NOT rank or grade claims, and SHALL NOT word a promise as kept, missed or late. The list in view SHALL be recorded in the page's address. With scripting off, every list SHALL be shown, one under the other.

#### Scenario: Lists on the home page
- **WHEN** one published claim has changed status twice, and another has a dated promise and the no-signal overlay
- **THEN** the home page offers Headlines, Claims with two rows, Status changes with two rows, Promises with one row and No signal with one row

#### Scenario: Every claim once
- **WHEN** a published claim has three source articles
- **THEN** it has three rows under Headlines and one row under Claims

#### Scenario: Claims in order of first report
- **WHEN** one claim was first reported on 12 November 2026 and another on 30 October 2026
- **THEN** the first is listed above the second under Claims, whatever their statuses or how much either has been tested

#### Scenario: A first status is not a change
- **WHEN** a claim's history holds only its first status
- **THEN** the claim has no row under Status changes

#### Scenario: A promise whose date has passed
- **WHEN** a claim's promised date is earlier than today
- **THEN** it is listed first under Promises with its status now, and the page adds no wording about the date having passed

#### Scenario: Nothing has gone quiet
- **WHEN** no published claim carries the no-signal overlay
- **THEN** the No signal list is not offered

#### Scenario: A list named in the address
- **WHEN** the home page is opened at an address naming the Claims list
- **THEN** that list is the one shown

#### Scenario: Where the five lists stand
- **WHEN** a reader opens the home page
- **THEN** the day-by-day list comes first under the lookup, and the five lists follow it under their own heading

### Requirement: The home page's lists can be narrowed by status and by topic
Above the day-by-day list, the home page SHALL offer one field that names each status with how many published claims are at it, in the order of the path a topic page shows, and SHALL let a reader pick one status; a status with no claim SHALL NOT be pickable. Where more than one topic is listed, it SHALL also let a reader choose one topic: from a list beside the day-by-day list on a wide screen, and from a field on a narrower one. A pick SHALL narrow the day-by-day list and all tabbed lists at once to rows whose claim has that status now and is filed under that topic; both picks together SHALL narrow to rows that meet both. Each tabbed list's count SHALL be the rows left, and a list left with none SHALL say so in place of an empty table. In the day-by-day list a heading SHALL count the rows left under it, a heading left with none SHALL NOT be shown, and a list left with none SHALL say so. With a topic chosen, the counts in the status field SHALL be that topic's. The picks SHALL be recorded in the page's address. The counts SHALL be stated as numbers only: the page SHALL NOT rank topics or characterise the spread.

#### Scenario: Counts on the path
- **WHEN** three published claims stand at preclinical only, phase 2 and approved
- **THEN** the status field shows one at each of those and none at the others, and a status with none cannot be picked

#### Scenario: Picking a status
- **WHEN** a reader picks phase 3
- **THEN** each list shows only rows of claims now in phase 3, and each list's count is the number of those rows

#### Scenario: Narrowing to a topic
- **WHEN** a reader chooses a topic with seven claims
- **THEN** every list shows only that topic's rows and the status field shows where those seven stand

#### Scenario: A list left empty
- **WHEN** no claim in the chosen topic carries the no-signal overlay
- **THEN** the No signal list shows a count of none and says nothing is in the list for that choice

#### Scenario: One topic
- **WHEN** only one topic is listed
- **THEN** no topic choice is shown

#### Scenario: Narrowing the day-by-day list
- **WHEN** a reader picks phase 3 and one day's heading holds two reports of claims now in phase 3 and one of a claim at preclinical only
- **THEN** that heading says "2 reports" and lists those two rows, and a heading whose claims are all at other statuses is not shown

#### Scenario: A status and a kind together
- **WHEN** a reader picks approved and chooses registry records
- **THEN** the day-by-day list shows only registry rows of claims now approved

### Requirement: Trials on the claim page
A claim page SHALL list each of the claim's trials once, under its own heading, with its registry identifier linked to the record, its state, the facts the export carries for it, and the score of its match. An entry SHALL show the trial's phase when the registry gives one, and SHALL say inside its fold when the registry gives none. Trials SHALL be ordered furthest phase first and, within a phase, those with posted results first. Each trial event in the timetable SHALL lead to its trial. A claim with no trial SHALL show no such section.

#### Scenario: Claim with one completed Phase 2 trial
- **WHEN** a reader opens a claim whose one trial enrolled 83 participants, was randomised and has posted results
- **THEN** the page shows that trial once with its identifier, "Phase 2", that it has finished, 83 people, that people were assigned at random, and its posted primary outcome

#### Scenario: Trial with no phase
- **WHEN** a trial's registry record gives no phase
- **THEN** the entry's visible lines name no phase, and its fold says the registry gives none

#### Scenario: Reader follows a timetable entry
- **WHEN** a reader presses a trial's "results posted" entry in the timetable
- **THEN** they can reach that trial's entry and its posted results

#### Scenario: Claim with no trial
- **WHEN** a claim has no trial
- **THEN** the page shows no trials section and no placeholder for one

### Requirement: A long list of trials opens with the furthest
The claim page SHALL show first, under a "Results posted" heading, every trial that has posted results, whatever its phase, each row naming its own phase. It SHALL group the other trials by each trial's furthest phase, furthest first, under a heading that names the phase and counts its trials. A trial whose phases are Phase 1 and Phase 2 SHALL sit with Phase 2, and the heading of a group with more than one phase wording SHALL read "<phase>, including <other wording>". Trials with no phase SHALL be in a last group named "No phase given". Each group SHALL show its first ten trials and SHALL keep the rest of that group reachable on the same page without loading anything. A group's heading SHALL stay in view while its trials are read.

#### Scenario: Claim with fifteen trials across three phases
- **WHEN** a reader opens a claim with four Phase 3 trials, ten trials of Phase 2 or Phase 1/Phase 2, and one with no phase, none with posted results
- **THEN** the page shows three headings in that order, "Phase 3", "Phase 2, including Phase 1/Phase 2" and "No phase given", with all fifteen trials shown

#### Scenario: Trials with posted results lead
- **WHEN** a claim has a Phase 2 trial that posted results and a Phase 3 trial that did not
- **THEN** the Phase 2 trial is shown first, under "Results posted", and names its phase

#### Scenario: Claim with twelve Phase 2 trials
- **WHEN** a reader opens a claim with twelve Phase 2 trials and none with posted results
- **THEN** ten are shown under the Phase 2 heading and the other two open on request

### Requirement: The claim page counts its trials
A claim page for a claim with at least one trial SHALL state, in "The record in brief", how many trials are on record and the largest number of participants any of them states, with whether that number is actual or planned when the answer is opened. The statement SHALL be a count and SHALL NOT add participants across trials. The facts under the digest SHALL NOT repeat it.

#### Scenario: Three trials, the largest of 1,200
- **WHEN** a claim has three trials and the largest states 1,200 actual participants
- **THEN** the section states three trials on record and 1,200 people in the largest, and the facts under the digest do not

#### Scenario: Trials that state no number
- **WHEN** none of a claim's trials states a number of participants
- **THEN** the section states the number of trials and no size

### Requirement: Trial facts are worded without a verdict
The site SHALL word each trial fact code itself and SHALL fail the build on a code it has no wording for. It SHALL show a posted result as the registry's numbers and SHALL NOT label an outcome as met, missed, significant, successful or failed, nor a trial as having worked. The trials section SHALL say that the numbers are as posted by the trial's sponsor to the registry.

#### Scenario: Posted comparison with a p value
- **WHEN** a trial's posted primary outcome carries a comparison with the p value 0.03
- **THEN** the page shows the group values and "p = 0.03" with the method, and no word on whether the outcome was met

#### Scenario: Fact code without site wording
- **WHEN** the export carries a masking code the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Wording with a verdict
- **WHEN** the site is built and the wording for a trial fact contains "successful"
- **THEN** the build fails and quotes the wording

### Requirement: Trial facts show when their record was read
Each trial's entry SHALL show the date its registry record was read, and the trials section SHALL say that the facts are a selection from the record and link to the record for the whole of it.

#### Scenario: Record read on 3 October 2026
- **WHEN** a trial's facts were read from a record fetched on 3 October 2026
- **THEN** the trial's entry shows that date

### Requirement: A trial is not presented as open to join
The trials section SHALL NOT show where a trial takes place, whom to contact, who may take part, or that a trial is recruiting. A trial under way SHALL be worded as under way.

#### Scenario: Trial the registry shows as recruiting
- **WHEN** a claim's trial is recruiting in the registry
- **THEN** its entry reads that the trial is under way and shows no location, contact or eligibility

### Requirement: Papers are listed apart from trial records
A claim page SHALL list matched papers under a heading of their own and SHALL NOT describe a paper as a trial registry record or count it among registry records.

#### Scenario: Claim with one matched paper and no trial
- **WHEN** a reader opens a claim whose only approved match is a paper
- **THEN** the paper is listed under the papers heading and the page says no trial record matched

### Requirement: Confidence is shown with an event scored below certain
An evidence event whose confidence is below 1 SHALL show that confidence on the claim page in the words and bands the site uses for matches. An event with a confidence of 1 SHALL show none.

#### Scenario: Follow-up paper scored 0.6
- **WHEN** a claim page shows a follow-up paper event with a confidence of 0.6
- **THEN** the event shows "Medium match · 60%"

#### Scenario: Trial event read from a registry record
- **WHEN** a claim page shows a trial registered event with a confidence of 1
- **THEN** the event shows no confidence

### Requirement: The home page says what is dated since a reader's last visit
Above its four tabbed lists, the home page SHALL show a reader with scripting on one line counting the news reports, status changes and promised dates that are dated from the day of their last visit to today, each count opening the list that holds its rows. Rows of news reports and status changes dated in that span SHALL carry the word "New". On a first visit, or where the browser keeps nothing, the line SHALL cover the last thirty days and no row SHALL be marked. When nothing is dated in the span the line SHALL say so. The day of a visit SHALL be kept in the reader's browser only and SHALL NOT be sent to the site. The line SHALL state counts only.

#### Scenario: A later visit
- **WHEN** a reader last opened the home page on 7 November and opens it on 14 November, and 12 reports and 1 status change are dated in between
- **THEN** the line reads "Since your last visit on 7 Nov 2026: 12 news reports, 1 status change." and those rows carry "New"

#### Scenario: A first visit
- **WHEN** a reader opens the home page with nothing kept in their browser
- **THEN** the line begins "In the last 30 days" and no row carries "New"

#### Scenario: A second look on the same day
- **WHEN** the reader reloads the home page later the same day
- **THEN** the line and the marked rows are the same as on the first look that day

#### Scenario: Storage holds something else
- **WHEN** the browser's kept value is not in the expected shape
- **THEN** the visit is treated as a first visit

### Requirement: Ways back sit beside the answer
A claim page's status panel SHALL link to the page's reminders where they can be offered. The home page SHALL link the feed of status changes in the open, and each topic page SHALL link a feed of that topic's status changes and offer to share the page. A claim page SHALL end with a link to look up another headline, and the home page SHALL end with the link to suggest a headline when a suggestion address is configured. Where a claim page says it has not been checked by a person is set by "Unchecked claims are marked".

#### Scenario: Following from a claim page
- **WHEN** a reader opens a claim page
- **THEN** the status panel holds a link to "Check again later", and the page's last section leads to the lookup

#### Scenario: A topic's status changes as a feed
- **WHEN** a topic has a claim whose status has changed twice
- **THEN** the topic page links a feed holding those changes, newest first

### Requirement: The home page's controls fit a phone
Below the site's one breakpoint, with scripting on, the status counts and the topic choice SHALL be reached from one control and SHALL start open when the address already narrows the lists. The controls for the kinds of row SHALL all be in view without scrolling sideways, and so SHALL the four lists' tabs where they stand. Every pressed thing SHALL be at least 44 pixels tall, except a link inside a sentence.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 pixels wide
- **THEN** the controls for the kinds of row are all in view, the counts are behind "Narrow these lists", and the four tabs sit in one row above their lists

#### Scenario: A narrowed address on a phone
- **WHEN** the home page is opened at an address that names a status
- **THEN** the counts are shown, with the named status picked

### Requirement: Counts in the since line stand beside their totals and narrow their lists
Each count in the home page's since line SHALL be given with the total of the list it belongs to. When any row is dated in the span and no status change is, the line SHALL say none of the status changes are. Pressing a count SHALL show its list narrowed to the rows dated in the span, and pressing it again, or "Show all", SHALL show the whole list. When a followed claim's status differs from the one kept, the line SHALL say how many have changed and link to the list.

#### Scenario: What is dated since the last visit
- **WHEN** 12 of 104 reports and 1 of 38 status changes are dated since the reader's last visit
- **THEN** the line reads "12 of 104 news reports, 1 of 38 status changes"

#### Scenario: No status change since the last visit
- **WHEN** 14 reports and no status change are dated since the reader's last visit
- **THEN** the line reads "14 of 104 news reports, none of 38 status changes"

#### Scenario: Pressing a count
- **WHEN** the reader presses "14 of 104 news reports"
- **THEN** the Headlines list shows those 14 rows and "Show all" brings back the rest

### Requirement: A headline starts on a phone's first screen
At 375 by 812 pixels, with scripting on and nothing followed, the first row of the home page's day-by-day list SHALL start within the first screen, and the controls for the kinds of row SHALL be in view. The order a keyboard moves in SHALL be the page's own.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** the first row of the day-by-day list starts above 812 pixels and the controls for the kinds of row sit above it

### Requirement: Topic pages end on a next step
A topic page SHALL end with a link to look up another headline and, when a suggestion address is configured, the link to suggest one. Rows of a claim list first reported since the reader's last visit to the home page SHALL carry the word "New". A pager step that leads nowhere SHALL be passed over by the Tab key.

#### Scenario: A topic's status changes as a feed
- **WHEN** a reader reaches the end of a topic page
- **THEN** it offers to look up another headline

### Requirement: The masthead's mark is drawn into the page and moves once a visit
Every page's masthead SHALL hold the reverse mark as a drawing in the page, with the same shapes as the generated reverse mark file. On the first page of a visit, for a reader who has not asked for reduced motion, the glass SHALL be lowered onto the capsule before the name's question mark is drawn and its dot lands, and the whole SHALL take no longer than two seconds. On later pages of the visit nothing in the masthead SHALL move on load. Hovering or focusing the name SHALL move only the capsule, which grows a little and settles. With reduced motion asked for, nothing in the masthead SHALL move. The mark SHALL be whole and in place from the first frame.

#### Scenario: The mark in the masthead
- **WHEN** any page is built
- **THEN** its masthead holds the mark as a drawing whose shapes are those of the reverse mark file

#### Scenario: A first page, then a second
- **WHEN** a reader opens one page and then another in the same visit
- **THEN** the glass, the question and the dot move on the first page and not on the second

### Requirement: A page or a search that finds nothing shows the path with no place marked
The not-found page, and a search with no result, SHALL show a drawing of the path's places with none of them marked and a glass at rest past the last. For a reader who has not asked for reduced motion the glass SHALL pass over the places once and come to rest; it SHALL NOT loop, and no place SHALL be marked at any moment. The drawing SHALL be hidden from screen readers, and the words beside it SHALL say what was not found.

#### Scenario: Unknown slug
- **WHEN** a reader opens an address with no page
- **THEN** the page says no page was found and shows the six places with none marked

#### Scenario: Search with no result
- **WHEN** a search finds nothing
- **THEN** the drawing is shown above the sentence that says so

### Requirement: The method page shows how a status is made as a drawing
Under its video the method page SHALL show a drawing in three parts: what was reported, what was recorded, and where that leaves the claim, with the status in words beside its place on the path. Its example SHALL be made up, and the page SHALL say so beside it. The drawing SHALL be complete without scripting, without motion and on paper. It SHALL move only when the reader presses its control, which SHALL be absent without scripting, with reduced motion asked for and on paper.

#### Scenario: The method page's drawing
- **WHEN** the method page is built
- **THEN** the drawing shows the status, its place on the path and the note that its records are made up, and its control starts hidden

### Requirement: Small drawings confirm a press
On a claim page, pressing "Follow" SHALL fill the bookmark, and for a reader who has not asked for reduced motion the bookmark SHALL land; it SHALL NOT move when a followed claim's page is opened. Saving a reminder SHALL be confirmed in the pill pressed, which SHALL read "Saved to your calendar" for about two seconds, SHALL tell a screen reader, and SHALL then offer its date again. A topic chip's drawing MAY be drawn again on hover or focus, by one technique for every topic. No drawing SHALL move on scroll.

#### Scenario: Following from a claim page
- **WHEN** a reader presses "Follow"
- **THEN** the pill reads "Following" with its bookmark filled

#### Scenario: A reminder is saved
- **WHEN** a reader presses "In a year"
- **THEN** the pill reads "Saved to your calendar", and two seconds later "In a year"

### Requirement: Every claim says whether a person checked it
Every exported claim SHALL state whether a person checked it. A claim SHALL count as checked only when a person approved it and no decision made by the assistant still stands on the claim, on one of its matches or on one of its events. A claim approved by rule, loaded from a seed file or decided by the assistant SHALL state that no person checked it, and SHALL be published like any other approved claim. The pipeline SHALL NOT write an export that calls itself a preview.

#### Scenario: Claim approved by the assistant
- **WHEN** a claim was approved by the assistant and the export is written
- **THEN** the export contains the claim, says no person checked it, and does not call itself a preview

#### Scenario: Operator's claim with an assistant's event
- **WHEN** an operator-approved claim has an event approved by the assistant
- **THEN** the export says no person checked the claim until the operator decides that event

#### Scenario: Operator takes over every decision
- **WHEN** the operator repeats, without the assistant flag, each decision the assistant made on a claim
- **THEN** the export says a person checked the claim

### Requirement: Unchecked claims are marked
A claim page, and the extension's view of a claim, SHALL say when no person has checked the claim, and SHALL say nothing of the kind for a claim a person checked. A claim page SHALL say it once, in a line under the title and above the status card, with the words leading to the guide entry on what "checked by a person" means; the same line SHALL give the day the registries were last checked. A site built from an older export that calls itself a preview SHALL show on every page that it is a preview and not for publication, and SHALL ask search engines not to index any page.

#### Scenario: Unchecked claim page
- **WHEN** a reader opens the page of a claim no person checked
- **THEN** the line under the title says the page was put together by software and is not yet checked by a person, and gives the day the registries were last checked

#### Scenario: Said once
- **WHEN** a reader reads the page of a claim no person checked from top to bottom
- **THEN** the page says it is not yet checked by a person in one place only

#### Scenario: Checked claim page
- **WHEN** a reader opens the page of a claim a person checked
- **THEN** the line under the title gives the day the registries were last checked and says nothing about who checked it

#### Scenario: Checked claim in the extension
- **WHEN** the extension shows a claim a person checked
- **THEN** it carries no unchecked note

#### Scenario: Older preview export
- **WHEN** the site is built from an export that calls itself a preview
- **THEN** every page carries the preview note and a noindex tag

### Requirement: A trial entry leads with plain words
A trial's entry SHALL lead with a heading that states how many people the trial enrolled or plans to enrol and, where its record names what it was compared with, that comparison. The heading SHALL state only what the record states. The registry's own title SHALL be shown inside the entry's fold. Every trial SHALL be drawn at the same size and weight.

#### Scenario: Trial with a named comparison
- **WHEN** a device trial enrolled 135 participants and its record names a sham comparator and no treatment
- **THEN** its heading reads "135 people, compared with a sham device and with no treatment"

#### Scenario: Trial whose record names no comparison
- **WHEN** a trial enrolled 34 participants and its record names no comparator
- **THEN** its heading reads "34 people" and says nothing about a comparison

#### Scenario: Planned size
- **WHEN** a trial not yet started plans to enrol 400 participants
- **THEN** its heading says 400 people are planned, not that 400 took part

#### Scenario: Trial that states no size
- **WHEN** a trial's record states no number of participants
- **THEN** its heading is the registry's title, and the title is not repeated in the fold

### Requirement: A trial's design and state are said in plain words
Under its heading a trial's entry SHALL say, in the site's fixed plain wording, how people were assigned, whether the trial was blinded or open label, its state with the date it finished when it has finished, and that results are posted with the date they were posted. The registry's exact terms for the design SHALL be shown inside the fold. No wording SHALL say that a trial is open to participants or how it turned out.

#### Scenario: Randomised, quadruple-blind, completed, results posted
- **WHEN** a trial is randomised and quadruple-blind, completed on 5 March 2023 and posted results on 30 June 2026
- **THEN** the entry reads that people were assigned at random, that it was blinded, that it finished on 5 March 2023 and that results were posted on 30 June 2026, and its fold gives "Randomised, quadruple-blind" in the registry's terms

#### Scenario: Open-label trial
- **WHEN** a trial's masking is none
- **THEN** the entry says it was open label and says what that means in a few words

#### Scenario: Trial under way
- **WHEN** a trial is under way
- **THEN** the entry says it is under way, with no finishing date, and nothing says it is recruiting

#### Scenario: Design the record does not state
- **WHEN** a trial's record states neither allocation nor masking
- **THEN** the entry says nothing about how people were assigned or whether it was blinded

### Requirement: A trial entry says what it measured where a reading allows
Where a trial's first main measure has a usable reading of its kind, the entry SHALL say in one sentence what the trial measured, in the same fixed wording "The record in brief" uses for that kind, with how long it was followed when that reading is usable too. The entry SHALL say that a model read that sentence and that it was checked against the record. With no usable reading the entry SHALL have no such sentence, and the measures SHALL remain listed in the registry's words inside the fold.

#### Scenario: Symptom score followed for four weeks
- **WHEN** a trial's first main measure has a measure reading of symptom score, a title that names a change, and a follow-up reading of 4 weeks
- **THEN** the entry says it measured the change in a symptom score over 4 weeks, and says a model read that and it was checked against the record

#### Scenario: Measure of a trial that has not ended
- **WHEN** a trial that has not ended and has posted no results has a usable reading of its first main measure
- **THEN** the entry says what it sets out to measure, and does not say that it measured anything

#### Scenario: Time until an event, followed for years
- **WHEN** a trial's first main measure is read as a time until an event with a follow-up of 4 years
- **THEN** the entry says people were followed for 4 years, and does not say the event was measured "over" 4 years

#### Scenario: Same wording as the record in brief
- **WHEN** the claim's largest trial has a measure sentence in its entry
- **THEN** the words for the measure are the same as in the brief's answer about what the largest trial measured

#### Scenario: No usable reading
- **WHEN** a trial has no reading, a reading too unsure to use, or a reading of a kind the site has no words for
- **THEN** the entry has no measure sentence and its fold lists the planned measures in the registry's words

### Requirement: Posted results are a table that says what its numbers are
Inside a trial's fold, a posted main measure with one value for each group SHALL be shown as a table with a row for each group, its value as the registry wrote it and how many were analysed, under a caption that names the measure and says what the numbers are. No figure SHALL be larger than body text, and nothing SHALL draw a result. The entry SHALL say that the registry record states what the measure runs from and to, and SHALL link to the record. The fold's control SHALL say whether posted results are inside.

#### Scenario: Three groups with a mean change
- **WHEN** a trial posted a mean change with a standard deviation for each of three groups, each with 39 analysed
- **THEN** the fold shows a table of three rows with the group, the mean change, the standard deviation and 39 analysed

#### Scenario: Measure that is a change
- **WHEN** the posted measure's title names a change and a group's value is below zero
- **THEN** a line under the table says a minus number is a fall

#### Scenario: Posted comparison
- **WHEN** the record gives a p value for a comparison of two groups
- **THEN** it is shown under the table as the record states it, naming the two groups, with no word on whether the measure was met

#### Scenario: Outcome posted in several rows
- **WHEN** a posted main measure gives several rows of values for each group
- **THEN** no table is shown for it, and the entry says the values are in the registry record

#### Scenario: Fold with no results
- **WHEN** a trial has posted no results
- **THEN** the fold's control does not mention results

#### Scenario: Narrow screen
- **WHEN** a reader opens a trial's results on a screen 320 pixels wide
- **THEN** the table is readable without the page being widened, and every control is at least 44 pixels tall

### Requirement: A claim page answers fixed questions from its records
Every claim page SHALL show a section, "The record in brief", of at most six fixed questions, each with a short answer. An answer SHALL be fixed wording filled only with counts, sizes, dates and names from the records the page shows, or from a reading the export carries. No person SHALL write an answer, and no model SHALL write the words of one.

#### Scenario: Claim with trials
- **WHEN** a reader opens a claim with 3 trials on record, the largest stating 135 participants
- **THEN** the section answers "In 3 trials. 135 people in the largest", and the answer does not begin with "Yes"

#### Scenario: Comparison group
- **WHEN** 1 of the claim's 3 trials names a sham comparator and the claim's approach is a device
- **THEN** the section asks whether it was compared with a dummy device and answers that one record names a dummy device, and the opened answer says the other two records name no comparison

#### Scenario: What the largest trial measured
- **WHEN** the largest trial's main measure has a measure reading of symptom score and a follow-up reading of 4 weeks
- **THEN** the section answers with the site's fixed phrase for a symptom score, worded as a change when the registry's title names a change, and "over 4 weeks"

#### Scenario: Measure with no reading
- **WHEN** the largest trial's main measure has no stored reading
- **THEN** the answer is the registry's title for the measure in quotation marks, and the opened answer says it is in the registry's words

#### Scenario: Results posted
- **WHEN** all 3 of the claim's trials have results posted, the latest on 30 June 2026
- **THEN** the section says results were posted by all 3 trials and gives that date, and a link under the answer, shown without opening it, leads to the trials' posted results on the page

#### Scenario: Trial with no stated enrolment
- **WHEN** no trial of the claim states how many participants it enrolled
- **THEN** the answer about testing in people gives the number of trials and no size

### Requirement: Each question has one fixed place
The questions SHALL be shown in a fixed order in two groups: how the treatment was tested, then where the records stand now. A question's place SHALL NOT depend on its answer. A question that has nothing to ask about, because the claim has no trial, SHALL be left out, and the others SHALL keep their order. An answer that a kind of record is absent SHALL say "None on record" in the question's own place, with the date of the last record of that kind where the rule has one. No heading, mark, colour or order SHALL say that an answer counts for or against the treatment. No answer SHALL say why a record is absent, predict, advise, or say that a trial is open to participants.

#### Scenario: Same questions, opposite answers
- **WHEN** one claim has a trial under way and an approval, and another has neither
- **THEN** both pages show "A trial under way?" and "Approved by a regulator?" in the same group and the same order

#### Scenario: No trial under way
- **WHEN** a claim has trials on record and none is under way
- **THEN** the answer is "None on record" with the date the last one completed

#### Scenario: A trial under way
- **WHEN** 2 of a claim's trials are under way
- **THEN** the answer says 2 are under way, and does not say a trial is recruiting or open to participants

#### Scenario: Approved claim
- **WHEN** a reader opens a claim whose status is Approved
- **THEN** the answer names the regulator and the date of the approval and says, without being opened, that an approval is not advice to take a treatment

#### Scenario: Approval entered by hand
- **WHEN** the approval's record names no regulator as its source
- **THEN** the answer gives the date of the approval and the same caution, and names no regulator

#### Scenario: Claim with no trial on record
- **WHEN** a reader opens a claim with no trial on record
- **THEN** the section says no trial in people is on record, says what the first report was about, answers the approval question, and has no question about a comparison, a measure, posted results or a trial under way

#### Scenario: Wording with a verdict
- **WHEN** the site is built and a question, an answer or a group name contains the word "abandoned"
- **THEN** the build fails and quotes the wording

### Requirement: Every answer shows the record it was read from
Each answer SHALL open to show the record it was read from as a link, what was read from it, whether it was read directly from the record or by a model, and the date the record was read. An answer read by a model SHALL also show the exact words it was read from and how sure the reading is, as a word and a percentage. An answer that counts trials SHALL link to them on the page. The section SHALL say that its answers are read from the records on the page, that they describe the records and not the treatment, and that they are not advice.

#### Scenario: Answer read directly
- **WHEN** a reader opens the answer about a comparison group
- **THEN** it names the trial by its registry identifier as a link, gives the design as the registry states it, and gives the date the record was read

#### Scenario: Answer read by a model
- **WHEN** a reader opens an answer that rests on a reading
- **THEN** it shows the words the reading was read from in quotation marks, says a model read them and that they were checked against the record, and says how sure the reading is

#### Scenario: Reading the model is certain of
- **WHEN** a reading's confidence is 1
- **THEN** the opened answer says how sure the reading is as 99%, never 100%

#### Scenario: Every answer opens to something
- **WHEN** a reader opens any answer in the section
- **THEN** it shows at least the record or records it was read from and the date they were read

#### Scenario: Without scripting
- **WHEN** a reader opens a claim page with scripting turned off
- **THEN** every answer can still be opened

#### Scenario: Narrow screen
- **WHEN** a reader opens a claim page on a screen 320 pixels wide
- **THEN** each question is above its answer, every row and every link in an opened answer is at least 44 pixels tall, and the page is not widened

### Requirement: The brief carries no result values
The section SHALL NOT show a trial's posted result values or a posted comparison. The answer about what the largest trial measured SHALL link to that trial's entry on the page, where its posted results are.

#### Scenario: Largest trial with posted values
- **WHEN** the largest trial has posted a value for each of three groups and a p value
- **THEN** the section shows none of those numbers, and the opened answer links to the trial's entry

### Requirement: The digest says when trials state no phase
When a claim's status is Trial registered and it has trials on record, the digest panel SHALL say, after what the status means, how many trials are on record, how many of them have finished, and that the registry gives none a phase.

#### Scenario: Three trials with no phase
- **WHEN** a reader opens a claim whose status is Trial registered and which has 3 trials on record, none stating a phase
- **THEN** the digest says 3 trials are on record and all have finished, and that the registry gives none a phase

#### Scenario: Status with a phase
- **WHEN** a reader opens a claim whose status is Phase 2 trial
- **THEN** the digest has no sentence about a missing phase, and counts the trials' states instead

### Requirement: The home page lists what is dated, day by day
Under the lookup, the home page SHALL show one list of what is dated for published claims, newest first: news reports by their publication date, registry records by their event date, and dated promises by the date promised. Rows SHALL stand under dated headings: one per day for the fourteen days up to the day the registries were last checked, one per week for the rest of that year, one per year before it. A heading SHALL say how many rows of each kind it holds.

#### Scenario: A day in the last fortnight
- **WHEN** the registries were last checked on 14 November 2026 and two news reports and one registry record are dated 9 November 2026
- **THEN** the list has a heading for Monday 9 November that says "2 reports, 1 registry record", with those three rows under it, the reports first

#### Scenario: Earlier in the year
- **WHEN** a news report is dated 28 October 2026
- **THEN** its row stands under the heading "Week of 26 October"

#### Scenario: An earlier year
- **WHEN** a news report is dated 9 January 2017
- **THEN** its row stands under the heading "2017"

#### Scenario: Unpublished claims
- **WHEN** a claim has not been published
- **THEN** none of its reports, records or promises has a row

### Requirement: The day-by-day list is dated by the last check
Above the list the home page SHALL name the day the registries were last checked. No heading SHALL be dated later than the last check. With scripting on, a heading with nothing under it SHALL NOT be shown; as built, a day in the seven up to the last check with nothing dated keeps its heading and says that nothing is dated. A heading SHALL be worded "Today" or "Yesterday" only when that is so on the reader's own date.

#### Scenario: Checked on the reader's own date
- **WHEN** the registries were last checked on 14 November 2026, a report is dated that day and a reader opens the page that day
- **THEN** the page names Saturday 14 November 2026 as the day of the last check and the first heading reads "Today, Saturday 14 November"

#### Scenario: A page built before the reader's date
- **WHEN** the registries were last checked on 13 November 2026 and a reader opens the page on 15 November
- **THEN** the page names 13 November as the day of the last check and no heading says "Today" or "Yesterday"

#### Scenario: A day with nothing dated
- **WHEN** no report, record or promise is dated 10 November 2026 and a reader opens the page with scripting on
- **THEN** the list shows no heading for 10 November

#### Scenario: An export with no day of last check
- **WHEN** the export does not say when the registries were last checked
- **THEN** the home page shows neither the dated head nor the day-by-day list, the tabbed lists follow the lookup, and no other day stands in for the missing one

### Requirement: Rows are of three kinds, and each kind can be shown alone
Each row of the day-by-day list SHALL say its kind in words: a news report, a registry record or a promised date. Above the list, one field SHALL name every kind that has a row and SHALL narrow the list to the kind chosen, or show every kind. While a kind is chosen, a heading with no row of it SHALL NOT be shown. The pick SHALL be recorded in the page's address. Pale amber SHALL be the ground of promised dates only.

#### Scenario: Picking a kind
- **WHEN** a reader chooses registry records
- **THEN** only registry rows are listed, under the headings that hold one, and the address names the pick

#### Scenario: The controls as a key
- **WHEN** a reader opens the home page's kind field
- **THEN** it offers "Everything", "News reports", "Registry records" and "Promised dates", leaving out a kind with no row

#### Scenario: A kind read aloud
- **WHEN** a screen reader reads a registry row
- **THEN** it is told the row is a registry record without relying on the row's ground

### Requirement: A report row sets the report beside the record
A news report's row SHALL lead with the outlet and the date, then the outlet's title in quotation marks leading to the claim page, then the claim's intervention and indication. In a column on the right on a wide screen, and under the claim on a phone, the row SHALL show the claim's status now in words with its place on the path, its no-signal note and its counts; a count of no trials SHALL NOT be shown. One line above the list SHALL say once what that column is. The column SHALL be one control, named by the status and what it opens, that opens the row's detail: the evidence stage when the claim was first reported, the status's gloss and meaning, the path with each place named, why the claim stands there, and the claim's latest promise, marked as a promise. Without scripting, and in print, the detail SHALL be shown. Reports of one claim dated the same day SHALL share one row that names each outlet. The site SHALL add no wording of its own about a title.

#### Scenario: A report of an animal study
- **WHEN** a claim first reported from an animal study stands at preclinical only and has a report dated 11 November 2026
- **THEN** the row shows the quoted title with its outlet and date and "Preclinical only" with the first place on the path marked, and its detail gives "Animal study" as the evidence when first reported and "No trial in people on record"

#### Scenario: Opening the detail
- **WHEN** a reader presses the status of a row, by pointer, touch or keyboard
- **THEN** the detail opens under the row, the control says it is expanded, and pressing it again closes the detail

#### Scenario: Two outlets on one day
- **WHEN** two outlets report the same claim on 6 October 2026
- **THEN** the list has one row for that claim that day, with the first title quoted and both outlets named

#### Scenario: One claim reported on two days
- **WHEN** a claim has reports dated 6 October and 13 October 2026
- **THEN** it has a row under each date

### Requirement: A report row says what the records add
Under the outlet's title, a report row SHALL show at most one line of counts in numerals: how many trials are on record and how many have posted results. A count the export does not hold SHALL be left out, never estimated. The row SHALL NOT draw a record strip; the claim page does. The row SHALL also carry at most two sentences built by fixed rules from the claim's records: the first two that apply, in one fixed order of preference, each stating a count or a date only. These sentences SHALL follow the counts for a screen reader and SHALL NOT be shown in sight on the row.

#### Scenario: The order of preference
- **WHEN** more than two sentences apply to a claim
- **THEN** the row's screen-reader text carries the first two of: a regulator's decision with its date; the year of the first registered trial, when it is two or more calendar years before the report; how many trials are on record, how many are completed and how many have posted results; that no record is dated since the first report, with the no-signal years

#### Scenario: A trial registered long before the report
- **WHEN** a claim reported in 2026 has five trials on record, the first registered in 2012, three completed and two with results posted
- **THEN** the row shows the counts "5 trials" and "2 with results posted" in numerals; its screen-reader text says the first trial was registered in 2012, 14 years before the report, and that 5 trials are on record, 3 completed, 2 with results posted

#### Scenario: Nothing since the report
- **WHEN** a claim reported in 2017 from laboratory work has no trial and carries "No signal for 9 years"
- **THEN** the row shows the count "0 trials", and its screen-reader text says no record is dated in the 9 years since the first report

#### Scenario: Nothing to add
- **WHEN** a claim reported from an animal study has no trial, no regulator’s decision and no no-signal note
- **THEN** the row shows the count "0 trials" and no sentence

#### Scenario: An approval
- **WHEN** a claim has a regulator's approval dated 3 September 2026
- **THEN** the claim page's strip shows the decision mark at that date and the first sentence of the row's screen-reader text is the approval as recorded, with that date

### Requirement: Row sentences describe records and nothing else
A sentence the site writes for a home page row or for a record strip's text alternative, a line of counts beside a strip, and the words of a strip's key SHALL pass the site's checks for verdict wording and for wording about how a trial turned out. None SHALL say that a promise was kept, missed or late, characterise the time between a report and a record, or present a trial as open to join. A build SHALL fail when the wording of any of them breaks one of these rules.

#### Scenario: A promised date that has passed
- **WHEN** a claim's report promised trials for 2020 and no trial is on record
- **THEN** the row shows the promise with its year and the status now, the strip marks 2020 as a promised date, and no sentence, count or key says the date passed or the promise was missed

#### Scenario: Wording that judges
- **WHEN** a sentence's wording is changed to include "still" or "only" before a count
- **THEN** the site's build fails and names the sentence

#### Scenario: Key wording with a verdict
- **WHEN** the site is built and the key names a mark with verdict wording
- **THEN** the build fails and names the wording

### Requirement: A registry row names the report it belongs to
A registry record's row SHALL lead with the claim's newest news report: its title quoted, leading to the claim page, with its outlet and date, and "First reported N years ago" when the claim was first reported in an earlier year than the record. It SHALL name the intervention and indication, and show what was recorded as one dated item: the registry's identifier leading to the record at its source, what was recorded worded as something done to that record ("registered", "results posted", "terminated"), never in a status's words, and its date. The claim's status SHALL stand in the same column, and open the same detail, as on a report row. Registry rows SHALL be listed for records dated in the ninety days up to the last check. An event with a confidence below 1 SHALL show it in the words the claim page uses.

#### Scenario: A trial registered last week
- **WHEN** a trial for a published claim was registered on 2 November 2026
- **THEN** its row quotes the claim's newest report with its outlet and date, gives the trial's identifier as a link to the registry with "registered" and the date, and shows the claim's status now

#### Scenario: A record for a story from an earlier year
- **WHEN** a trial dated 12 November 2026 belongs to a claim first reported in March 2022
- **THEN** its row says "First reported 4 years ago" above the quoted title

#### Scenario: A follow-up paper scored 0.6
- **WHEN** a follow-up paper with a confidence of 0.6 is dated 26 October 2026
- **THEN** its row shows "Medium match · 60%"

#### Scenario: A record from last year
- **WHEN** a trial for a published claim was completed in 2024
- **THEN** it has no row on the home page and is listed on the claim page as before

### Requirement: A registry row says when a status changed
A row for a registry record dated on a day the claim's status changed SHALL say "Changed" in its status column, with the status before that day once and the status from it as the column's status, on a ground that sets it apart from rows that did not change. Where several of the claim's records are dated that day, only the first listed SHALL say so. Where the claim has changed again since, its detail SHALL say so and give the status now. Any other registry row SHALL show the claim's status now, as a report row does.

#### Scenario: An approval that changed the status
- **WHEN** a regulator's approval dated 20 October 2026 moved a claim from Phase 3 trial to Approved
- **THEN** the row's status column says "Changed", "from Phase 3 trial" and "Approved", with the last place on the path marked, on the panel blue

#### Scenario: A record that changed nothing
- **WHEN** a further trial is registered for a claim already at Phase 3 trial
- **THEN** the row's status column shows Phase 3 trial and does not say "Changed"

### Requirement: Promised dates to come are offered with the list
Dated promises whose date is later than the last check SHALL be offered with the day-by-day list when the reader chooses promised dates, apart from its dated headings and earliest first, behind one line that says how many there are and gives the next date; the line SHALL open them in place. With scripting off the line SHALL stand above the list.

#### Scenario: Promises still to come
- **WHEN** nine published claims have a promised date after the last check, the earliest is 31 December 2026, and a reader chooses promised dates
- **THEN** the line says there are 9 promised dates to come and that the next is 31 Dec 2026, and pressing it lists the nine, earliest first

#### Scenario: Every kind shown
- **WHEN** a reader has chosen no kind
- **THEN** the line is not shown

#### Scenario: Nothing promised to come
- **WHEN** no published claim has a promised date after the last check
- **THEN** the line is not shown

### Requirement: A promise row shows the promise beside the status now
A promised date's row SHALL show the claim's latest dated promise on pale amber with its year, the report it came from and the claim's status now. A promise dated on or before the last check SHALL be listed under that date's heading. The page SHALL add no wording about a date having passed.

#### Scenario: A promise for a past year
- **WHEN** a claim's latest promise is dated 2020 and the claim stands at preclinical only
- **THEN** its row stands under the heading "2020", shows the promise with 2020 in bold on pale amber and "Preclinical only", and says nothing about the date

### Requirement: The day of the last check shows one older claim
Under the day-by-day list, under a heading of its own, the home page SHALL show one report row for a claim first reported in a year before the last check, chosen by a fixed rule from that day's date so that it differs from one day to the next and is the same for every reader. The heading SHALL say it was picked by the date. It SHALL be shown in every span of time, and SHALL be left out by a kind, status or topic it does not meet. When no published claim was first reported in an earlier year, no such row SHALL be shown.

#### Scenario: A day with nothing dated
- **WHEN** nothing is dated on the day of the last check and published claims include some first reported before that year
- **THEN** one older claim's row stands after every dated heading, under a heading that says it was picked by the date

#### Scenario: Two readers on one day
- **WHEN** two readers open the home page built from the same export
- **THEN** both see the same older claim

#### Scenario: The next day
- **WHEN** the registries are checked again the next day and the site is rebuilt
- **THEN** the older claim shown is a different one, as long as more than one qualifies

### Requirement: The day-by-day list marks a reader's last visit
For a reader with scripting on whose browser keeps the day of an earlier visit, the day-by-day list SHALL draw one line between the rows dated from that day on and the rows dated before it, naming that day: the span the since line counts. On a first visit, where the browser keeps nothing, or when nothing is dated in the span, no line SHALL be drawn. Rows of this list SHALL NOT carry "New". The day SHALL be the one the since line uses, kept in the reader's browser only.

#### Scenario: A later visit
- **WHEN** a reader last opened the home page on 7 November and opens it on 14 November, and ten reports are dated from 7 November on
- **THEN** one line naming 7 Nov 2026 stands under the rows of 7 November and above the heading for 6 November

#### Scenario: A first visit
- **WHEN** a reader opens the home page with nothing kept in their browser
- **THEN** no line is drawn

#### Scenario: One kind shown
- **WHEN** the reader picks registry records and none is dated from their last visit on
- **THEN** no line is drawn

### Requirement: The day-by-day list opens on its day headings
With scripting on, the day-by-day list SHALL first show what is dated in the seven days up to the last check, and SHALL let a reader choose the span it keeps to from one field: the past week, the past month, the past year or all time, each counted back from the day of the last check. The pick SHALL be recorded in the page's address. Within a span, headings earlier than the day headings SHALL be shown a batch at a time from one control directly under the list that says how many rows remain. Where a span narrower than all time has been read to its end, the page SHALL say so, or that nothing is dated in it, and SHALL offer the next wider span with one press. The rows under its day headings SHALL be in the page as built. The earlier headings and the promised dates still to come SHALL be fetched the first time a reader asks for a span wider than the past week, for promised dates, or for an address that names an earlier heading. With scripting off, and in print while they are not in the page, the list SHALL show its day headings and SHALL say how many earlier rows and how many promised dates still to come are not shown, and that every claim is also listed under its topic, with a link to the topics. An address that names a heading SHALL show the list opened as far as that heading, widened to all time when the heading is outside the span.

#### Scenario: Opening the home page
- **WHEN** nine reports are dated in the seven days up to the last check and thirty earlier headings exist
- **THEN** those nine rows are shown under their day headings, the earlier headings are not in the page, and under the rows the page says that is everything dated in the past week and offers the past month

#### Scenario: Widening the span
- **WHEN** a reader asks for the past month
- **THEN** the earlier headings are fetched, the headings dated in the past month are shown, and a control under them says how many rows are earlier and shows the next headings when pressed

#### Scenario: Nothing in the span
- **WHEN** nothing is dated in the seven days up to the last check
- **THEN** the page says nothing is dated in the past week and offers the past month

#### Scenario: An address naming an earlier week
- **WHEN** the home page is opened at an address that names the heading "Week of 5 October"
- **THEN** the earlier headings are fetched, the list is widened to all time and opened as far as that heading, and the page is at it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every day heading and its rows are shown, and the list says how many earlier rows are not shown and links to the topics

### Requirement: The Claims list is narrowed and paged like the others
The home page's Claims list SHALL show each claim's name and headline, the date it was first reported, how much it has been tested in people, its latest dated promise where it has one, and its status with its place on the path. It SHALL be narrowed by the home page's status and topic controls and read a page at a time, as the other lists are.

#### Scenario: Narrowed to a status
- **WHEN** a reader picks Phase 3 trial among the home page's status counts while the Claims list is in view
- **THEN** the list shows only claims whose status is Phase 3 trial, and says how many there are

#### Scenario: Narrowed to a topic
- **WHEN** a reader picks a topic while the Claims list is in view
- **THEN** the list shows only that topic's claims

#### Scenario: More claims than a page holds
- **WHEN** 84 claims are published
- **THEN** the Claims list shows the first page and says which rows of 84 are in view

#### Scenario: Promise beside the record
- **WHEN** a listed claim has a dated promise for 2027
- **THEN** its row shows the promise on the site's promise colour, between how much it has been tested and its status

### Requirement: A list of claims says how much each has been tested in people
Wherever the site lists claims in its claims table, each row SHALL say whether the claim has been tested in people: with trials on record, how many, and beneath it the largest stated size and whether results are posted to the registry; with none, "None on record" and, where the claim records it, what its first report was about. The words SHALL be read by the same rule as the first answer of "The record in brief". A list that carries the column SHALL say, once, that it counts trials on record and does not say what they found. No row SHALL carry a result value, and nothing SHALL order or mark claims by how much they have been tested.

#### Scenario: Claim with three trials
- **WHEN** a list shows a claim with 3 trials on record, the largest stating 135 participants, all with results posted
- **THEN** its row says it was tested in 3 trials, with 135 people in the largest and results posted by all 3

#### Scenario: Claim with no trial
- **WHEN** a list shows a claim with no trial on record whose first report was about a study in animals
- **THEN** its row says "None on record" and that the first report was about a study in animals

#### Scenario: Trials with no results posted
- **WHEN** a list shows a claim with 2 trials on record, neither with results posted
- **THEN** its row says no results are posted

#### Scenario: Same words as the claim page
- **WHEN** a claim's page answers "Tested in people?" with "In 3 trials. 135 people in the largest"
- **THEN** every list that shows the claim gives the same count and the same size

#### Scenario: Topic page
- **WHEN** a reader opens a topic page
- **THEN** its table of claims carries the column, and the line that says what the column counts

#### Scenario: Narrow screen
- **WHEN** a reader opens a list of claims on a screen 320 pixels wide
- **THEN** each claim is a block with "Tested in people" as a labelled line, and the page is not widened

### Requirement: Reported statements on the claim page
A claim page SHALL list the claim's approved reported statements under their own heading, placed after the summary and before the records. Each statement SHALL show its text, its kind, its article by outlet and date with a link, and how sure the pipeline is that the article says it, as a word and a percentage. A claim with no approved statement SHALL show no such section.

#### Scenario: Claim with three statements from one report
- **WHEN** a reader opens a claim with three approved statements from one article
- **THEN** the page lists the three under the report's outlet and date, each with its confidence

#### Scenario: Claim with no statement
- **WHEN** a claim has no approved statement
- **THEN** the page shows no statements section and no placeholder for one

### Requirement: A statement is worded as a report's statement
Each statement SHALL be shown as something its report said, with the site's wording for how firmly the report put it and for who the report had saying it. The section SHALL say that a report's statement is not a record and that the records follow. The site SHALL NOT show a statement as a finding, and SHALL NOT say whether a statement held, was confirmed or was contradicted.

#### Scenario: Possibility voiced by a researcher
- **WHEN** a statement was put as a possibility and said by a researcher
- **THEN** the page reads that the report had a researcher saying it could be so, and names no one

#### Scenario: Statement beside a trial result
- **WHEN** a claim has a statement of an effect and a trial with posted results
- **THEN** the page shows both, in their own sections, and no word compares them

### Requirement: A statement shows what the report said it rested on
Each statement SHALL show its basis in the site's words: a study in people, a study in animals, laboratory work, or that the report did not say. The wording SHALL attribute the basis to the report.

#### Scenario: Effect reported from a mouse study
- **WHEN** a statement's basis is a study in animals
- **THEN** the page says the report gave a study in animals as its basis

### Requirement: Statement codes are worded by the site
The site SHALL word each kind, firmness, speaker role and basis code itself and SHALL fail the build on a code it has no wording for. The wording SHALL pass the site's check against verdict wording.

#### Scenario: Kind code without site wording
- **WHEN** the export carries a statement kind the site has no wording for
- **THEN** the site build fails and names the code

### Requirement: The method page explains reported statements
The method page SHALL explain that statements are read from a report by a language model, put in the site's own words, checked against the report and shown with a confidence; that they are what a report said and not what is on record; and that they never change a status.

#### Scenario: Reader doubts a statement
- **WHEN** a reader follows the method link from the statements section
- **THEN** they can read how a statement is found, what its confidence means and how to report an error

### Requirement: Organisations on the claim page
A claim page SHALL list each of the claim's organisations once, under its own heading, with its name, its roles in the site's words, and, when it is identified, its kind, country, website, a link to its registry record and the match score. A sponsor's role SHALL link to the trials it sponsors. A claim with no organisation SHALL show no such section.

#### Scenario: Claim with a university and a company
- **WHEN** a reader opens a claim whose report names a university and whose three trials are sponsored by one company
- **THEN** the page lists the university as named in the report and the company as sponsor of three trials, each trial linked

#### Scenario: Claim with no organisation
- **WHEN** a claim names no organisation
- **THEN** the page shows no organisations section and no placeholder for one

### Requirement: An unidentified organisation is listed plainly
An organisation that is not identified SHALL be shown by the name it was given with its roles, and SHALL say, where its row opens, that it was not matched to a registry record. It SHALL show no kind, country or website.

#### Scenario: Start-up the registry does not know
- **WHEN** a claim names a company with no approved match
- **THEN** its row shows the report's name and role, and opening it says no registry record was matched

### Requirement: Organisations are listed without rank or judgement
The organisations section SHALL order organisations by role and then by name. It SHALL NOT rank them, count their other claims, describe their standing, or say that an organisation endorses, backs or vouches for the claim. It SHALL say that the registry identifies an organisation and does not verify its part in the claim. The site SHALL word each kind and role code itself and SHALL fail the build on a code it has no wording for.

#### Scenario: Kind code without site wording
- **WHEN** the export carries an organisation kind the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Well-known and unknown organisations together
- **WHEN** a claim names a large university and a small clinic in the same role
- **THEN** they are listed in name order, with the same facts shown for each

### Requirement: A report published by a named organisation says so
Where the claim page names a source article that is marked as published by one of the claim's organisations, it SHALL say, beside that report, that the report is on that organisation's website. The wording SHALL state where the report is and SHALL NOT call it promotional, biased or unreliable.

#### Scenario: University press release
- **WHEN** a claim's report is marked as published by Kyoto University
- **THEN** the page says, beside the report, that it is on Kyoto University's website

#### Scenario: Newspaper report
- **WHEN** a claim's report carries no such mark
- **THEN** the page says nothing of the kind beside it

### Requirement: No person is named in the organisations section
The organisations section SHALL NOT show the name of a researcher, an investigator, an author or any other person.

#### Scenario: Trial sponsored by a person
- **WHEN** one of a claim's trials is sponsored by a person
- **THEN** the organisations section lists nothing for that sponsor

### Requirement: Papers on the claim page
A claim page SHALL list each of the claim's papers once, under its own heading, grouped by role: the paper first reported, results papers listed by a trial, follow-up papers, and related research. Each entry SHALL show the title linked to the paper, the journal, the year, the kind of publication, and the facts the export carries for it. A claim with no paper SHALL show no such section.

#### Scenario: Claim with an origin paper and two results papers
- **WHEN** a reader opens a claim that has an origin paper and a trial with two results papers
- **THEN** the page lists three papers, the origin paper under its own group and two under the trial's results

#### Scenario: Paper with two roles
- **WHEN** a paper is both the origin paper and a results paper of a trial
- **THEN** it is listed once, in the origin paper's group, and names the trial it reports

#### Scenario: Claim with no paper
- **WHEN** a claim has no paper
- **THEN** the page shows no papers section and no placeholder for one

### Requirement: A results paper names its trial
A results paper's entry SHALL name the trial whose record lists it, linked to that trial's entry, and SHALL say whether the sponsor listed the paper or the registry linked it. A trial's entry SHALL lead to its results papers.

#### Scenario: Reader goes from a trial to its paper
- **WHEN** a reader opens a trial entry whose record lists a results paper
- **THEN** the entry links to the paper's entry, and the paper's entry links back to the trial

### Requirement: A paper says whether it studied people or animals
A paper's entry SHALL identify its human or animal subject headings as the index's subject headings, not as proof of a study in living participants. It SHALL state nothing when neither heading is recorded. These headings SHALL remain separate from the claim's confirmed evidence stage.

#### Scenario: Paper using extracted human teeth
- **WHEN** a laboratory paper has human and animal subject headings
- **THEN** its entry attributes those headings to the index without saying the treatment was studied in people

#### Scenario: Paper of a study in mice
- **WHEN** a paper's facts include the animal subject heading
- **THEN** its entry identifies that heading and attributes it to the index

#### Scenario: Paper with no statement
- **WHEN** a paper's facts state neither heading
- **THEN** its entry says nothing about human or animal headings

### Requirement: The claim page counts its records in people and in animals
A claim page SHALL count its trial records and papers separately, without deriving a count of human or animal studies from indexing terms. These are counts of records, not independent studies or participants. A paper listed in multiple roles SHALL count once. Missing paper facts SHALL NOT exclude a listed paper. An empty record set SHALL show no count; legacy exports without structured papers SHALL retain their existing display.

#### Scenario: Claim with three trials and one mouse paper
- **WHEN** a claim has three trials and one paper with an animal subject heading
- **THEN** the page states three trial records and one paper

#### Scenario: Laboratory paper with human and animal headings
- **WHEN** a claim has no trial and one paper with both headings
- **THEN** the page states one paper, without implying a human trial

#### Scenario: Claim with no such record
- **WHEN** a claim has neither trials nor papers
- **THEN** the page shows no record count

### Requirement: Papers are worded without a verdict
The site SHALL word each paper fact code itself and SHALL fail the build on a code it has no wording for. It SHALL NOT say that a paper supports, confirms, proves or refutes a claim, and SHALL NOT rank papers by quality. The papers section SHALL say that a paper is not a trial record and does not set the status.

#### Scenario: Kind code without site wording
- **WHEN** the export carries a publication kind the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Randomised trial report
- **WHEN** a paper's first kind is randomised trial
- **THEN** its entry reads that it is a report of a randomised trial, and says nothing of what the trial found

### Requirement: A retracted paper is marked where it is listed
A paper whose facts state that it is retracted SHALL be marked as retracted in its entry, in words.

#### Scenario: Retracted follow-up paper
- **WHEN** a claim page lists a follow-up paper marked retracted
- **THEN** its entry says the paper has been retracted

### Requirement: Paper facts show when their record was read
Each paper's entry SHALL show the date its index record was read, and the papers section SHALL name the index the facts come from.

#### Scenario: Record read on 3 October 2026
- **WHEN** a paper's facts were read from a record fetched on 3 October 2026
- **THEN** the paper's entry shows that date

### Requirement: Archived addresses answer gone
The address of an archived claim or source page SHALL answer with status 410 and a short page saying the page was taken down and on which date. It SHALL NOT state the reason. Archived items SHALL NOT appear in any feed, the sitemap, the lookup file or the data file.

#### Scenario: Reader opens an archived claim
- **WHEN** a reader opens the address of a claim archived on 14 November 2026
- **THEN** the response has status 410 and says the page was taken down on 14 November 2026

### Requirement: Confidence is shown with every match
Each entity match a claim page or source page shows SHALL carry its score as a word and a percentage, such as "High match · 92%", with its reasons available on request. The words and their bands SHALL be set by the site. A match a person approved SHALL keep its score. Pending candidates SHALL be listed apart from the matches that produced the status and SHALL NOT count toward it.

#### Scenario: Claim with one rule-approved trial and one pending candidate
- **WHEN** a reader opens the claim page
- **THEN** the trial that produced the status shows "High match" with its percentage, and the pending candidate is listed separately with its own score

### Requirement: A record page sets its title and section headings in the heading face
A claim page and a topic page SHALL set the title in their band and their section headings in the heading face, a serif served from the site itself. The status label, the records and every other role SHALL stay in the page's face. A page that is not a claim or a topic page SHALL NOT load the heading face ahead of need.

#### Scenario: A claim page
- **WHEN** a reader opens a claim page
- **THEN** the title and the section headings are in the heading face, the status label is in the page's face, and no font is fetched from another site

#### Scenario: A long headline
- **WHEN** a claim's headline is longer than 110 characters and the page is 1400 pixels wide
- **THEN** the title is set at the smallest of its three sizes and stays beside the status card

### Requirement: A claim's band names its topic as a path and carries the summary
On a claim page the band SHALL show the topic as a path of two links, the topics and the claim's topic, ahead of the title. From 40rem wide the band SHALL show the claim's summary under the title, held to five lines with a control to show the rest, and the sheet SHALL NOT show it. Below 40rem the sheet SHALL open with the summary and the band SHALL NOT show it. The summary SHALL never be drawn twice.

#### Scenario: Wide screen
- **WHEN** a claim page is read at 1400 pixels wide
- **THEN** the summary stands under the title in the band and the sheet starts with what follows it

#### Scenario: Phone
- **WHEN** the page is read at 375 pixels wide
- **THEN** the band holds the path, the title, the facts and the status card, and the summary is in the sheet

### Requirement: The status card's heading is in sight
The status card on a claim's band SHALL show its heading, "Where it stands", in sight as part of the card. Each record line in the card SHALL carry a mark beside its words; the mark SHALL NOT carry meaning the words do not.

#### Scenario: Reading the card
- **WHEN** a reader looks at the status card
- **THEN** "Where it stands" is readable on the card, above the status label

### Requirement: The record band has three tones and the status card is one of them
On a claim page at a width where the section list stands beside the sheet, the band SHALL be drawn in three tones of navy: the sides; one main surface, lighter than the sides, from the masthead to the sheet and as wide as the sheet; and the status card, which SHALL stand on that surface and SHALL be darker than the sides. The title and the status card SHALL stand on the same surface. Adjacent tones SHALL differ by at least 1.3:1. The main surface SHALL be darker than the accent. The status card SHALL NOT be white on a screen in either theme. Text and marks inside the card and on the main surface SHALL meet 4.5:1 against their ground, and a panel opened from the card SHALL be drawn in the page's own colours. Beside the card the title SHALL be set larger than the status label. On paper the band and the card SHALL have no fill.

#### Scenario: Wide screen, light theme
- **WHEN** a reader opens a claim page at 1400 pixels wide in the light theme
- **THEN** the title and the status card stand on one surface lighter than the band's sides and as wide as the sheet, the status card is a darker navy with white lettering, and the status label's info panel opens white with dark lettering

#### Scenario: A sentence-long headline
- **WHEN** a claim's headline is longer than 70 characters and the page is 1400 pixels wide
- **THEN** the title is set larger than the status label beside it

#### Scenario: Phone
- **WHEN** the page is read at 375 pixels wide
- **THEN** the band is one surface a step lighter than the masthead and the status card is the darker tone on it

### Requirement: At a glance is two columns on a wide screen
From 60rem wide, the terms of "At a glance" SHALL be laid out in two columns, each term a cell with its label over its value. A cell whose card is open SHALL take the full width. Below 60rem the terms SHALL be one column.

#### Scenario: Two terms
- **WHEN** a claim has a treatment and a condition and the page is 1400 pixels wide
- **THEN** the two stand side by side, and opening "Why this term" on one gives that term the full width

### Requirement: Article lookup file
The site SHALL publish a file at `/lookup.json` that maps the address of every source article of a published claim to that claim, and gives for each published claim its headline, status wording, no-signal note, first-reported date, latest dated promise and page address. The file SHALL carry the footer notices and the date the registries were last checked. It SHALL contain no article text.

#### Scenario: Article of a published claim
- **WHEN** a published claim has a source article
- **THEN** the lookup file lists that article's address in its comparison form and names the claim

#### Scenario: Two addresses of one article
- **WHEN** an article is reached with or without "www.", a trailing slash, a tracking parameter or a fragment
- **THEN** all of those addresses have the same comparison form

#### Scenario: Unpublished claim
- **WHEN** a claim has not been approved in review
- **THEN** neither the claim nor its articles appear in the lookup file

### Requirement: Looking up a pasted link
The home page's main field SHALL accept the address of a news article as well as search words. An address SHALL be compared with the lookup file in the reader's browser and SHALL NOT be sent to any server. For a tracked article the page SHALL show its claim and status; for an untracked one it SHALL show the tracked claims that share words with the address, stated to be a guess, or say that nothing tracked looks close and that this implies nothing about the story. A shortened link or a social media post SHALL be named as such, with what to paste instead.

#### Scenario: Tracked article
- **WHEN** a reader pastes the address of a source article of a published claim
- **THEN** the claim's headline and status are shown with a link to its page

#### Scenario: The same article shared another way
- **WHEN** the address arrives inside a social site's redirect, an AMP cache or a web archive, or with a mobile host or tracking parameters
- **THEN** it is read as the article itself

#### Scenario: Another outlet's report
- **WHEN** the address is not tracked but its words name a tracked treatment, or share two or more telling words with a tracked claim
- **THEN** those claims are listed as a guess for the reader to check

#### Scenario: Shortened link
- **WHEN** the address belongs to a link shortener
- **THEN** the reader is told to open it and paste the article's own address

### Requirement: Moved addresses lead to the claim
The export SHALL list each published address that no longer has a page of its own because its claim was merged into another or given a new slug, with the slug of the published claim it leads to. Such an address SHALL answer with a permanent redirect to that claim's page, and SHALL NOT be listed as archived. When the claim it leads to is archived, the address SHALL answer 410 like that claim's. When the claim it leads to is off the site for another reason (awaiting audit, or not approved), the address SHALL be listed nowhere and SHALL answer not found, as that claim's own address does, until the claim is published again. The reason for a merge or a rename SHALL NOT be exported. A moved address SHALL NOT appear in any feed, the sitemap, the lookup file or the data file.

#### Scenario: Merged claim's address
- **WHEN** a reader opens the address of a published claim that was merged into another published claim
- **THEN** the response is a permanent redirect to the kept claim's page

#### Scenario: Renamed claim's old address
- **WHEN** a reader opens the address a published claim had before its slug was made again
- **THEN** the response is a permanent redirect to the claim's page at its new address

#### Scenario: Kept claim awaiting audit
- **WHEN** the claim a moved address leads to is awaiting audit
- **THEN** the address is in neither list of the export and answers not found, like the claim's own address

#### Scenario: Kept claim taken down
- **WHEN** the claim a moved address leads to has been archived
- **THEN** the address answers 410

### Requirement: A claim page's lists, tables and panels share one scale
The lists of labelled values, the record rows, the tables and the pale panels of a claim page SHALL take their row padding, the rule between rows, the size of labels and column heads, the size of notes, and a panel's padding and corner from one set of values defined once. A build check SHALL fail when one of them is given a value of its own.

#### Scenario: A row in any section
- **WHEN** a reader compares a row of "At a glance", a registry record, a trial and a timetable row
- **THEN** each has the same space above and below it and the same soft rule between it and the next

#### Scenario: A section drifts
- **WHEN** a stylesheet change gives a record row its own padding
- **THEN** the site's tests fail and name the row

### Requirement: Every table on a claim page has the same head
The timetable, the trials table and the index table SHALL have the same head: small grey semibold column names on the pale table-head ground. No table head SHALL be navy.

#### Scenario: Trials table
- **WHEN** a claim page lists trials
- **THEN** the column names People, Compared with, Main measure, State and Trial are grey on the pale ground, as the timetable's are

### Requirement: A claim page is titled by its claim
The title of a claim page SHALL be the claim's intervention followed by its indication, each worded as the record gives it, with the intervention the more prominent. The page SHALL NOT set the claim's headline, or the title of any news report, as its own title. A news report's title SHALL appear on the page only as a quotation with its outlet and date.

#### Scenario: A claim reported as an approval
- **WHEN** a reader opens the page of a claim for erenumab, for preventing migraine, whose reports say it was approved and whose status is Phase 3 trial
- **THEN** the title reads "erenumab" and under it "Preventing migraine in people who have at least four migraines a month", and the words "EU approves" appear only inside a quoted report's title

#### Scenario: Read aloud
- **WHEN** a screen reader reads the title
- **THEN** it reads the intervention, "for", and the indication as one heading

#### Scenario: The indication is readable on paper

- **WHEN** a reader prints the intervention-and-indication heading from either screen theme
- **THEN** the printed heading distinguishes the indication clearly on paper with background graphics disabled

### Requirement: What the registry lists, beside the approach
The export SHALL carry, for a claim whose approved trials list its intervention under exactly one registry intervention type that maps to the claim's approach, that type and the number of trials that list it, as codes, whoever set the approach. For any other claim it SHALL carry none. A claim page SHALL state it beside the approach label, in the site's own wording, and SHALL NOT say whether the intervention works or is available.

#### Scenario: Registry supports the approach
- **WHEN** a reader opens a claim whose approach is drug and whose 3 approved trials list its intervention as a drug
- **THEN** the page shows the label for drug and states that the registry lists the intervention as a drug in 3 trials

#### Scenario: Approach the registry does not support
- **WHEN** a reader opens a claim whose approach an operator set to gene therapy and whose trials list the intervention as a drug
- **THEN** the page shows the label for gene therapy and nothing about the registry's type

#### Scenario: Claim with no approach
- **WHEN** a reader opens a claim with no approach
- **THEN** the page shows nothing about the registry's type

#### Scenario: Registry type without site wording
- **WHEN** the export carries a registry type the site has no words for
- **THEN** the site build fails and names the type

### Requirement: Clinical index
The site SHALL have a clinical index at `/clinical` that lists the top categories of the MeSH tree under which at least one published claim falls, each with the number of published claims at or below it. A category with no published claim SHALL NOT be listed. The page SHALL say that the categories are MeSH's and that the reader-friendly topics are at the topics page.

#### Scenario: Top category with claims
- **WHEN** 161 published claims have a clinical category at or below "Neoplasms"
- **THEN** the index lists "Neoplasms" with the count 161

#### Scenario: Claim under two top categories
- **WHEN** a published claim's category sits under two top categories
- **THEN** it is counted once under each

#### Scenario: Top category with no claim
- **WHEN** no published claim falls under a top category
- **THEN** the index does not list it

#### Scenario: A category comes only from the checked condition

- **WHEN** a filed claim has an approved condition reading and no trial or paper supporting that category
- **THEN** the clinical index identifies a checked condition term as a possible source and does not imply that every assignment was indexed from a trial or paper

### Requirement: Clinical category page
Each MeSH category at or above a published claim's clinical category SHALL have a page at `/clinical/{descriptor identifier}`. It SHALL show the category's MeSH name, every broader category it sits under, its narrower categories that have published claims with their counts, and the published claims at or below it with their statuses. A claim under several narrower categories SHALL be listed once.

#### Scenario: Category in two places
- **WHEN** a reader opens the page for "Obesity", which sits under two broader categories
- **THEN** the page links to both broader categories

#### Scenario: Claims at and below
- **WHEN** 4 published claims have the category "Dementia" and 20 have narrower ones
- **THEN** the page lists 24 claims with their statuses and the narrower categories with their counts

#### Scenario: Category with no published claim
- **WHEN** a category has no published claim at or below it
- **THEN** it has no page and no link leads to it

### Requirement: Clinical categories on the claim page
A claim page SHALL list the claim's clinical categories by their MeSH names, each linking to its category page, and SHALL say for each which of the claim's trials and papers gave it. A claim with no clinical category SHALL show no such list and no placeholder. The categories SHALL NOT be worded as a diagnosis, as who a treatment is for, or as advice.

#### Scenario: Category from a trial and a paper
- **WHEN** a reader opens a claim whose category "Psoriasis" came from one trial and one paper
- **THEN** the page shows "Psoriasis" linking to its category page, and names that trial and that paper as its source

#### Scenario: Category from the reading of the claim's condition
- **WHEN** a reader opens a claim whose category "Psoriasis" came from the reading of its own condition, scored 0.93
- **THEN** the page says the category is what the claim's own condition was read as, and shows the score 0.93

#### Scenario: Claim with no category
- **WHEN** a reader opens a claim with no clinical category
- **THEN** the page shows no clinical category list

### Requirement: Clinical pages credit the vocabulary
Every page that shows a MeSH category SHALL credit "Medical Subject Headings (MeSH), U.S. National Library of Medicine", state the MeSH year the categories were read from, and say that NLM does not endorse the site.

#### Scenario: Credit on a category page
- **WHEN** a reader opens any clinical category page
- **THEN** the page carries the credit line, the MeSH year and the statement that NLM does not endorse the site

#### Scenario: Export without a MeSH year
- **WHEN** the export carries clinical categories and no MeSH year
- **THEN** the site build fails and says so

### Requirement: Clinical browse is reachable
The clinicians page and the topics page SHALL each link to the clinical index, and the sitemap SHALL list the clinical index and every clinical category page.

#### Scenario: From the clinicians page
- **WHEN** a reader opens the page for clinicians
- **THEN** it links to the clinical index

#### Scenario: Sitemap
- **WHEN** the site is built with 300 clinical category pages
- **THEN** the sitemap lists the clinical index and all 300

### Requirement: Missing paper facts do not establish index absence
A listed paper with no exported index facts SHALL say those details are unavailable here. It SHALL NOT infer that the index holds no record: the paper may not yet have been fetched. Available facts SHALL retain their normal source attribution and fetched timestamp.

#### Scenario: Origin paper is approved after preparation
- **WHEN** the exported origin paper has no fetched facts
- **THEN** its entry describes unavailable details without claiming the index lacks the paper

### Requirement: No-trial wording does not imply a human study
Status explanations, topic summaries and guide text for `no_trial_found` SHALL describe the absence of a matched trial record without asserting a study in people. Confirmed first-report evidence SHALL remain separately visible where available. `preclinical_only` explanations SHALL describe confirmed laboratory or animal evidence.

#### Scenario: Claim has an unknown first-report stage
- **WHEN** a claim with no approved trial and no confirmed evidence stage is displayed or counted in a topic summary
- **THEN** its no-trial wording does not say it was studied in people or only in the laboratory

### Requirement: The site follows the reader's appearance and lets them choose
The site SHALL draw every page in a light theme or a dark theme. With no choice stored, it SHALL follow the device's appearance, including with no script. A switch in the masthead SHALL change the look on every press; a press to the device's own look SHALL clear any stored choice, and a press away from it SHALL store the choice. The choice SHALL be kept in the reader's browser only, sent nowhere, and applied before the first paint. A printed page, the embed and the drawn extension popup SHALL stay light. The dark theme SHALL keep the light theme's meanings: amber for what was promised and nothing else, no colour for any status, and text contrast of at least 4.5:1.

#### Scenario: A device set to dark
- **WHEN** a reader with a device set to dark opens a claim page for the first time
- **THEN** the page is drawn dark, and the switch offers the light appearance

#### Scenario: The reader chooses light
- **WHEN** that reader presses the control
- **THEN** the page is drawn light, and a later page of the site opens light from its first paint

#### Scenario: Back to the device's look
- **WHEN** that reader, now on light, presses the switch again
- **THEN** the page is drawn dark, no choice is stored, and the page follows the device from then on

#### Scenario: Several tabs open
- **WHEN** the reader switches the look in one tab while others of the site are open
- **THEN** the other tabs draw the same look and the choice is written once

#### Scenario: The device changes while the page is open
- **WHEN** no choice is stored and the device switches from dark to light
- **THEN** the open page follows it without a reload

#### Scenario: An embed on a dark device
- **WHEN** a claim's embed is shown inside another site to a reader whose device is set to dark
- **THEN** the embed is drawn light

#### Scenario: Printing in the dark theme
- **WHEN** a reader prints a claim page while it is drawn dark
- **THEN** the printed page is light, with no appearance control

### Requirement: The method page shows an explainer video
The method page SHALL show the explainer video under its lede as a file served by the site itself. The video SHALL NOT play on its own, and nothing of it except its poster image SHALL be fetched before the reader presses play. The page SHALL state the month the registries were checked for the records the video shows, and SHALL carry the video's narration as text. The video SHALL hold to the site's rules: no verdict wording, no medical advice, an outlet's headline only in quotation marks with the outlet named, and no article text.

#### Scenario: Opening the method page
- **WHEN** a reader opens the method page
- **THEN** the video is shown with its poster and controls, is not playing, and the video file has not been requested

#### Scenario: A reader who cannot play it
- **WHEN** a reader cannot or does not play the video
- **THEN** its narration can be read on the page, and the rest of the page explains the method without it

#### Scenario: A claim in the video has since changed
- **WHEN** a claim shown in the video has a newer status than the video shows
- **THEN** the caption's date tells the reader the video's records are as of that month, and the claim page shows the current status

### Requirement: A term in "At a glance" is one line that opens
On a claim page each term of "At a glance" SHALL be drawn as one line holding its label and its value, on one baseline at the top of the row at every width, with the value's other names under it. The line SHALL open, on a press and from the keyboard, to the source's definition whole and in quotation marks, the term's match, where the claim's term is filed when it differs, and the card's credit and reasons. With no script, and on paper, every row SHALL be open. A link to a term from elsewhere on the page SHALL open it. The claim's own facts SHALL be rows of the same list.

#### Scenario: Reading the list
- **WHEN** a reader opens a claim with four terms at 1400 pixels wide
- **THEN** each term is one line with its label and its value, and the three facts follow as rows of the same list

#### Scenario: From the band
- **WHEN** the reader follows "Kind of molecule" from the band
- **THEN** that term's row is open and in view

### Requirement: A term's score is said where its row opens, unless it is below the high band
A term's score in the high band, and how a term was found where it has no percentage, SHALL be shown where the row opens, as the page's score chip at the head of that term's "Why it matched", ahead of the reasons. "Why it matched" SHALL be closed when the row opens and SHALL open at one press; on paper it SHALL be open. A term's score below the high band SHALL be shown on the closed row, in sight with nothing to press. This is an exception, for term matches in "At a glance" only, to the requirement that every score is in sight.

#### Scenario: A strong match
- **WHEN** a condition is matched to a vocabulary term at 0.98
- **THEN** the closed row shows the label and the value only, the opened row shows "Why it matched" closed, and pressing it shows a chip reading "High, 98%" followed by the reasons

#### Scenario: A weaker match
- **WHEN** a condition is matched to a vocabulary term at 0.62
- **THEN** the closed row shows a chip reading "Medium, 62%" beside the value

### Requirement: The source's words end in a pill that opens the source
Where a row opens to a source's words, the words SHALL be shown without a label, and SHALL be followed by a pill that names the source and is a link to the term's page at that source, or to the source itself where the words are another source's. The link SHALL open in a new tab and SHALL say so to a screen reader, with whose words they are. A term with no words of its source's SHALL show the pill beside the label "Source".

#### Scenario: A definition from a vocabulary
- **WHEN** a reader opens "Claimed for"
- **THEN** the definition is followed by a pill reading "MeSH", and pressing it opens the term's page at the vocabulary in a new tab

### Requirement: An opened row is marked and its parts are labelled
The head of an opened row (its label, its value and what stands under the value) SHALL be tinted across the list's width and SHALL be the row's press, whole; what the row opens to SHALL lie under the head on the page's ground and SHALL NOT close the row when pressed. After the source's words, each part SHALL carry its own label: where the term is filed, naming the source; the term as its source names it with its credit; and, last and closed until pressed, why it matched. What the row's value already says SHALL NOT be repeated in the opened row. The source's words SHALL be the most prominent part and the credit the least. A card's note that its record is not medical advice SHALL stay in sight, outside "Why it matched".

#### Scenario: Reading an opened term
- **WHEN** a reader opens "Claimed for"
- **THEN** the row's head is tinted, the definition is the largest text under it, and "Filed in MeSH as", the term with its credit and a closed "Why it matched" follow, each smaller and each named

#### Scenario: Pressing inside an opened row
- **WHEN** a reader presses the definition, or selects its text, in an opened row
- **THEN** the row stays open

### Requirement: Every fold's mark stands at the end of its line
A section's heading SHALL start at the section's left edge, where its rows start. The mark that folds a section and the mark that opens a fact row SHALL be the same round chevron, at the right edge of the line they belong to, and SHALL point up while open and down while shut. The rule a section's body starts under SHALL be softer than the ink of the text.

#### Scenario: Reading down a section
- **WHEN** a reader looks at "At a glance" on a wide screen
- **THEN** the title and the rows' labels start at one left edge, and the section's mark and the rows' marks stand in one column at the right

### Requirement: The claim's facts are rows of one fact sheet
The terms of "At a glance" and the claim's own facts SHALL be rows of one list, built from one row component, with every value in one size and weight.

#### Scenario: A term and a fact
- **WHEN** a reader compares "Treatment" with "First reported"
- **THEN** both rows have the same label column, value size and rule

### Requirement: The home page's first screen leads with the lookup
The home page's opening band SHALL hold the title, one sentence saying what the site does, and the lookup box as the largest control on the page. Under the box, on a screen wider than a phone, it SHALL offer the three listed topics with the most claims as words to try, each looking its words up when pressed, and SHALL say how many claims are tracked in how many topics, as numbers only. The words to try SHALL be shown only where scripting can run them. The box SHALL keep its label for a screen reader wherever the label is not drawn.

#### Scenario: A word to try
- **WHEN** a reader presses a topic offered under the box
- **THEN** the box holds that topic's name and the page answers as if the reader had typed it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** no words to try are shown

#### Scenario: A phone
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** neither the words to try nor the count line is drawn, and the box's label is

### Requirement: The home page says beside its list how it is made
On a wide screen the home page SHALL show, beside the day-by-day list, how a status is set in at most three steps with a link to the method page, a link to the feed of status changes, and that the site gives no medical advice and that a registered trial is not a treatment option. It SHALL add no verdict wording and no count.

#### Scenario: A wide screen
- **WHEN** the home page is opened on a screen at least 72rem wide
- **THEN** the three parts stand at the right of the list, each with one link

#### Scenario: A narrower screen
- **WHEN** the home page is opened on a narrower screen
- **THEN** the parts are not drawn, and the page's footer still carries the notices

### Requirement: The home page draws one claim, reported and on record
Under its box the home page SHALL draw one published claim, chosen by the site's rule for its example and never by hand: the earliest report's title as a quotation with its outlet and its day, the number of whole years between that day and the day the registries were last checked, and the claim's status as the site labels it, with its place on the path and the day of its latest record. The card SHALL lead to the claim's page. The years SHALL NOT be stated for a report under a year old. The card SHALL NOT be drawn below 40rem. The home page's title and section headings SHALL be set in the heading face.

#### Scenario: A report of five years ago
- **WHEN** the example claim was first reported on 31 March 2021 and the registries were last checked on 17 November 2026
- **THEN** the card says "5 years on" between the outlet's title and the claim's status

#### Scenario: On a phone
- **WHEN** the home page is read at 375 pixels wide
- **THEN** the card is not drawn and a row of the list starts on the first screen

### Requirement: The home page's card is drawn once, in the order it is read
When the home page opens, the card's arrow SHALL be drawn from the report to the record and the marker SHALL then land on the claim's place with one ring, once. Every word of the card SHALL be readable from the first paint. With reduced motion asked for, with no script and on paper the card SHALL be shown in its finished state and nothing SHALL move.

#### Scenario: Reduced motion
- **WHEN** a reader who has asked for reduced motion opens the home page
- **THEN** the arrow and the marker are drawn whole and nothing moves

### Requirement: The day-by-day list is narrowed from one control
Where scripts run, the head of the home page's day-by-day list SHALL carry one control, on the line of the list's name, that opens, by a press and not by pointing, a panel holding every choice that narrows the list: the kind of row, the span of time, the status now and, where more than one topic is listed, the topic. Each choice SHALL be a field with its name written before it. While no field narrows the list the control SHALL say "Filter"; while one or more do, it SHALL say those picks in the fields' own words and be marked as narrowing, and the panel SHALL offer to clear them all at once. Each pick SHALL narrow the lists and be kept in the page's address exactly as before. Without scripts neither the control nor the fields SHALL be shown, and the whole list SHALL be.

#### Scenario: Nothing picked
- **WHEN** a reader opens the home page with no pick in its address
- **THEN** the control says "Filter" and the list shows the past week

#### Scenario: Two picks
- **WHEN** a reader picks news reports and phase 3 in the panel
- **THEN** the control says "News reports · Phase 3 trial", the list shows only reports of claims now in phase 3, and the address keeps both picks

#### Scenario: Clearing
- **WHEN** a reader presses "Clear filters"
- **THEN** every field returns to its first choice, the control says "Filter", and the address keeps no pick

#### Scenario: On a phone
- **WHEN** the home page is read at 375 pixels wide
- **THEN** the list's name and the control share one line, the control is 44 pixels tall, and the open panel stands inside the screen

### Requirement: A row's headline is set in the heading face and is read first
In the home page's day-by-day list, the list's name and each row's reported headline SHALL be set in the site's heading face, as SHALL a report's title in a search's answer, which stands in the list's place, and a row's headline SHALL be the largest text in the list after its name. A day's heading SHALL be drawn as a label smaller and quieter than a headline. A day's heading, a row's labels and its status SHALL stay in the text face.

#### Scenario: A report row
- **WHEN** a report row is drawn
- **THEN** its headline is in the heading face and the outlet, the claim and the status are in the text face

#### Scenario: A day's heading
- **WHEN** a day with two reports is drawn
- **THEN** the day and "2 reports" are in grey at the size of a label, and each report's headline is larger than both

### Requirement: An outlet's title keeps its marks, drawn softer and hung
Wherever the home page's day-by-day list, its card or a search's answer quotes an outlet's title on a line of its own, the title SHALL stand between quotation marks that are part of the text. The marks SHALL be drawn softer than the words, and the opening mark SHALL hang outside the column so that the title's first letter stands on the same edge as the lines above and below it.

#### Scenario: Aligned with its row
- **WHEN** a report row is drawn with the outlet above its headline and the claim below
- **THEN** the headline's first letter, the outlet and the claim start on the same edge, and the opening mark stands to the left of it

#### Scenario: Copied
- **WHEN** a reader copies a headline from the list
- **THEN** what is copied begins and ends with its quotation marks

### Requirement: The list's head is one line
The head of the home page's day-by-day list SHALL be one line on a wide screen: the list's name, a mark that opens the sentence saying what each row's right column is, the day the registries were last checked, and the control that narrows the list. The sentence SHALL be in the page as built and reachable without scripts. On a phone the day checked SHALL take the line under the others.

#### Scenario: What the column says
- **WHEN** a reader presses or points at the mark beside "Latest"
- **THEN** a panel says "With each report and record: where its claim stands on record now. Press it for why."

### Requirement: A registry row leads with what was recorded
In the home page's day-by-day list, a registry record's row SHALL lead with the record: a mark of what happened, its kind in words and the record's identifier leading to the record at its source, then what was recorded, in the record's own words, as the row's title leading to the claim page, then the claim. Where the registry gives a trial's phase, the title SHALL name it. The claim's newest news report SHALL follow these, set smaller than the row's title and joined to the row as what the record belongs to: named "Newest report", with its outlet and date, how long ago the claim was first reported when that is a year or more, and its title quoted. A registry row SHALL NOT set a news report's title as its own title.

#### Scenario: A phase 3 trial registered last week
- **WHEN** a phase 3 trial for a published claim was registered on 2 November 2026
- **THEN** the row's title reads "Phase 3 trial registered", and the claim's newest report is quoted under it, smaller, after "Newest report"

#### Scenario: A trial with no phase given
- **WHEN** the registry gives no phase for a trial whose results were posted
- **THEN** the row's title reads "Trial results posted"

#### Scenario: A report and a record of one claim on one day
- **WHEN** a claim was reported and a trial for it was registered on the same day
- **THEN** the report's row has the outlet's title as its title, and the record's row has what was recorded as its title

#### Scenario: Read aloud
- **WHEN** a screen reader lists the page's links
- **THEN** a registry row's title is read with its treatment, as what was recorded, a colon and the treatment's name

### Requirement: A row's status stands in a named panel
In the home page's day-by-day list, a report's and a registry record's row SHALL show the claim's status in a panel at the row's right: the status, its place on the path, a no-signal note where there is one, and the counts. The panel SHALL be named "Status now", so that it is not read as what the report or the record beside it says: once for each day, at the right of the day's heading, where the panels stand in a column; on the panel's own first line where the panel stands under the claim. The panel SHALL be no taller than what it holds while its detail is closed. A row for a record dated on a day the claim's status changed SHALL say "Changed" and the status before in place of "Status now". The panel SHALL be the control that opens the row's detail, and while the detail is open the two SHALL be drawn as one shape. The phase in a registry row's title is the trial's; the status in the panel is the claim's.

#### Scenario: An early trial of a claim that is further on
- **WHEN** a phase 2 trial is registered for a claim that stands at phase 3
- **THEN** the row's title reads "Phase 2 trial registered" and its panel, under "Status now", reads "Phase 3 trial"

#### Scenario: A day of three rows on a wide screen
- **WHEN** a day lists two reports and a registry record
- **THEN** the day's heading says "Status now" once, over the three panels, and no panel says it

#### Scenario: On a phone
- **WHEN** the list is read at 375 pixels wide
- **THEN** each panel says "Status now" on its first line and no heading does

#### Scenario: A record that changed the status
- **WHEN** a record dated today moved a claim from phase 2 to phase 3
- **THEN** the panel says "Changed" and the status before, and does not say "Status now"

#### Scenario: Opened
- **WHEN** a reader presses a row's panel
- **THEN** the detail opens under the row with nothing between it and the panel, on the same ground

### Requirement: A record's mark is coloured by which way the record moved
A registry row SHALL carry one mark for what its record did, hidden from a screen reader. The mark's colour SHALL say which way the record moved and nothing else: one colour where something began or a regulator approved (a trial registered, a trial started, a regulatory approval), another where something was halted, taken back or refused (a trial suspended, terminated or withdrawn, a regulatory refusal, a retraction), and the site's blue for every other record. A completed trial and posted results SHALL keep the blue. No mark SHALL be a tick or a cross, and colour SHALL never be the only thing that tells two marks apart: each has its own drawing and the row says what happened in words. No status and no place on the path SHALL take these colours.

#### Scenario: A trial registered
- **WHEN** a trial is recorded as registered
- **THEN** its mark is a plus in the colour of a record that moved forward

#### Scenario: A terminated trial
- **WHEN** a trial is recorded as terminated
- **THEN** its mark is a square in the colour of a record that stopped, and the row says "terminated" in words

#### Scenario: A completed trial
- **WHEN** a trial is recorded as completed, whatever its results
- **THEN** its mark keeps the blue

#### Scenario: Results posted
- **WHEN** a trial's results are posted
- **THEN** its mark keeps the blue

### Requirement: A row does not repeat its day
Under a heading that names one day, a report's or a registry record's row of the day-by-day list SHALL NOT draw its date again. A promised date's row SHALL keep the date of the report that made the promise, which is not the day it is listed under. Under a heading that names a week or a year, each row SHALL draw its date. Every row's date SHALL remain in the page as built.

#### Scenario: Under a day
- **WHEN** two reports are listed under "Sunday 15 November"
- **THEN** neither row draws "15 Nov 2026"

#### Scenario: Under a week
- **WHEN** a report dated 21 October is listed under "Week of 19 October"
- **THEN** its row draws "21 Oct 2026"

### Requirement: A record matched to several claims is drawn once
Where one registry record is listed in a day for more than one claim, the day-by-day list SHALL draw the record in full for the first of those claims and SHALL list each further claim straight after it, under one label that says they are the same record for other claims, as one line that names the treatment, leading to its claim page, and what it is for, with that claim's own status beside it. When a reader's choice leaves the first of those rows out, the first one left SHALL be drawn in full. The day's counts SHALL still count every row.

#### Scenario: One trial, five claims
- **WHEN** a trial registered on 12 November is matched to five published claims
- **THEN** the day shows the record once, with its identifier, then "The same record, for other claims" once, and four lines under it, each a treatment, what it is for and its status

#### Scenario: The leading claim is filtered out
- **WHEN** a reader narrows the list to a topic the first of those five claims is not filed under
- **THEN** the first claim left is drawn as the record, in full, and the rest follow it

### Requirement: The list reads as a feed on a phone
At 375 pixels wide, a row's status panel SHALL be one line of at least 44 pixels: the status, its place on the path and the control's mark; a change of status and a no-signal note SHALL keep a line of their own. The counts SHALL be said in the opened detail. The panel SHALL be named "Status now" to a screen reader. A day's heading SHALL stay in view while its rows are read. A link in an opened detail SHALL be at least 44 pixels to press. The first row and its status panel SHALL both be on the first screen of a phone 812 pixels tall.

#### Scenario: First screen
- **WHEN** the home page opens on a phone 375 by 812
- **THEN** the title, the box with its button beside it, three things to try, the list's head, and the first row with its status panel are all in view

#### Scenario: A long day
- **WHEN** a reader scrolls through a day of eleven rows
- **THEN** that day's heading stays at the top of the screen until the next day's replaces it

### Requirement: A long day is cut on a narrow list
Where the day-by-day list is narrow and scripts run, a day SHALL show its rows up to its fifth leading row, with the rows that follow that one, and SHALL offer the rest behind one control that says how many rows it brings back. A row that follows its record SHALL NOT be parted from it. A day SHALL be cut only when that leaves out at least two leading rows. Once a reader has asked for a day's rest, that day SHALL stay whole. A wide list, paper, and a page without scripts SHALL show every row, and a day's counts SHALL count every row.

#### Scenario: Seven leading rows on a phone
- **WHEN** a day lists three reports and four records, one of them matched to five claims
- **THEN** the day shows the three reports, the record with its four following lines and one more record, and "Show 2 more"

#### Scenario: Asked for
- **WHEN** the reader presses "Show 2 more"
- **THEN** every row of that day is shown, the control is gone, and narrowing the list afterwards does not cut that day again

#### Scenario: Six leading rows
- **WHEN** a day lists six leading rows
- **THEN** all six are shown and there is no control

### Requirement: Background cards on the claim page
A claim page SHALL show the claim's background cards in an "At a glance" section, placed before the record in brief: a list of rows ruled in ink above and below, each a label and a one-line value, for the treatment (its name and other names), the kind of treatment (a kind card's term, shown only when there is no drug card), the kind of molecule (a drug card's kind of molecule and what its record says the drug acts on, with the kind card, when there is one, inside the same row's disclosure), a target (labelled "Gene named", or "Acts on" when the drug's record names it) and the condition the claim is for (its words), followed by the claim's own facts (first reported, evidence when first reported, records of studies) side by side in one line. A row whose card is missing SHALL be left out, except the treatment and the condition, which come from the claim. A row whose card has a definition SHALL show it in sight under the value, unchanged and in quotation marks; a definition longer than 240 characters MAY be cut to three lines there and SHALL then be given whole in the card. A row with a card SHALL have one disclosure, closed until asked for, whose summary is one grey line: first "Why this term", or "Full definition and why this term" when the definition is cut, named for the row's term for a screen reader; then whose words the definition is ("In MeSH’s words") or, with no definition, which source the row's facts are from; for the treatment, the drug and the condition, the claim's words beside the source's term with an arrow when they differ other than in case ("Lung cancer → Lung Neoplasms"); and the score of each card in the row in sight, named for what was matched ("Term match: high, 81%"; on a kind of molecule row "Drug record: by exact name", then "Kind term: high, 94%" for a kind card in the same row), never as a bare percentage beside the treatment. One line under the section's heading SHALL say what a term match is, where a reader first meets one. It opens to the card: its label, its definition marked as the source's words unless its row shows it (a cut definition is given whole in the row once opened), the source's name, a link to the source's record, the date the record was read, and the score's reasons under "Why it matched", any drug named in them as the claim writes it. The section's note on what the cards are SHALL be at most three sentences with a link to the method page, and SHALL be shown only when the claim has a card. Decided by the operator on 2026-11-15, from the knowledge-card sketches (`.impeccable/mocks/knowledge-card/`) and, the same day, after a critique of the first build (`.impeccable/critique/`), which found the open cards made the section three screens long on a phone. Changed by the operator on 2026-11-16, from the At a glance sketches (`.impeccable/mocks/at-a-glance/`, variant 4 with the claim's words beside the source's term from variant 2): a definition is in sight in its row, and the dates leave the term rows for a line of their own.

#### Scenario: Claim with a condition card only
- **WHEN** a reader opens a claim that has a card for its condition and none for its intervention
- **THEN** "At a glance" shows the treatment's name and the condition's words, the condition row shows the condition's definition in quotation marks and has one closed disclosure whose summary names the source and reads "Term match: high, 100%", and there is no kind, molecule or target row

#### Scenario: Claim with no card
- **WHEN** a claim has no card
- **THEN** "At a glance" shows the treatment, the condition and the claim's facts, with no disclosure and no note on cards

### Requirement: The band names what the treatment is
When a background card gives the treatment's kind or a target, the record band SHALL name only those in one line directly under the headline, before the status on a phone: the kind of molecule from a drug card, or else the kind of treatment from a kind card, and a target, each under the same label as its row in "At a glance" and each a link down to that row with a visible cue that it is one. A row reached from the band SHALL take focus and be marked as a record reached by a link is. The row SHALL NOT repeat the treatment's name or the condition, which the headline gives, and SHALL show no score, definition or reason beside the status: the score of each value is in sight on its row. Decided by the operator on 2026-11-15 after the critique, replacing a first build that showed scores in the band.

#### Scenario: Device with a kind card
- **WHEN** a reader opens a device claim whose kind card scores 0.81 and which has a condition card
- **THEN** the line under the headline reads "Kind of treatment" with the kind's term and no percentage, and pressing it moves focus to the kind row of "At a glance", which is marked and whose summary reads "Term match: high, 81%"

#### Scenario: Drug with a kind card
- **WHEN** a claim has a drug card and a kind card
- **THEN** "At a glance" has a kind of molecule row and no kind of treatment row, and the kind card is inside the kind of molecule row's disclosure

#### Scenario: Claim with only a condition card
- **WHEN** a claim's only card is for its condition
- **THEN** the band has no such line

### Requirement: A card shows how sure its link is
Each card made from a scored link SHALL show the score as a word and a percentage, with its reasons in the site's words available on request, and SHALL say when its term is broader than the claim's condition or intervention, when it is the kind of intervention and not the intervention itself, and when a target is one the report names and not one a drug's record gives.

#### Scenario: Kind card
- **WHEN** an intervention card is made from a kind link with a score of 0.9
- **THEN** the card says its term is the kind of treatment this is, not the treatment itself, and shows "High match · 90%"

#### Scenario: Registry type as a reason
- **WHEN** a reader asks why a kind card's term was chosen and the registry lists the intervention as a device in three of the claim's trials
- **THEN** the card says so in the site's words

#### Scenario: Target the report names
- **WHEN** a target card is made from a gene named in the intervention
- **THEN** the card says the gene is named in the intervention's name, shows the score, and does not say the intervention works through it

#### Scenario: Broader term
- **WHEN** a condition card is made from a broader term with a score of 0.9
- **THEN** the card says the term is broader than the claim's condition and shows "High match · 90%"

#### Scenario: Reason shown on request
- **WHEN** a reader asks why a card's term was chosen
- **THEN** the card says the registry files five of the claim's six trials under it

### Requirement: A card's words are its source's
A definition SHALL be shown as its source wrote it, marked as the source's words, and SHALL NOT be reworded by the site. The site SHALL add no explanation of a condition or a treatment of its own. The site SHALL word each card kind, reason, registry type and molecule kind code itself and SHALL fail the build on a code it has no wording for.

#### Scenario: Definition in the vocabulary's style
- **WHEN** a definition uses the vocabulary's own capitalised cross-references
- **THEN** the card shows it unchanged and names the vocabulary as its source

#### Scenario: Code without site wording
- **WHEN** the export carries a molecule kind the site has no wording for
- **THEN** the site build fails and names the code

### Requirement: Background is not advice and not evidence
"At a glance" SHALL say that the cards describe terms, are not about the claim's evidence and are not medical advice. A card SHALL NOT state that the intervention treats the condition, and the site SHALL NOT place a card, or any definition or reason, inside the status panel.

#### Scenario: Card for a drug class with approved uses
- **WHEN** a card's definition mentions what a class of drugs is used for
- **THEN** the definition is shown as the source's words in "At a glance", with the section's note, and nothing of it is in the status panel

### Requirement: Card sources are credited
Every page that shows a card SHALL credit the card's source in the terms the source asks for, including the version or date of a vocabulary. The footer's list of data sources SHALL include each source a published card comes from.

#### Scenario: Vocabulary that asks for its version to be stated
- **WHEN** a page shows a card from a vocabulary whose terms ask for the version used
- **THEN** the card names the vocabulary and its version or date

### Requirement: A topic page opens for a reader who arrives from a shared link
Under its title a topic page SHALL say in one line what the page is and link the method page. Directly under the sentence that summarises where its claims stand, it SHALL offer to share the page, link the feed of the topic's status changes, and, where copying works, offer to copy that sentence with the month the registries were checked and the page's address. Where a suggestion address is configured, the page SHALL end with the link to suggest a headline.

#### Scenario: Arriving from a forum
- **WHEN** a reader opens a topic page with seven claims at 375 pixels wide
- **THEN** the line saying what the page is, the summary, Share, the feed link and "Copy sentence" all come before the first claim

#### Scenario: Copying the sentence
- **WHEN** the reader presses "Copy sentence" on a topic checked in November 2026
- **THEN** the copied text is the summary sentence, "Checked November 2026." and the topic page's address

#### Scenario: Copying is not possible
- **WHEN** the browser cannot copy
- **THEN** no copy control is shown and the sentence stays readable on the page

### Requirement: The home page holds what a reader sees on arrival
The home page as built SHALL hold the first ten rows of each of its tabbed lists and the rows under its day-by-day list's day headings, and SHALL NOT hold the other rows of those lists. The number each tab shows, each pager's line and the line about the reader's last visit SHALL state the whole list's numbers all the same.

#### Scenario: Opening the home page
- **WHEN** published claims have 1,597 source articles between them and the home page is opened
- **THEN** the page holds ten rows of the Headlines list, its tab says 1,597, its pager says "1–10 of 1597 headlines", and no other row of the list has been fetched

#### Scenario: A list that fits one page
- **WHEN** the No signal list has four rows
- **THEN** all four are in the page

### Requirement: The rest of a list is fetched when a reader asks for it
The rest of each home page list SHALL be published as a file of rows, drawn as the rows in the page are drawn. The page SHALL fetch a list's file once, the first time a reader asks for something that needs rows that are not in the page. Once fetched, the rows SHALL be narrowed, counted and paged as the rows in the page are.

#### Scenario: Stepping to the next page
- **WHEN** a reader presses "Next" under the Headlines list for the first time
- **THEN** the rest of its rows are fetched, and the eleventh to the twentieth headline are shown

#### Scenario: Narrowing by status
- **WHEN** a reader picks the status "Approved" on the home page
- **THEN** the rest of each tabbed list is fetched, and each tab shows how many of its rows, among all of them, are of claims at that status

#### Scenario: A count pressed on the line about the last visit
- **WHEN** a reader presses "82 of 1597 news reports" on the line about their last visit
- **THEN** the rest of the Headlines list is fetched and the list shows the 82 reports dated since

#### Scenario: An address naming a later page
- **WHEN** the home page is opened at an address that names the third page of the Headlines list
- **THEN** the rest of the Headlines list is fetched and the twenty-first to the thirtieth headline are shown

#### Scenario: A list that is whole in the page
- **WHEN** the No signal list has four rows
- **THEN** no file of rows is published for it

#### Scenario: Retry completes the original action

- **WHEN** an initial request fails after Next or after opening an older date heading and the reader presses Try again
- **THEN** a successful retry advances the requested page or opens the requested heading once, without another press

#### Scenario: A deployment changes the home list order

- **WHEN** a reader holds the first ten rows while a new export inserts a row ahead of them
- **THEN** paging either continues the original export or restarts coherently on the new export. The displayed sequence has no omissions or duplicates from mixing versions

### Requirement: A file of rows is not a page
A file of rows SHALL hold rows only, and search engines SHALL be asked not to index it.

#### Scenario: A file of rows asked for by its address
- **WHEN** the file of the Headlines list's rows is requested
- **THEN** it is served as text with a header that asks search engines not to index it

### Requirement: A list says when its rows are not all in the page
While a list's rows are being fetched the list SHALL say so in words and SHALL be marked busy. If they do not arrive, the list SHALL say that the rest of it did not load and SHALL offer a control to ask again. A list whose rows are not all in the page SHALL NOT say that nothing matches a choice, that a span has been read to its end, or how many earlier rows remain.

#### Scenario: Rows on their way
- **WHEN** a reader presses "Next" under a list whose rows are not yet fetched
- **THEN** the list says "Loading the rest of this list." until the rows arrive

#### Scenario: Rows that do not arrive
- **WHEN** a list's file of rows cannot be fetched
- **THEN** the list says "The rest of this list did not load." with a control to try again, keeps showing its first rows, and does not say that nothing matches

#### Scenario: Printing after selecting a different tab

- **WHEN** one of the five home lists is active and later rows have never been fetched
- **THEN** print includes first rows and the applicable partial-list notice for each of the five lists

### Requirement: A status off the path is drawn as off it
Where a row draws a status's place on the path and the status is not on it (no trial record found, failed, terminated, retracted), the row SHALL draw a square, and no path, with the status in words beside it, and its text alternative SHALL say the status is not a place on the path. No status SHALL have a colour of its own.

#### Scenario: Trials ended early
- **WHEN** a claim stands at "Trials ended early"
- **THEN** its row shows those words and a square, with no path drawn

### Requirement: Search results set the status on the right
In search results, each match SHALL show its headline, its intervention and indication and what the words were found in on the left, and its status, place on the path and first-report date in a column on the right on a wide screen, after the headline in the order a screen reader reads them.

#### Scenario: A search on a wide screen
- **WHEN** a reader searches "cancer" on a laptop
- **THEN** each match's headline starts at the left edge of the list and its status stands in a column on the right

### Requirement: A link in a row that opens can be pressed
In a fact row that opens, a link under the row's value SHALL be pressed for itself and SHALL NOT be covered by the row's own press. On a phone it, a moment of the record, the line that opens the rest of a list and a marked word of the record in brief SHALL each be at least as tall as a fingertip, or lie in running text.

#### Scenario: "See the posted results"
- **WHEN** a reader presses "See the posted results" under an answer of the record in brief
- **THEN** the page goes to the trials on record and the row does not open

### Requirement: A heading's note says only what is true of what is in sight
The note beside the timetable's heading SHALL give the counts of promises and records and SHALL NOT name an order: the moments under it run oldest first and the full record newest first.

#### Scenario: A claim with 163 records and one promise
- **WHEN** a reader reads the timetable's heading
- **THEN** the note reads "1 promise · 163 records"

### Requirement: A Phase 3 status with no approval says approvals are not read
When a claim's status is Phase 3 trial and no approval is among its records, the status card SHALL say, after what the status means, that no approval is listed and that the site does not read regulators' records, so one can exist and not be listed. Whether the sentence is shown SHALL be decided by the status code and the claim's records alone, never by the wording of a news report. The sentence SHALL hold no verdict and no link.

#### Scenario: Reported as approved, status Phase 3 trial
- **WHEN** a claim whose news reports say it was approved has a Phase 3 trial status and no approval record
- **THEN** the status card says no approval is listed here and that the site does not read regulators' records

#### Scenario: An earlier place on the path
- **WHEN** a claim's status is Phase 2 trial
- **THEN** the status card says nothing about approvals

### Requirement: The status panel names the latest records and can be closed
The panel that opens from the status SHALL name at most the three latest records the status rests on, each leading to its record on the page. When the status rests on more, the panel SHALL say how many and lead to the timetable, which marks every one. A panel of the status card SHALL end with a control that closes it, in reach without scrolling the panel.

#### Scenario: A status that rests on 44 records
- **WHEN** a reader opens the panel of a status that rests on 44 records
- **THEN** it names the three latest, says they are the 3 latest of 44, and leads to the timetable

#### Scenario: A status that rests on two records
- **WHEN** a reader opens the panel of a status that rests on two records
- **THEN** it names both and says nothing of a count

#### Scenario: Closing the panel on a phone
- **WHEN** a reader on a phone has opened the panel
- **THEN** a "Close" control is in sight at its foot and closes it

#### Scenario: One press closes a hovered status panel

- **WHEN** a reader with a hover-capable pointer opens the status panel and presses Close once
- **THEN** the panel closes on that press. The opening control can still reopen it

### Requirement: Claim and topic pages open with a band
A claim page and a topic page SHALL open, directly under the masthead, with a full-width band in the site's navy. On a claim page the band SHALL hold the breadcrumb, the title, the reports followed and the status panel. On a topic page it SHALL hold the breadcrumb, the title, the summary sentence and the number of claims at each status. On a screen wide enough for two columns the status panel SHALL start level with the title.

#### Scenario: Claim page on a wide screen
- **WHEN** a reader opens a claim page at 1280 pixels wide
- **THEN** the status label is in the band, beside the title, and starts within the first 200 pixels of the page

#### Scenario: Topic with one claim at each of two statuses
- **WHEN** a reader opens a topic whose two claims stand at Preclinical only and Phase 3 trial
- **THEN** the band shows the topic's name and a count of one at each of those statuses, each named in words

### Requirement: The band stays short on a phone
Below the site's phone breakpoint the band of a claim page SHALL hold only the breadcrumb, the title, the link to the method and the status panel. The reports followed SHALL open the content below the band, and the follow and share controls SHALL close the band, under the status panel. When a claim follows more than one report, the first SHALL be shown there and the rest SHALL be reached by one link to the timetable.

#### Scenario: Claim page on a phone
- **WHEN** a claim page is opened at 375 by 812 pixels
- **THEN** the status label starts within the first screen and the content below the band starts within 1,000 pixels of the top

#### Scenario: Claim that follows three reports
- **WHEN** a claim with three source articles is opened at 375 pixels wide
- **THEN** one report is shown under the band with a link reading that two more are on the timetable

### Requirement: A claim page lists its sections
A claim page SHALL list its sections by name, each with the count it holds where it has one, and SHALL mark the section in view. On a wide screen the list SHALL stay in view beside the content. On a narrow screen it SHALL be one row that stays at the top, SHALL keep the marked section in view, and SHALL show at either end that more lies beyond it. A section the page does not have SHALL NOT be listed.

#### Scenario: Reader scrolls to the trials
- **WHEN** a reader scrolls a claim page until the trials section is at the top
- **THEN** the list marks "Trials on record" and no other section

#### Scenario: Claim with no papers
- **WHEN** a claim has no matched paper
- **THEN** the list has no entry for papers

#### Scenario: Narrow screen, section far along the row
- **WHEN** a reader on a phone scrolls to the last section
- **THEN** the row has moved so that the last section's name is in view and marked

### Requirement: Sections of a claim page fold
Each section of a claim page SHALL fold and unfold from its heading. The heading SHALL remain a heading, and the control SHALL say whether the section is open. Papers, organisations and background SHALL start folded. Below the phone breakpoint only the record in brief and the timetable SHALL start open. A link to a folded section, or to something inside one, SHALL open it. With scripting off every section SHALL be open.

#### Scenario: Wide screen, first view
- **WHEN** a claim page with papers and organisations is opened at 1280 pixels wide
- **THEN** the papers and organisations sections are folded, with their counts on the heading line, and the timetable and trials are open

#### Scenario: Phone, first view
- **WHEN** the same page is opened at 375 pixels wide
- **THEN** only the record in brief and the timetable are open

#### Scenario: Link into a folded section
- **WHEN** a reader presses a trial identifier in the timetable while the trials section is folded
- **THEN** the trials section opens and the reader arrives at it

#### Scenario: Scripting off
- **WHEN** a claim page is opened with scripting off
- **THEN** every section is open

### Requirement: The timetable reads newest first
The claim page's timetable SHALL list its years newest first and, within a year, its entries newest first. A year for which a promise was made SHALL show what was promised for it beside what was recorded in it, including a year still to come. A run of years with neither a promise nor a record SHALL be shown as one gap that names the years. Each entry SHALL state its kind in words as well as by its mark.

#### Scenario: Records from 2021 to 2026 with none in 2024 and 2025
- **WHEN** a claim has records in 2021, 2022, 2023 and 2026
- **THEN** the timetable starts with 2026, ends with 2021, and shows one gap reading "2024 to 2025" with no record

#### Scenario: Promise for a year still to come
- **WHEN** a claim reported in 2026 carries a promise for 2029 and nothing is recorded for 2029
- **THEN** the timetable starts with 2029, showing the promise beside "Not yet reached"

### Requirement: The timetable can be narrowed to one kind of entry
With scripting on, a timetable holding more than one kind of entry SHALL let a reader show promises, registry records or news reports alone, and all of them again. A year left with no entry SHALL be hidden, and a year's stated count SHALL be the entries left. The choice SHALL be announced to a screen reader. With scripting off, and in print, every entry SHALL be shown.

#### Scenario: Registry records only
- **WHEN** a reader picks registry records on a claim whose 2026 holds three news reports and one registry record
- **THEN** 2026 shows one entry and states one record, and promises with and without a date are hidden

#### Scenario: One kind only
- **WHEN** a claim's timetable holds only registry records
- **THEN** no control to narrow it is shown

### Requirement: Promises and records are counted apart
Wherever a claim page states how many entries its timetable holds, it SHALL give the number of promises and the number of records as two numbers and SHALL NOT add them into one. Every place that states them SHALL give the same two numbers. A promise with no date SHALL count as a promise.

#### Scenario: Four promises and seventeen records
- **WHEN** a claim has two dated promises, two promises with no date and seventeen records
- **THEN** the section list, the section heading and the controls that narrow the timetable all give 4 promises and 17 records, and none gives 21

### Requirement: Trials read across as a table
The trials section SHALL show its trials as rows of a table with columns for how many people, what it was compared with, its main measure, its state and the trial's identifier (change `trials-by-phase`: one table per phase). A row SHALL open to show the rest of what the export carries for that trial, its match and its record. Below the phone breakpoint each value SHALL carry its column's name. The control that opens a row SHALL say whether it is open.

#### Scenario: Three finished trials
- **WHEN** a reader opens a claim with three finished trials on a wide screen
- **THEN** the three are rows under one row of column names, and opening the first shows its registry title, main measure, match and record link

#### Scenario: The same table on a phone
- **WHEN** the table is read at 375 pixels wide
- **THEN** each trial's state reads with the word "State" beside it and the page does not scroll sideways

### Requirement: A match score reads as a note about the match
On a claim page the score of a paper's, a background term's or a trial's match SHALL be shown in the entry's notes, worded as a match to the claim with its band and percentage. It SHALL NOT be set apart beside the entry's title or given more weight than the notes around it.

#### Scenario: Paper matched at 100%
- **WHEN** a claim page lists a paper whose match is scored 1.0
- **THEN** the paper's notes end "Match to this claim: high, 100%" and nothing but the title stands on the title's line

### Requirement: A topic's claims can be narrowed by a word
Where a topic's claims can be narrowed by status, they SHALL also be narrowed by a typed word, matched against each claim's name and headline, and both together. The page SHALL state how many claims are shown out of how many, SHALL announce that count, and SHALL offer one control that removes every narrowing. When nothing matches, the page SHALL say so in place of the table, name what was typed, and offer the same control.

#### Scenario: A word that matches one claim
- **WHEN** a reader types "gene" on a topic of seven claims, one of which names a gene therapy
- **THEN** one row is shown and the page reads "1 of 7 claims"

#### Scenario: Nothing matches
- **WHEN** a reader types a word no claim holds
- **THEN** the table is replaced by "No claim matches", the word typed, and a control that shows all seven again

### Requirement: A topic page lists the other topics
A topic page SHALL list the other topics that have published claims, each with its number of claims, with the topic being read marked. On a wide screen the list SHALL sit beside the claims; on a narrow screen it SHALL be one row above them with the topic being read in view.

#### Scenario: Topic among ten
- **WHEN** a reader opens one of ten topics with published claims
- **THEN** all ten are listed with their counts and the one being read is marked

### Requirement: Actions come before the content for a keyboard
On a claim page the follow, share, check-again and report-an-error controls SHALL be reached by the Tab key before the first control inside the content. Every page SHALL start with a link that skips to its content. A control on a white surface inside the band SHALL show its focus ring in the site's blue.

#### Scenario: Tabbing into a claim page
- **WHEN** a keyboard reader presses Tab from the top of a claim page
- **THEN** the first stop is the skip link, and "Follow" is reached before any link inside the record in brief

#### Scenario: Focus inside the status panel
- **WHEN** a link in the status panel takes keyboard focus
- **THEN** its ring is visible against the panel

### Requirement: A printed claim page is whole
When a claim page is printed, every section SHALL be open, every entry of the timetable SHALL be shown whatever was narrowed on screen, each link to a source outside the site SHALL be followed by its address, and the masthead's links, the breadcrumb, the section list and the action controls SHALL be left out. The basis mark and the marked place on the path SHALL print without background colours. Sections SHALL print open when scripting is off.

#### Scenario: Printing with papers folded and the timetable narrowed
- **WHEN** a reader prints a claim page whose papers section is folded and whose timetable shows news reports only
- **THEN** the print shows the papers and every timetable entry, and the screen returns to how it was

#### Scenario: Source link on paper
- **WHEN** the printed page lists a trial's registry record
- **THEN** the record's address is printed after its link

### Requirement: A summary and a section's note are held short, with the rest on request
On a claim page, where a script runs, the summary SHALL be drawn in at most three lines and the note of "At a glance", trials, registry records, papers and organisations in one line, each followed by a control reading "More" only when text is cut, which shows the whole text and then reads "Less". The whole text SHALL remain in the page for a screen reader and for search, and SHALL be drawn whole with no script and on paper. The notes of "The record in brief" and of the reported statements SHALL NOT be cut.

#### Scenario: A long summary
- **WHEN** a claim's summary runs to five lines at the reader's width
- **THEN** three lines are drawn, "More" follows, and pressing it draws all five and reads "Less"

#### Scenario: A summary that fits
- **WHEN** a claim's summary is one line
- **THEN** no control is drawn

#### Scenario: Paper
- **WHEN** the page is printed
- **THEN** every summary and note is whole and no control is printed

### Requirement: Sections a reader acts from start folded
"Pass it on" and "Check again later" SHALL start folded at every width. The registry records section SHALL start folded when it holds no matched record. A link into a folded section SHALL open it.

#### Scenario: Only possible records
- **WHEN** a claim page lists one possible registry record and no matched one
- **THEN** the section starts folded with "1 possible" beside its heading, and the status card's "1 possible" link opens it

### Requirement: The band's side column holds the topic's drawing
Where the section list stands beside the sheet, the band's side column SHALL hold the topic's drawing, hidden from a screen reader. It SHALL NOT be drawn at narrower widths or on paper.

#### Scenario: Wide screen
- **WHEN** a claim in a topic drawn as a tooth is opened at 1400 pixels wide
- **THEN** the tooth is drawn large at the left of the title, and the topic chip still names the topic

### Requirement: Recent reports on the home page
The home page SHALL list the most recently published source articles of published claims, newest first (ten at a time: see change `browse-lists`). Each entry SHALL show the article's title as the outlet wrote it, marked as a quotation, with the outlet, the publication date and the claim's current status. The title SHALL link to the claim page and the outlet SHALL link to the article.

#### Scenario: Reports from several claims
- **WHEN** three published claims have four source articles between them
- **THEN** the home page lists all four in order of publication date, newest first, each with its claim's status

#### Scenario: Headline wording
- **WHEN** an article's title makes a stronger statement than the claim's status supports
- **THEN** the title is shown in quotation marks with its outlet, next to the status derived from the evidence, and the site adds no wording of its own about the title

#### Scenario: Unpublished claims
- **WHEN** a claim has not been approved in review
- **THEN** none of its articles appears on the home page

### Requirement: A claim page names the reports it follows
A claim page SHALL show, directly under its title and above the status, the claim's source articles, newest first, at most three: each article's title as the outlet wrote it, marked as a quotation and linked to the article, with the outlet and the publication date. When the claim has more than three, the page SHALL link to the dated record of all of them. Where the export carries the claim's matches, the status panel SHALL state how many registry records count toward the status and how many are possible, linked to the list of matched records, and that list SHALL be present, saying that no record matched, when there is none.

#### Scenario: Reader follows a headline from the home page
- **WHEN** a reader opens a claim page from a headline on the home page
- **THEN** the same headline, its outlet and its date are shown under the page's title, before the status

#### Scenario: Claim with matched records
- **WHEN** a claim has three approved matches and two pending candidates
- **THEN** the status panel says three registry records matched and two are possible, and links to the list

#### Scenario: Claim with no matched record
- **WHEN** the export carries an empty list of matches for a claim
- **THEN** the status panel says no registry record matched, and the list of matched records says the registries were searched and none matched

### Requirement: Topics are filed under groups
The export SHALL carry, for each vertical, the group it is configured under, or none. When any listed topic has a group, the topic directory SHALL list topics under their groups' names, groups in alphabetical order and topics in alphabetical order within each, with topics that have no group last; its jump links SHALL lead to the groups, and its filter SHALL match a group's name as well as a topic's. When no listed topic has a group, the directory SHALL list topics under their first letters. The site SHALL NOT assign a topic to a group itself.

#### Scenario: Topics with groups
- **WHEN** a listed topic is configured under a group
- **THEN** the topic directory shows the topic under that group's name and offers a jump link to the group

#### Scenario: No topic has a group
- **WHEN** no listed topic has a group
- **THEN** the topic directory lists topics under their first letters, with a jump link for each letter

### Requirement: Outlets are shown with their own icon
The pipeline SHALL fetch, at most once per outlet domain, the small icon that the outlet's own site serves, and store the image with its address and fetch time. An outlet domain is the host of a source article's URL without a leading `www.`. Before any request to a host the pipeline SHALL read that host's robots.txt and SHALL send nothing further when the rules refuse it or cannot be read. Every request SHALL identify the client with the contact address, and requests SHALL be spaced at least one second apart. Only a raster image (PNG, ICO, GIF, JPEG or WebP, told from the file's own bytes) of at most 100,000 bytes SHALL be stored; a domain with no such image SHALL be recorded as asked and not asked again unless the operator asks for a retry. An ICO file whose every image is fully transparent is a blank placeholder: it SHALL NOT count as an icon, the icons the home page names SHALL be tried after it, and one stored earlier SHALL be left out of the export and asked for again on a retry. The export made for publishing SHALL first ask the outlets not yet asked, so an outlet added since the last run is not left without its icon.

The export SHALL carry the stored image itself, as a data URI, for each outlet domain that has an exported article and an icon, and SHALL NOT carry an address for the site to fetch. Wherever the site names an outlet it SHALL show that icon, served as a file of the site, SHALL show the icon of the nearest parent domain when the export has none for a subdomain (`ca.news.example.com` shows the icon of `news.example.com`, else of `example.com`), and SHALL draw a letter tile when the export has neither. No page SHALL request an icon, or anything else it displays, from another host.

#### Scenario: Outlet with an icon
- **WHEN** an outlet's robots.txt allows it and its site serves a small raster icon
- **THEN** the icon is stored for the outlet's domain with the address it came from and the time it was fetched

#### Scenario: Outlet whose robots.txt refuses
- **WHEN** an outlet's robots.txt disallows the client, or cannot be read
- **THEN** no other request is sent to that host and no icon is stored for it

#### Scenario: Icon over the size cap
- **WHEN** the file an outlet serves is larger than the cap, or is not a raster image
- **THEN** it is not stored

#### Scenario: Blank placeholder icon
- **WHEN** an outlet's `/favicon.ico` is an ICO file with every pixel transparent and its home page names a raster icon
- **THEN** the named icon is stored and the placeholder is not

#### Scenario: Blank placeholder stored earlier
- **WHEN** a blank placeholder is already stored for an outlet
- **THEN** the export leaves that outlet out, and a retry asks the outlet again

#### Scenario: Outlet added since the last run
- **WHEN** the export for publishing is made and a source article's outlet has never been asked
- **THEN** that outlet is asked for its icon before the export is written

#### Scenario: Outlet asked before
- **WHEN** the icons command runs again
- **THEN** no request is sent for a domain that was asked before

#### Scenario: Export of an outlet's icon
- **WHEN** a published claim has an article from an outlet whose icon is stored
- **THEN** the export lists that outlet's domain with the image as a data URI and its fetch time

#### Scenario: Outlet with a stored icon
- **WHEN** a page names an outlet whose icon is in the export
- **THEN** the page shows the icon from a file of the site itself

#### Scenario: Outlet on a subdomain
- **WHEN** a page names an outlet on a subdomain with no icon in the export, and the export has its parent domain's icon
- **THEN** the page shows the parent domain's icon

#### Scenario: Outlet with no stored icon
- **WHEN** a page names an outlet with no icon in the export
- **THEN** the page shows a letter tile in its place

### Requirement: Topics are listed once they have a published claim
Menus and lists of topics SHALL include a vertical only when at least one published claim belongs to it. The index page of a vertical without published claims SHALL still exist.

#### Scenario: Vertical with no published claims
- **WHEN** a vertical is configured and none of its claims is published
- **THEN** its index page says no claims are tracked, and no menu or list links to it

#### Scenario: One listed topic
- **WHEN** exactly one vertical has published claims
- **THEN** the menu names that topic and links straight to its index

### Requirement: A record strip shows a claim's dated records on one time axis
The site SHALL be able to draw, for any published claim, a record strip: one horizontal time axis that ends at the day the registries were last checked, with a mark at the date of each news report, dated registry record, posting of trial results, regulator's decision and dated promise. Kinds of mark SHALL differ by shape or position, not by colour alone. The strip SHALL be built from the export alone, with no script in the reader's browser.

#### Scenario: Records before and after a report
- **WHEN** a claim first reported in 2026 has a trial registered in 2012 and results posted in 2015
- **THEN** its strip shows the registration mark and the results mark to the left of the report mark, each at its own date

#### Scenario: A claim with a report and nothing else
- **WHEN** a claim has one news report and no dated record
- **THEN** its strip is drawn with the axis, the report mark and the last-check end, and nothing else

#### Scenario: A promise with no date in the export
- **WHEN** a claim's report holds a promise whose date the export does not hold
- **THEN** the strip has no promise mark: a position is never estimated

#### Scenario: A promise dated after the last check
- **WHEN** a claim's promise is dated after the day the registries were last checked
- **THEN** the strip has no promise mark

#### Scenario: Many records in one year
- **WHEN** a claim has 79 dated records
- **THEN** every record is marked at its own date, marks may overlap, and a mark for posted results is never hidden by a mark for another record

### Requirement: Every record strip uses one time scale
Every record strip on the site SHALL use the same time scale: the axis SHALL start at the same year and end at the day the registries were last checked, so that the same date falls at the same place in every strip of the same width. The start year SHALL be fixed at build from the earliest dated record among published claims.

#### Scenario: Two claims in one list
- **WHEN** a list shows a claim reported in 2017 and a claim reported in 2026
- **THEN** the 2017 report mark sits to the left of the 2026 report mark by the same distance in both strips' scale

#### Scenario: A claim reported this year
- **WHEN** a claim was first reported in the year of the last check and has no earlier record
- **THEN** in a list its report mark sits near the right end of the axis and the rest of the axis is drawn empty

### Requirement: A claim page draws the claim's records on its own axis
A claim page SHALL draw the claim's record strip at the head of its recorded records, on an axis of its own: from the year of the claim's earliest dated record, or five years before its first report when that is earlier, to the day the registries were last checked. The strip SHALL have the axis's first year and the day of the last check written under its ends, and a key under it SHALL name only the kinds of mark the strip draws.

#### Scenario: A trial years before the report
- **WHEN** a claim reported in 2026 has a trial registered in 2012
- **THEN** its page's strip starts at 2012, is notched every year, and the registration mark sits at the left of the axis

#### Scenario: A report and nothing else
- **WHEN** a claim reported in 2026 has no dated record
- **THEN** its page's strip starts at 2021 and its key names the news report and no other mark

### Requirement: A record strip does not judge
The axis of a record strip SHALL be drawn at one weight and one colour along its whole length. A stretch with no mark SHALL NOT be set apart, and nothing SHALL be filled between two marks. A promise mark SHALL NOT differ according to whether its date has passed. Marks of one kind SHALL be one size. The strip SHALL NOT use a tick, a cross, or red and green.

#### Scenario: Two trials of different size
- **WHEN** a claim has a trial of 40 people and a trial of 981 people
- **THEN** their registration marks are the same size

#### Scenario: No signal for nine years
- **WHEN** a claim reported in 2017 has no dated record since
- **THEN** the axis from the report mark to the last-check end is drawn exactly as the rest of the axis

#### Scenario: A promised date that has passed
- **WHEN** a claim's report promised trials for 2020 and no trial is on record
- **THEN** the promise mark for 2020 is drawn the same as a promise mark that a record followed

### Requirement: A record strip is readable without seeing it
A record strip SHALL be exposed to assistive technology as one image with a text alternative in sentences that state counts and dates only. Its marks SHALL stay distinguishable when printed and when the reader's system forces its own colours. The strip SHALL NOT be a control and SHALL NOT respond to pointing.

#### Scenario: Screen reader on a report row
- **WHEN** a screen reader reaches the strip of a claim with five trials on record, the first registered in 2012
- **THEN** it reads that the first trial was registered in 2012, 14 years before the report, and that 5 trials are on record with the counts completed and with results posted

#### Scenario: A claim with a report and nothing else
- **WHEN** a screen reader reaches the strip of a claim with one report and no dated record
- **THEN** it reads the number of reports and that no dated record is on file as of the last check

### Requirement: Claim list tables carry the record strip
Every claim list table SHALL show each claim's record strip on the axis every list shares, drawing registry records, posted results and news reports only: a promise is in the list's own column and a regulator's decision is in the status. On a wide screen the strips SHALL sit in one column at one width so their axes align from row to row. The status label SHALL remain in sight in the same row.

#### Scenario: Topic index
- **WHEN** a reader opens a topic index with 18 claims on a wide screen
- **THEN** each row shows the claim's strip in the same column and the claim's status label

#### Scenario: Phone
- **WHEN** the same index is opened below the site's one breakpoint
- **THEN** each claim's strip is drawn across the width of its row, under its status

### Requirement: The marks of a record strip are named once per page
A page that shows a record strip SHALL carry one key that names each kind of mark in words, before the first strip. The guide SHALL hold an entry that explains the strip, what its marks rest on in the records and what it does not tell the reader.

#### Scenario: Topic index
- **WHEN** a reader opens a topic index
- **THEN** the key above the table names the registry record, results posted and news report marks, and gives the years the axis runs between

#### Scenario: Home page
- **WHEN** a reader opens the home page
- **THEN** the day list shows no record strip and no key

#### Scenario: Guide entry missing
- **WHEN** the site is built and the guide has no entry for the record strip
- **THEN** the build fails and says so

### Requirement: Registry records are grouped by reading and laid out field by field
Registry records listed on a claim page outside its trials SHALL be shown in groups by how each was read, closest to the claim first: this treatment for this condition; for another condition, patient group or setting; a study it is in but does not test; a study of something else; and last, records scored before the condition was asked. Each group's heading SHALL say its reading once, with how many records it holds. A group SHALL show its first three records and fold the rest under one control that says how many. Each record SHALL show the study's title as written in the registry, then one line of what the record says of the trial in the trials table's words: its phase, its size ("780 people planned") when the record states one, and its state. A possible record's line SHALL open with its match ("Possible match: medium, 78%"), so the uncertainty is read before its phase and state. Then the record and its page here as a trial entry names them: its identifier with its registry's name in sight, linking to the registry, and "View trial details here"; a matched record's match note follows. Then what it is for and the interventions the record names, never worded as what the trial tests, because a record lists comparators and procedures among them. A record SHALL never be worded as recruiting. A record whose fields have not been read SHALL take "Registry record" and its identifier as its title and say on a line of its own that its details have not been read, and SHALL NOT show its one-line summary in their place.

#### Scenario: Possible record read as another condition
- **WHEN** a claim page lists a candidate read as the same treatment for another condition, recruiting, Phase 1, scored 0.31
- **THEN** it sits under "Read as this treatment for another condition, patient group or setting", its title leads, its line reads "Possible match: low, 31%", "Phase 1", "120 people planned" and "Under way", then "NCT00000077 at ClinicalTrials.gov" and "View trial details here", and its interventions are under "Named in the record"

#### Scenario: Possible record not yet read into fields
- **WHEN** a candidate's record is null in the export
- **THEN** the row's title is "Registry record NCT00000077", its line reads its possible match, then "Details not read from the registry yet" and its identifier, and no summary is shown

#### Scenario: Group of more than three records
- **WHEN** a group holds five records
- **THEN** three are shown and "The other 2 of 5 records" opens the rest

### Requirement: Possible records say once that none counts, and why
Above the possible records the page SHALL say once that none of them is counted in the status and no person has checked them, then the rule that would count one: read as this treatment for this condition with a match at or above the score the export gives for approval by rule, or, when the export gives none, confirmed by a person. It SHALL link to the guide entry on match and confidence. Under a subheading for possible records beneath matched ones, the subheading SHALL NOT say again that they are not counted. The section SHALL have one name in its heading and its section-list entry, and its folded heading, section-list entry and the digest SHALL give how many records it holds, the digest's count of possible records linking to the section.

#### Scenario: Claim with one possible record
- **WHEN** a claim page lists one candidate and no other unplaced record, and the export gives 0.8 as the score for approval by rule
- **THEN** "None of these is counted in the status, and no person has checked them." appears once, followed by "…its match is 80% or more." and a link to "How a match is scored"; the folded heading says "1 possible", and the digest's "1 possible" links to the section

#### Scenario: Possible records when only a person approves a match
- **WHEN** the export gives no score for approval by rule
- **THEN** the note says a record counts only once a person confirms it, and names no percentage

### Requirement: A trial page tells citing claims from possible ones
A trial details page SHALL list the claims that cite the record (by an event or an approved match) apart from the claims it is only a possible match for, which it SHALL list under their own heading with a line saying the match is not counted in those claims' status.

#### Scenario: Trial page reached from a possible match
- **WHEN** one claim cites a trial and another has it only as a candidate
- **THEN** the trial page lists the first under "Claims citing this record" and the second under "Claims this record may be about"

### Requirement: A trial names its registry in sight
A trial entry's identifier SHALL be followed in sight by its registry's name ("NCT05899608 at ClinicalTrials.gov"), the same words a registry record row uses, so the two sections describe a trial in one grammar.

#### Scenario: Trial on ClinicalTrials.gov
- **WHEN** a claim page lists trial NCT00000002 from ClinicalTrials.gov
- **THEN** its entry reads "NCT00000002 at ClinicalTrials.gov" in sight

### Requirement: Related research on the claim page
A claim page SHALL list the claim's approved papers under a heading of their own, apart from the evidence events. Each paper SHALL show its title, year, kind, a link to it, its confidence score and its reasons in the site's words. The section SHALL say that a paper is not a trial record and does not set the status. A claim with no approved paper SHALL show no such section.

#### Scenario: Claim with no trial and two approved papers
- **WHEN** a reader opens a claim whose status is "No trial record found" and which has two approved papers
- **THEN** the page shows that status and, apart from it, two papers with scores, reasons and links

#### Scenario: Claim with no approved paper
- **WHEN** a reader opens a claim that has no approved paper
- **THEN** the page has no related research section

### Requirement: Related research is worded without a verdict
The wording of the related research section and of each reason SHALL describe what was found and SHALL NOT say that a paper supports, confirms or refutes the claim. A reason code the site has no wording for SHALL fail the site build.

#### Scenario: Unknown reason code
- **WHEN** the export carries a reason code the site does not know
- **THEN** the site build fails and names the code

### Requirement: A score is one chip that opens its meaning
Wherever a claim page or a trial page shows a score (a registry record's, a paper's or a trial's match to the claim, a background term's match, how sure the check of a reported statement is, a lower-band reading), it SHALL be drawn as the same chip: the band in words and the percentage, in sight, with nothing to press before either is read. The chip SHALL open a panel, on hover with a mouse, on a press and from the keyboard, that says what the score is about and that it says nothing about the treatment. The chip's text SHALL say what was matched ("Match to this claim: high, 92%"); the opening words MAY be left undrawn where the row itself says what is matched, and SHALL then remain for a screen reader and on paper. A possible record's chip SHALL say "Possible match" in sight. A lower-band reading's chip SHALL say "Low confidence" in words, and the sentence that it does not decide the status SHALL stay in sight beside it. No colour, fill, meter or mark SHALL say how high a score is. This replaces the requirement "A match score reads as a note about the match".

#### Scenario: Matched registry record
- **WHEN** a claim page lists a registry record matched at 0.92
- **THEN** a chip at the end of its title's line reads "High, 92%", a screen reader hears "Match to this claim: high, 92%", and opening it gives how the record was read and that the score says nothing about whether the treatment works

#### Scenario: Possible registry record
- **WHEN** a claim page lists a candidate scored 0.31
- **THEN** its chip reads "Possible match: low, 31%" in sight, before its phase and state

#### Scenario: Background term
- **WHEN** "At a glance" shows a condition matched to a vocabulary term at 0.98
- **THEN** the chip stands beside the row's value and reads "High, 98%", and the row's disclosure line no longer carries the score

#### Scenario: Lower-band reading
- **WHEN** a claim's evidence stage was read at 0.41 and not confirmed
- **THEN** the chip is outlined in dashes and reads "Low confidence · 41%", and "Not confirmed, so it does not decide the status." is in sight without opening anything

#### Scenario: On a phone
- **WHEN** a chip is pressed at 375 pixels wide
- **THEN** its press area is at least 44 pixels tall and the panel opens within the screen

### Requirement: Only a score is drawn as a score chip
Words that say how a background term was found and carry no percentage SHALL open the same panel as a score chip but SHALL NOT be drawn with the chip's outline. Inside a score chip the percentage SHALL be set apart from the band's words in the markup, and the text read out and printed SHALL remain the whole phrase.

#### Scenario: A drug row in "At a glance"
- **WHEN** a treatment's drug record was found by its exact name and its kind term matched at 0.98
- **THEN** "Drug record: by exact name" is drawn as plain underlined words that open a panel, and "Kind term: high, 98%" is drawn as a chip

### Requirement: The box and its answer stay in step
On the home page, once the box has answered, nothing the page sets under the box SHALL be drawn between the box and its answer until the search is cleared. A field emptied by the reader SHALL leave no answer and no searched words in the page's address.

#### Scenario: An answer under the box
- **WHEN** a reader pastes the address of a tracked article on the home page
- **THEN** the answer follows the field and its one line of help, and the words to try, the tally and the example are not drawn

#### Scenario: The field emptied
- **WHEN** a reader with an answer on screen empties the field with Escape, its cross or the delete key
- **THEN** the answer is gone, the list is back in its place, and the address holds no searched words

#### Scenario: Going to the answer
- **WHEN** a search on the home page answers in the list's place, on a screen 34rem wide or more
- **THEN** the line under the box ends in a link, and taking it puts the reader on the answer's heading

### Requirement: Search history redraws each answer
Each lookup and clear SHALL add one history step. Back and Forward SHALL restore that step's answer, chosen topic and loaded result pages. Changing the topic or loading more results SHALL update the current step. A pasted article address SHALL stay in page memory and SHALL NOT enter the page's address or saved history state.

#### Scenario: Back
- **WHEN** a reader searches for "tooth regrowth" and presses Back
- **THEN** the page stays, the field is empty and the list is back; Forward draws the answer for "tooth regrowth" again

#### Scenario: Back to a pasted link
- **WHEN** a reader pastes an article's address, clears its answer and presses Back in the same page
- **THEN** the field and answer return without putting the article's address in the page's address, and Forward clears them again

#### Scenario: A topic that first appears in a later batch
- **WHEN** the page opens a search address with a topic whose first match is after the first twenty claims
- **THEN** it reads enough results to draw the answer with that topic selected

### Requirement: A failure offers the same question again
A search or a lookup that could not be read SHALL say so, SHALL offer a control that asks the same question again, and SHALL say where every tracked claim is listed. It SHALL NOT tell the reader to type in the box.

#### Scenario: The lookup file cannot be read
- **WHEN** a reader pastes an article's address and the lookup file cannot be fetched
- **THEN** the page says the lookup is not available right now, offers "Try again", and links to the topics

### Requirement: The box says where a pasted link goes
Under the field, wherever the box is drawn, one line SHALL say that a pasted link is compared in the reader's browser. Where the site is built with no registry search it SHALL say the link is sent nowhere; where it is built with one it SHALL say the link is sent only if the reader asks for that search.

#### Scenario: No registry search
- **WHEN** the site is built with no lookup service
- **THEN** the line reads "A pasted link is compared in your browser and sent nowhere."

### Requirement: An untracked article is offered a date to come back on
An article the site does not track SHALL be offered a calendar file, made on the reader's device, to check it again in six months or a year, whether or not a registry search is offered or asked for.

#### Scenario: Not tracked, no registry search
- **WHEN** a reader pastes the address of an article the site does not track, on a site built with no lookup service
- **THEN** "Check again later" follows the answer with both dates

### Requirement: A search's count is of every claim found
The count SHALL be the number of claim pages the index found. While more remain, the heading and the line under the box SHALL state how many are shown and how many were found. The list SHALL offer the next twenty and say how many remain. Each batch SHALL follow the existing rows without reordering them and put the reader on its first claim. A topic change SHALL preserve the pending batch, and a topic or batch that arrives late SHALL NOT replace a topic chosen or a search asked after it.

#### Scenario: More found than drawn
- **WHEN** the index finds 161 claims for "cancer" and the page draws 20
- **THEN** the count reads "First 20 of 161 tracked claims", and the list ends with "Show 20 more" over "141 more tracked claims hold these words."

#### Scenario: The next twenty
- **WHEN** the reader presses "Show 20 more"
- **THEN** forty claims are drawn, the first twenty where they were, the count reads "First 40 of 161 tracked claims", and the page has not moved

#### Scenario: All drawn
- **WHEN** the index finds 3 claims
- **THEN** the count reads "3 tracked claims"

#### Scenario: The topic changes while the next twenty are loading
- **WHEN** the reader asks for more results and chooses a topic before they arrive
- **THEN** the next batch is added once to the claims it was asked for, and the answer is drawn with that topic selected

### Requirement: An exact headline keeps the index count
An exact report headline's claim SHALL be shown first and SHALL count once if the index found it. An exact headline outside the index SHALL be shown above the indexed matches without changing their count.

#### Scenario: Exact headline among the later matches
- **WHEN** the index finds 40 claims, including the exact headline's claim in the second batch
- **THEN** the exact claim leads the first twenty, the count reads "First 20 of 40 tracked claims", and the next batch has the other twenty

### Requirement: A treatment suggested for another name says that name
Where the typed words are in none of a treatment's first name but in another of its names, its suggested row SHALL give the first name followed by the name the words are in.

#### Scenario: A brand name typed
- **WHEN** a reader types the start of a treatment's second name
- **THEN** the row reads the first name, then the second name in brackets

### Requirement: A result says where its claim stands right after its headline
In a search's answer each result SHALL give, in this order in the page itself, the claim's headline, where the claim stands, the treatment and what it is claimed for, and what the searched words were found in. On a screen narrower than 34rem these SHALL be drawn in that order in one column, with one report or trial named and the rest counted.

#### Scenario: A phone
- **WHEN** a reader on a phone searches for "cancer"
- **THEN** each result shows its status under its headline, before any report

### Requirement: A suggested row that opens a page is marked
A suggested row that opens a page SHALL end in an arrow and SHALL be named to a screen reader as opening its page. A row that searches in place SHALL have no arrow and SHALL be named to a screen reader as searching here.

#### Scenario: A topic and a condition
- **WHEN** a topic and a condition are offered for what is typed
- **THEN** the topic's row ends in an arrow and is named "Opens its page."; the condition's row has no arrow and is named "Searches here."

### Requirement: Topics beside a search count every claim found
Each topic and "All results" SHALL show the total claim pages the index found, without reading those pages for their counts. Picking a topic SHALL show its claims, loading the first twenty as needed. The answer SHALL show how many claims are drawn, the topic's total if more remain, and the total across all topics.

#### Scenario: More found than read
- **WHEN** the index finds 59 claims for "vaccine" and the page has read 20
- **THEN** the topics' counts add up to 59, and "All results" reads 59

#### Scenario: A topic with no claim among those read
- **WHEN** the reader picks a topic that holds 3 of the 59 claims, none of them among the 20 read
- **THEN** those 3 claims are read and shown, and the count reads "3 of 59 tracked claims, in" the topic's name

#### Scenario: A topic that holds more than twenty
- **WHEN** the reader picks a topic that holds 33 of the 59 claims
- **THEN** 20 are shown, the count reads "First 20 of 33 in" the topic's name ", of 59 tracked claims", and "Show 13 more" draws the rest of that topic's

### Requirement: The field's example words are chosen by rule
At build, the example SHALL use the first eligible claim in the site's example order. Its treatment name SHALL have one to three plain words, fit the field, appear in its own headline, and appear whole in no other claim's headline, treatment names, condition or report titles. A search for the words SHALL lead with that claim. If none qualifies, the field SHALL offer a link alone.

#### Scenario: The example searched
- **WHEN** a reader types the field's example words and looks them up
- **THEN** the closest match is the claim the words were chosen from

#### Scenario: No claim passes
- **WHEN** no published claim's treatment name passes the rule
- **THEN** the field's example reads "https://…" and no words

### Requirement: A searched word no claim holds is named
Where a search by words finds claims and the search index holds one of the words nowhere, neither whole, in another of its forms, nor as the start of a longer word, the answer SHALL name that word under its heading and say that the claims shown were found without it.

#### Scenario: A mistyped word
- **WHEN** a reader searches for "lung cancercancer"
- **THEN** the answer says no tracked claim holds “cancercancer”, and that the claims shown were found without that word

#### Scenario: The start of a word
- **WHEN** a reader searches for "canc", which starts a word that claims hold
- **THEN** no word is named

### Requirement: The suggestions have room and stand clear of the field's line
The suggestions SHALL start under the line that says where a pasted link goes. Where they do not fit between there and the bottom of what the reader can see, the box SHALL be brought to the top of the screen. The panel's height SHALL be taken from the part of the screen not covered by an on-screen keyboard.

#### Scenario: The box low on the screen
- **WHEN** a reader types in the home page's box at 1280 by 720
- **THEN** the box moves to the top of the screen and every suggested row is in view

### Requirement: On a touch screen a typed search puts the reader on its answer
On a screen worked by touch, a search by words that has answered SHALL move the reader from the field to the answer's heading. On a screen narrower than 34rem the line under the box that says where the answer is SHALL NOT be drawn, and SHALL still be announced to a screen reader.

#### Scenario: A phone
- **WHEN** a reader on a phone types "cancer" and sends it
- **THEN** the field is left, the keyboard closes, the answer's heading follows the field's line of help, and the reader is on that heading

### Requirement: A search is named in the page's title
While a search by words is answered the page's title SHALL begin with the searched words, and SHALL return to the page's own title when the search is cleared. A pasted article address SHALL NOT enter the title.

#### Scenario: Searched and cleared
- **WHEN** a reader searches for "vaccine" and then clears the search
- **THEN** the title begins “vaccine” while the answer is shown, and is the page's own title afterwards

### Requirement: A search is answered with its closest match first
A search typed in the lookup box SHALL be answered with every matching claim on one row each: its status in words, its place on the path, when it was first reported, its headline as a link, the treatment and what it is claimed for, and its topic. Matches SHALL be ordered by a fixed rule over the words they hold: the searched words side by side, then all of them, in the claim's own headline, then in a report's headline, then in the treatment and condition, the search index's order breaking a tie. The first SHALL be labelled the closest match. A word search SHALL NOT draw any one claim as the full answer a tracked article gets. The searched words SHALL be marked where they stand in a match. The answer SHALL end with a link to the page of each topic among the matches. No score SHALL be shown, and no mark, colour or order SHALL rank a treatment.

#### Scenario: Several matches
- **WHEN** a reader searches for "regrowing teeth" and one matching claim's headline says it "regrows teeth" while the search index lists another first
- **THEN** the claim whose headline holds the words side by side is first, labelled "Closest match", with its status in words
- **AND** the other matches follow one to a row, each with its status in words

### Requirement: On the home page a search answers in the list's place
On the home page a search's answer SHALL stand in the place of the day-by-day list, in the same sheet, until the reader clears it or asks something else, and the list SHALL come back unchanged when it is cleared. Under the box one line SHALL say where the answer is. The answer SHALL say how many claims match once, beside the one control that clears the search. Where the matches belong to two topics or more, they SHALL be counted by topic, under the answer's heading and, on a wide screen, in the side column, and each topic SHALL narrow the answer to its matches and be kept in the page's address. On any other page the same answer SHALL stand under the box.

#### Scenario: Clearing a search
- **WHEN** a reader presses "Clear search" beside the answer's count
- **THEN** the box is empty, the page's address carries no words, and the day-by-day list is shown as before

#### Scenario: Narrowing by topic
- **WHEN** a search matches claims in two topics and the reader presses one topic in the side column
- **THEN** only that topic's matches are shown, the answer says how many of all the matches they are, and the page's address names the topic

### Requirement: A search says what each match was found in
Under each match a search SHALL name every report headline and trial title of that claim that holds the searched words, up to a fixed number, each with its kind in words, the matched text with the words marked, and where it is from: for a report the outlet's name, its icon where the site holds one, and the date; for a trial the registry, the identifier and the phase. Every result SHALL remain a claim, led by its status.

#### Scenario: A report headline holds the words
- **WHEN** a reader searches for "regrowing teeth" and a matching claim's report is headlined "New drug to regrow lost teeth"
- **THEN** under that claim a line reads "Report headline" with the headline quoted, "regrow" and "teeth" marked, the outlet's icon and name, and the report's date

### Requirement: An exact headline or a trial identifier is answered with that thing first
Words that are the whole headline of a tracked report SHALL put that report's claim first: the answer SHALL say a tracked report has this headline, show the report with the words marked, then the claim drawn as a tracked article's answer is drawn. A search that is a trial registry's identifier SHALL be answered from the trials matched to tracked claims, not from the word search: the trial's registry record, then each claim it is matched to, and a sentence saying a trial on record is not a treatment option. An identifier with no trial on record SHALL be answered with a sentence saying so and, where the registry's address is built from the identifier alone, a link to the record on the registry.

#### Scenario: A trial identifier
- **WHEN** a reader searches for "NCT01814436"
- **THEN** the answer shows that trial's registry record and the one claim it is matched to, and no claim that only shares the prefix "NCT"

#### Scenario: An identifier not on record
- **WHEN** a reader searches for an identifier no tracked claim has
- **THEN** the answer says no trial with that identifier is matched to a claim tracked here, and links to it on its registry

### Requirement: A search with no result points to the link
A search that finds no tracked claim SHALL say that nothing tracked here matches the words, in wording that cannot be read as a claim's status, and SHALL say that pasting the article's link is the way to check a story.

#### Scenario: No match
- **WHEN** a reader searches for words no tracked claim holds
- **THEN** the answer reads "Nothing tracked here matches" with the words, and names pasting the article's link

### Requirement: The box offers rows for what is typed
While two or more letters of words stand in the search box, and scripts run, the box SHALL offer rows under it that hold every typed word at the start of a word. The rows SHALL be of five kinds, each under its name and always in this order: topics, treatments, conditions, reports, trials on record. A kind with no row SHALL be left out, and a kind SHALL show two rows at most. With no row to offer, nothing SHALL be shown. A pasted or typed address SHALL offer nothing.

#### Scenario: Five kinds
- **WHEN** a reader types "lung" and the site holds a topic, treatments, conditions, reports and trials with a word that starts so
- **THEN** rows are offered under "Topics", "Treatments", "Conditions", "Reports" and "Trials on record", in that order, two at most under each

#### Scenario: One letter
- **WHEN** a reader types one letter
- **THEN** nothing is offered

#### Scenario: An address
- **WHEN** a reader pastes the address of an article
- **THEN** nothing is offered and the address is looked up as before

#### Scenario: A complete trial number is typed before detail arrives

- **WHEN** a reader types NCT04510194 before search details load and leaves the field focused with the same input
- **THEN** the matching trial appears when its detail arrives without another keystroke. Dismissed suggestions stay dismissed

### Requirement: A suggested row says what it is and what is behind it
A row SHALL show what it names with the typed words marked where they start a word, and beside it: for a topic and a condition, how many claims; for a treatment, what it is for and its claim's status in the site's words; for a report, its outlet and date; for a trial, its identifier first, then its title and its phase. A report's title SHALL stand between quotation marks. A trial SHALL be listed as a record and never worded as a treatment to take. A condition SHALL be one row however many claims are for it.

#### Scenario: A treatment
- **WHEN** a treatment's name starts with what is typed
- **THEN** its row gives the name, what it is for, and where its claim stands, and opens the claim's page

#### Scenario: A condition with three claims
- **WHEN** three claims are for "Lung cancer"
- **THEN** one row says "Lung cancer" and "3 claims", and taking it searches for "Lung cancer"

### Requirement: The order of suggested rows is by rules a reader could check
No model and no score SHALL order the rows. Topics SHALL come by whether the title begins with the first typed word, then by claims. A treatment whose name begins with the word SHALL come before one that holds it later, the shorter name first. The condition most claims are for SHALL come first. Reports SHALL be newest first, each title once. A trial found by the start of its identifier SHALL come before one found by its title, and after that the newest identifier first.

#### Scenario: Two reports
- **WHEN** two reports hold the typed word, dated 15 November and 17 August
- **THEN** the one of 15 November is the first row

### Requirement: The rows are worked by keys and by a press
The down key SHALL choose the first row and then the next, the up key the one before; past either end the box itself SHALL be chosen again. Enter SHALL take the chosen row; with no row chosen it SHALL search for the words as typed, as before. Escape SHALL close the rows and keep the words. A last row SHALL send the words as typed. The box SHALL say to a screen reader that it has rows, how they are grouped, and which is chosen. Without scripts the box SHALL work as before.

#### Scenario: Enter with nothing chosen
- **WHEN** a reader types "lung" and presses Enter without choosing a row
- **THEN** the site searches for "lung" as it did before this change

#### Scenario: Escape
- **WHEN** rows are shown and the reader presses Escape
- **THEN** the rows close and "lung" stays in the box

#### Scenario: The keyboard selection survives a detail refresh

- **WHEN** a reader types lung and selects the first suggestion with Down before detail data arrives
- **THEN** if that suggestion still exists it stays selected by identity and Enter opens it, even if its row position changed

### Requirement: A section may say what it holds from an info mark beside its heading
A section of a claim page MAY carry an info mark beside its heading in place of an opening paragraph. The mark SHALL open the section's note in a panel on hover with a pointer, on a press and from the keyboard, and the panel SHALL close on Escape. The mark SHALL be named after its section for a screen reader. On paper the note SHALL be printed whole under its heading. A note that says the page is not advice SHALL NOT be moved into a panel.

#### Scenario: Reading a section
- **WHEN** a reader looks at "Trials on record"
- **THEN** the heading is followed by the trials, and an info mark beside the heading opens what the section holds

#### Scenario: A note that says "not advice"
- **WHEN** a reader looks at "The record in brief"
- **THEN** its note is in sight under the heading, whole, with no mark in its place

### Requirement: Every section of a claim page follows one funnel
Each section of a claim page below "At a glance" SHALL show, in sight, a label and its value, with a number or a shape where it can stand for words; SHALL give what the value means and where it is from at one press; and SHALL give why it is listed and how sure a reading is at a second press or in the same place. Nothing the page showed before SHALL be removed by this: it is moved down the funnel. A shape SHALL stand beside words or a number. A shape MAY carry the hue of its kind; no hue SHALL be red or green, and a kind SHALL never be told by hue alone. A paragraph that describes a section SHALL open from the info mark beside the section's heading and SHALL NOT stand under the heading.

#### Scenario: Opening an answer twice
- **WHEN** a reader opens "Compared with a placebo?" and then "Where this is read from"
- **THEN** the first press shows what a placebo is and how many records name none, and the second shows which registry records the answer was read from and when

### Requirement: The record in brief opens on one sentence
"The record in brief" SHALL open on one plain sentence that gives every answer the section holds, in the order of its rows, with each answer's figure a link to its row. Under it each answer SHALL be a row holding its question and its answer, and, where the answer is so many of the claim's trials, a bar that shows the share and names it in words for a screen reader. The sentence SHALL say nothing the rows do not.

#### Scenario: A claim with seven trials
- **WHEN** a reader opens a claim with seven trials, one of which names a placebo and one of which has posted results
- **THEN** the sentence reads "Tested in 7 trials, the largest planned for 1,200 people. One record names a placebo. 1 of 7 has posted results, …", and "7 trials" leads to the row "Tested in people?"

#### Scenario: A single trial has only planned enrollment

- **WHEN** the only trial has not started, its registry entry lists 456 people as planned and it names a planned outcome
- **THEN** the summary and expanded rows identify enrollment and outcome as planned. Neither says testing or measurement has already occurred

#### Scenario: Sham and placebo have distinct registry codes

- **WHEN** five embolisation trials name a sham comparator and none names a placebo
- **THEN** the brief and expanded facts report five sham comparisons. Mixed comparators are attributed to the trials recording each

### Requirement: Statements are grouped by who said them or by kind
A claim's statements SHALL stand in one list, grouped by who the report had saying each; a reader SHALL be able to group them instead by kind of statement, or by report, wherever that order makes more than one group. With no script the statements SHALL be grouped by who said them. Each row SHALL say, beside the statement, the two of kind, speaker and report that its group does not, the report at least by its outlet, and SHALL give the report's title as a link where the row opens. Each statement SHALL carry a mark for how firmly the report put it, named in words once over the list, and SHALL keep its attribution in words for a screen reader. A statement's score SHALL be shown on its row when the check is less than very sure, and where the row opens otherwise.

#### Scenario: A statement the check is very sure of
- **WHEN** a statement's confidence is 0.93
- **THEN** its row shows its kind, its mark and its words, and opening it and then "How sure this reading is" shows "Very likely in the report · 93%"

#### Scenario: A statement the check is less sure of
- **WHEN** a statement's confidence is 0.62
- **THEN** its row shows "Likely in the report · 62%" without a press

### Requirement: Recorded opens on the record's moments
"Recorded" SHALL open on the record's moments in order of date: the first trial registered, the first trial started, the report, the first results posted, a regulator's decision, the latest record where none of these is it, and a promised date. Each SHALL be a shape, a name and a date, and SHALL lead to its year in the timetable. The timetable, with its strip and its filter, SHALL be one press under the moments, SHALL be open on paper, and SHALL open when a link leads to a record inside it.

#### Scenario: Following a moment
- **WHEN** a reader presses "First results posted"
- **THEN** the timetable opens and the year of that record is in view

#### Scenario: An article follows the last registry event

- **WHEN** the timetable includes a February 15 registry event and an April 12 news report
- **THEN** April 12 is the latest record. The earlier event receives no latest label, including when the newest date is already shown as a milestone

### Requirement: The trials' spread is drawn over their table
Where a claim has four trials or more, the trials section SHALL show a mark for each trial under its phase, in the shape of its state and ringed where it has posted results, with a key in words. Each trial's row SHALL show its size as a bar against the claim's largest trial. The drawing SHALL be for the eye only: the table says the same in words.

#### Scenario: Forty-seven trials
- **WHEN** a reader opens a claim with 47 trials
- **THEN** the marks stand in columns by phase with the number of trials over each, and a mark leads to its trial

### Requirement: Organisations stand as names beside their part
The organisations section SHALL show one row for each part organisations play, with the names of that part beside its label in order of name; a sponsor's name SHALL carry how many of the claim's trials name it. A name SHALL open its parts, its trials, what an open registry says the organisation is, and whether a registry record was matched.

#### Scenario: A sponsor of three trials
- **WHEN** a reader presses the name of an organisation that sponsors three of the claim's trials
- **THEN** a panel names the three trials and says whether the name was matched to a registry record

### Requirement: Sharing and reminders are one section of labelled rows
A claim page SHALL offer sharing, reminders, following, its feed and its embed as rows of one section, each a label and its controls. The reminders' row SHALL be shown only where the browser can make and save the file, and a link to "Check again later" SHALL open the section and lead to that row.

#### Scenario: From the band
- **WHEN** a reader presses "Check again later" in the band
- **THEN** "Keep or pass on" opens and the row "Remind me" is in view

### Requirement: A trial's row is one line that opens
On a wide screen a trial's row SHALL hold, on one line, how many people it enrolled or plans to with a bar against the claim's largest trial, its phase, its state beside its shape, when it posted results, and its number. What it was compared with and its main measure SHALL be the first facts where the row opens. A trial that has the claim's treatment only as its comparison SHALL say so on the row.

#### Scenario: A finished trial with results
- **WHEN** a reader looks at a trial that finished and posted results
- **THEN** its row reads its size, its phase, "Finished" with its date beside a ringed full mark, the date results were posted and its number, and opening it gives what it was compared with and its main measure first

### Requirement: A folded year is drawn as its records
In the timetable a year that is folded SHALL show a shape for each of its records, oldest first, in the shapes the trials table uses, with a report as the report's mark, then how many records it holds. What the shapes stand for SHALL be said once over the timetable, and the kinds of record SHALL be said in words to a screen reader.

#### Scenario: A year of seventeen records
- **WHEN** a reader looks at a folded year that holds seventeen records
- **THEN** its row shows seventeen shapes and "17 records", and opening it lists the records

#### Scenario: A folded year contains a retraction

- **WHEN** a folded year contains a retraction alongside trial events
- **THEN** the finished-trial symbol denotes only a recorded completion, and the retraction remains identifiable in the row

### Requirement: A registry record is one line that opens
A registry record that is not a trial on the page SHALL be a row of its title, what its record says of the trial or that it is not yet read, and its match, which stays in sight. A possible record SHALL be marked and named as possible before its title. Where to read the record, how it was read and what it names SHALL be where the row opens.

#### Scenario: A possible record not yet read
- **WHEN** a reader looks at a possible record whose details are not yet read
- **THEN** its row reads its registry number, "Details not read from the registry yet" and "Possible match: medium, 79%", and opening it gives the link to the registry

### Requirement: A section's heading is set apart from its content
Each section of a claim page SHALL start in the same way: more room over its heading than between any two things inside a section, and a heading that differs from every text under it in face, size and colour. A heading SHALL NOT be set apart by a rule heavier than the hairlines between rows. A heading that follows a folded section SHALL stand closer to it than to an open one.

#### Scenario: Skimming for a section
- **WHEN** a reader scrolls a claim page looking for "Trials on record"
- **THEN** each section's heading is the only text in the heading face and the accent colour, with more room over it than anywhere inside a section
- **AND** no line on the page between two headings is heavier than a hairline, except the timeline drawn under "Recorded"

#### Scenario: Where a section's fold mark stands
- **WHEN** a claim page is read at a width that shows the side columns
- **THEN** each section's fold mark stands to the left of its heading, in the sheet's margin, and the heading's title starts on the edge its rows start on
- **AND** at a narrower width the mark stands at the right end of the heading's first line

#### Scenario: Folded sections in a row
- **WHEN** several sections one after another are folded
- **THEN** their headings stand close together as a list, with no rule between them

### Requirement: What a fact row opens to starts under its label and value
What a row of a fact sheet opens to SHALL start under the taller of the row's label and its value, across the row's full width, at every width.

#### Scenario: A label of two lines
- **WHEN** a reader opens the row "Compared with a placebo?" at a width where that label takes two lines
- **THEN** the whole label is in sight and what the row opens to starts under it

### Requirement: A paper's title can be read whole
On a closed row a paper's title SHALL be shown on at most two lines. On an opened row, with no script, and on paper, the title SHALL be shown whole.

#### Scenario: A title of 196 characters
- **WHEN** a reader opens the row of a paper whose title is 196 characters long
- **THEN** the whole title is in sight

### Requirement: The digest counts the trials' states under a status that names a phase
When a claim's status is not Trial registered and it has trials on record, the digest panel SHALL say, after what the status means, how many trials are on record and how many are under way, finished and stopped early, leaving out a state no trial has. Where no trial is in one of those three states, it SHALL count every state instead, so the count never stands bare. For any claim with a Phase 4 trial, the status panel SHALL give the number of Phase 4 trials and explain that the path counts phases up to Phase 3. This applies even when the current status is off the path. The digest SHALL omit this note. The sentence SHALL be a count of records and SHALL NOT say what the counts mean.

#### Scenario: Most trials stopped early
- **WHEN** a reader opens a claim whose status is Phase 3 trial and which has 9 trials on record, 3 finished and 6 stopped early
- **THEN** the digest says "9 trials on record: 3 finished, 6 stopped early."

#### Scenario: Forty-nine trials in six states
- **WHEN** a claim has 49 trials on record: 5 under way, 1 not started, 32 finished, 3 stopped early and 8 in other states
- **THEN** the digest says "49 trials on record: 5 under way, 32 finished, 3 stopped early."

#### Scenario: Phase 4 trials on record
- **WHEN** a claim whose status is Phase 3 trial has 47 trials on record, 24 of them Phase 4
- **THEN** the panel that opens from the status says, under the path's places, that 24 trials on record are Phase 4 trials and that the path counts phases up to Phase 3

#### Scenario: A Phase 4 trial is present with an off-path status

- **WHEN** the claim has a Phase 4 trial but its current status does not display the six-stage path
- **THEN** the status panel still gives the count of Phase 4 trials and explains that the path ends at Phase 3

### Requirement: No approval is said by what the site reads
Where no approval is among a claim's records, the answer to "Approved by a regulator?" SHALL say that none is listed and that regulators' records are not read, and what the row opens to SHALL say that an approval can exist and not be listed.

#### Scenario: A claim with a report of an approval and no approval record
- **WHEN** a claim lists a news report of an approval and holds no record of one
- **THEN** the answer reads "None listed. Regulators' records are not read", and never "None on record"

### Requirement: An unconfirmed stage reading's chip says what it is
The chip beside an evidence stage that was read but not confirmed SHALL say that the reading is not confirmed and the score it was read at. The panel the chip opens SHALL name the low-confidence band.

#### Scenario: A reading at 95%
- **WHEN** a claim's evidence stage was read at 95% and not confirmed
- **THEN** the chip reads "Not confirmed · read at 95%" and the line beside it says that it does not decide the status

### Requirement: A key names only the marks its list draws
A key over the trials' table or the folded years SHALL list only the marks drawn under it, each in the words the rows use for it.

#### Scenario: A claim with no trial stopped early
- **WHEN** none of a claim's trials was stopped early
- **THEN** the trials' key has no mark for "Stopped early"

### Requirement: A long timetable folds by year
On a claim page whose timetable holds more than 20 records, the years before last year SHALL each be drawn as one line that states how many records the year holds and of which kinds, and that opens to those records. The current year and last year SHALL be drawn open. A year that a promise names SHALL be drawn open, so that a promise is never folded away from its record. A folded year that holds a record the status rests on SHALL say so with the basis mark and in words for a screen reader. A link to a record in a folded year SHALL open that year. While the timetable is narrowed to one kind of entry, and on paper, every year SHALL be open. A claim with 20 records or fewer SHALL NOT be folded.

#### Scenario: A claim with many records
- **WHEN** a reader opens a claim with 147 records
- **THEN** this year's and last year's records are listed, and each earlier year is one line with its count and its kinds

#### Scenario: Following the status to its record
- **WHEN** a reader follows a link from the status card to a record in a folded year
- **THEN** that year opens and the record is in view

#### Scenario: A short record
- **WHEN** a claim has five records
- **THEN** every year is drawn open

### Requirement: A record page's sections share one container and one opening note
On a claim page and a topic page, every section's rows SHALL stand between a rule above and a hairline below, with no rounded frame around a table. A section's opening note SHALL be set in the note size and the muted colour. A note that says the page is not advice SHALL NOT be cut short.

#### Scenario: Reading down the page
- **WHEN** a reader scrolls a claim page
- **THEN** each section starts with its heading, at most one muted note, and rows under one rule, whether the section is a table or a list

### Requirement: The trials on a claim page read as one table
On a wide screen the trials table's columns SHALL be named once, above every group, and SHALL stay in view while the groups scroll. Each group's own column names SHALL remain available to a screen reader. Each group SHALL be introduced by a row that names it and states how many trials it holds.

#### Scenario: Scrolling the trials
- **WHEN** a reader scrolls through a claim's trials at 1400 pixels wide
- **THEN** the column names stay at the top of the view and each group begins with a row naming it and its count

### Requirement: A record page's sections share two column stops and one right edge
On a wide screen the sections of a record page SHALL share two column stops: what a label, a group's name, a statement's kind or a year names SHALL start on the first, and a second column (the brief's answers, a paper's ties, an organisation's parts) SHALL start on the second. Every list, strip and rule of a section SHALL run to the section's right edge. A table with named columns MAY keep its own columns.

#### Scenario: Reading down the page
- **WHEN** a reader scrolls a claim page on a wide screen
- **THEN** the values of "At a glance", the questions of "The record in brief", a report's statements and the timetable's records start at one distance from the left edge, and no section's rule stops short of the right edge

### Requirement: Rows that open share one press
An answer of "The record in brief" SHALL open as a fact row does: by its whole line, which is tinted under the pointer and while open and ends in the round fold mark; what it opens to SHALL lie on the page's ground. Anything that folds the rest of a list or a part of a section SHALL be drawn as one kind of line with a chevron that turns.

#### Scenario: Opening an answer
- **WHEN** a reader opens "Tested in people?"
- **THEN** the line is tinted, its mark points up, and the sentences under it stand on the page's ground with no panel around them

### Requirement: Lists of things on a record page share one row
On a record page a paper, an organisation and a registry record SHALL each be drawn as one row of the same parts: what the thing is at the section's left edge, with at most one grey line under it; how it is tied to the claim, from the second column stop, in one line; and what ends its line (a score, the mark that opens it) at the section's right edge. A score SHALL stay in sight on the row. Where a record came from, when it was read, and the sentences a mark stands for SHALL be shown where the row opens, and SHALL be shown without a press when the page has no script and on paper.

#### Scenario: A paper tied to two trials
- **WHEN** a paper is listed by one trial's sponsor and linked by the registry to another
- **THEN** its row shows its title, its kind, journal and year, and the two trials' numbers each beside a mark, and opening it gives each tie as a sentence and when the index record was read

#### Scenario: A sponsor
- **WHEN** an organisation sponsors two of the claim's trials
- **THEN** its row shows its name and "Sponsor of 2 trials" beside the drawing of a registry record, and opening it names the two trials

### Requirement: Marks say a kind or a state, with words, and never a verdict
A mark that stands for how a paper came to be listed SHALL be explained in words once over its list and again, as a sentence, where its row opens. A mark for a trial's state SHALL stand beside the words that say the state. Every such mark SHALL keep its shape in every state; it MAY carry the hue of its kind, never red or green, and a state SHALL never be told by hue alone: it says what kind of tie or which state, never whether a result is for or against a treatment.

#### Scenario: A column of trial states
- **WHEN** a reader looks down the State column of the trials table
- **THEN** each state's words are preceded by a grey shape, a full circle for a finished trial, a half for one under way, a ring for one not started and a square for one that was halted

### Requirement: A record of the timetable is one line
On a wide screen a record of the timetable SHALL be one line: the drawing of its kind, its day, what happened, and at the end of the line the link to where it can be checked.

#### Scenario: A trial registered
- **WHEN** a reader looks at "29 Oct, Trial registered"
- **THEN** the registry's name and the trial's number are a link at the right end of the same line

### Requirement: A control a script works holds its place while the page loads
A control that only a script can work SHALL take its place in the page from the first paint and SHALL be out of sight, and out of reach of a keyboard and a screen reader, until its script is ready. Where scripts do not run, the control SHALL be left out of the page.

#### Scenario: The home page while its scripts load
- **WHEN** a reader opens the home page and its scripts have not yet run
- **THEN** the kind field, the span field, the status field, the list tabs and the words to try each hold their place, and nothing below them moves when they come into sight

#### Scenario: A reader without scripts
- **WHEN** a reader opens the home page in a browser that runs no scripts
- **THEN** none of those controls is shown and none leaves a gap

### Requirement: Text holds its place when a face arrives
Each of the site's faces SHALL name a fallback drawn from a font already on the device and scaled to the face's widths and line height. A device without that font SHALL use the next font named.

#### Scenario: A slow connection
- **WHEN** a page is painted before a face has arrived
- **THEN** its text is drawn in the fallback, and its lines keep their height when the face takes over

### Requirement: A page a reader points at is fetched ahead
The site SHALL fetch a page of its own when a reader points at or focuses a link to it, and SHALL NOT fetch ahead a page on another site.

#### Scenario: Pointing at a claim
- **WHEN** a reader on the home page points at a claim's link
- **THEN** that claim's page is fetched before the link is pressed

### Requirement: An unconfirmed stage reading is marked on the claim page
When the export carries a stage reading for a claim, the claim page SHALL show, where a confirmed stage would be shown, the stage the reading chose, marked low confidence with its score as a percentage, a statement that it is not confirmed and does not decide the status, and the other stages the reading weighed with their percentages. The page SHALL word nothing else from the reading: lists, summaries, the claim's brief and the open data file SHALL use the confirmed stage only.

#### Scenario: Reading shown beside the claim's facts
- **WHEN** a claim page is built for a claim whose export carries a stage reading of early human at 0.7 with animal at 0.28
- **THEN** the page shows "Early human study" under "Evidence when first reported", with "Low confidence · 70%", that it is not confirmed and does not decide the status, and "animal study, 28%"

#### Scenario: No reading
- **WHEN** a claim page is built for a claim with no confirmed stage and no stage reading
- **THEN** the page shows no evidence stage

### Requirement: A trial reads as one row
Each trial SHALL be one row under its group's column names: how many people, what it was compared with, its main measure, its state and its identifier. What it was compared with SHALL be the names the record gives its comparator arms, at most two and a count of the rest, else the plain words for the kinds of comparator. When the claim's treatment is only a comparator in the trial, the row SHALL say what the trial tests and that the claim's treatment is what it is compared with. The main measure SHALL be the registry's own words for its first main measure; an abbreviation the site knows SHALL be said plainly under it, once per section, on the first row that uses it; the sponsor SHALL be named under it with its kind. When a trial has posted results, the date SHALL be under its state. The control that opens a row SHALL say that it opens more from the trial's record. The design SHALL be in the row's fold, once, with the registry's terms under it, and the match SHALL be said once, in the fold's notes.

#### Scenario: A finished Phase 2 trial with posted results
- **WHEN** a reader opens a claim with one finished Phase 2 trial of 83 people, placebo-controlled, that posted results on 1 Sep 2025
- **THEN** its row reads "83 people", "Placebo", its main measure, "Finished" with "Results posted 1 Sep 2025" under it, and its identifier, and the row's fold says "Assigned at random · Blinded" with the registry's terms under it

#### Scenario: The claim's treatment is only what a trial compares with
- **WHEN** a trial's record tests another drug against the claim's treatment
- **THEN** its row names the claim's treatment under "Compared with" and says "It tests <other drug>; <treatment> is what it is compared with."

#### Scenario: An abbreviation in the main measure
- **WHEN** two rows' main measures say "PFS"
- **THEN** the first says "PFS: progression-free survival, the time before the illness grew or got worse" under the registry's words, and the second does not

### Requirement: The shared stylesheet's font sizes come from one scale
Every font size in the site's shared stylesheet SHALL be one of the type scale's steps or named roles, a title's fluid size, or inherited. The steps and roles SHALL each be defined once. A build's tests SHALL fail when a rule writes a font size of its own. No text SHALL be drawn under 12 pixels.

#### Scenario: A new rule with its own size
- **WHEN** a rule is added to the shared stylesheet with `font-size: 0.9rem`
- **THEN** the site's tests fail and name the size

#### Scenario: A claim page
- **WHEN** a reader opens a claim page with every kind of section
- **THEN** its text is drawn in no more than ten sizes
