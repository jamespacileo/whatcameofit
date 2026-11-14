# site-publishing Specification

## Purpose
Publishes reviewed claims as a static public site on which every status is shown with the sourced evidence that produced it.

## Requirements

### Requirement: Publication gate
The export that feeds the site SHALL contain only approved claims and, for each of them, only approved evidence events. Pending and rejected items SHALL NOT appear in the export in any form.

#### Scenario: Claim with mixed events
- **WHEN** an approved claim has three approved events and two pending events
- **THEN** the export contains the claim with three events

#### Scenario: Draft claim
- **WHEN** a claim is still a pending draft
- **THEN** the export does not contain it

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
A claim page SHALL identify the evidence events that produced the current status.

#### Scenario: Status produced by one trial
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the page marks that trial's events as the reason for the status

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
Each list on the home page SHALL show ten rows at a time. Every other list of claims SHALL show 25 rows at a time. A list longer than one page SHALL have, directly under it, a control to step to the next and the previous page and a line saying which rows are shown and how many there are. A list that fits one page SHALL show no such control. Where a list can be narrowed by status, the narrowing SHALL apply to the whole list and SHALL return the reader to its first page.

Every row SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. The page in view SHALL be recorded in the page's address, and an address naming a page that does not exist SHALL show the nearest page that does.

#### Scenario: More rows than one page
- **WHEN** published claims have 104 source articles between them
- **THEN** the home page shows the ten newest, says "1–10 of 104 headlines", and the next step shows the eleventh to the twentieth

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
- **WHEN** the home page is opened with scripting off
- **THEN** every headline and every claim is listed

### Requirement: The home page offers the claims in four orders
Under the lookup, the home page SHALL offer these lists of published claims, in this order, and SHALL show one at a time, the first unless the address names another:

1. Headlines: every source article, newest first.
2. Status changes: every change from one status to another, newest first, each with the day, the status from that day and the status before it. A claim's first status is not a change.
3. Promises: every claim with a dated promise, in order of its latest promised date, earliest first, with the promise beside the status now.
4. No signal: every claim carrying the no-signal overlay, the most years first.

A list with no rows SHALL NOT be offered, except Headlines. Each list SHALL show how many rows it has. Every order SHALL be a date or a count from the record: the page SHALL NOT rank or grade claims, and SHALL NOT word a promise as kept, missed or late. The list in view SHALL be recorded in the page's address. With scripting off, every list SHALL be shown, one under the other.

#### Scenario: Lists on the home page
- **WHEN** one published claim has changed status twice, and another has a dated promise and the no-signal overlay
- **THEN** the home page offers Headlines, Status changes with two rows, Promises with one row and No signal with one row

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
- **WHEN** the home page is opened at an address naming the Status changes list
- **THEN** that list is the one shown

### Requirement: The home page's lists can be narrowed by status and by topic
Above its lists, the home page SHALL show how many published claims are at each status, on the same path a topic page shows, and SHALL let a reader pick one status. Where more than one topic is listed, it SHALL also let a reader choose one topic. A pick SHALL narrow all four lists at once to rows whose claim has that status now and is filed under that topic; both picks together SHALL narrow to rows that meet both. Each list's count SHALL be the rows left, and a list left with none SHALL say so in place of an empty table. With a topic chosen, the counts on the path SHALL be that topic's. The picks SHALL be recorded in the page's address. The counts SHALL be stated as numbers only: the page SHALL NOT rank topics or characterise the spread.

#### Scenario: Counts on the path
- **WHEN** three published claims stand at preclinical only, phase 2 and approved
- **THEN** the home page shows one at each of those places and none at the others, and a place with none cannot be picked

#### Scenario: Picking a status
- **WHEN** a reader picks phase 3
- **THEN** each list shows only rows of claims now in phase 3, and each list's count is the number of those rows

#### Scenario: Narrowing to a topic
- **WHEN** a reader chooses a topic with seven claims
- **THEN** every list shows only that topic's rows and the path shows where those seven stand

#### Scenario: A list left empty
- **WHEN** no claim in the chosen topic carries the no-signal overlay
- **THEN** the No signal list shows a count of none and says nothing is in the list for that choice

#### Scenario: One topic
- **WHEN** only one topic is listed
- **THEN** no topic choice is shown

### Requirement: Trials on the claim page
A claim page SHALL list each of the claim's trials once, under its own heading, with its registry identifier linked to the record, phase, state, the facts the export carries for it, and the score of its match. Trials SHALL be ordered furthest phase first and, within a phase, those with posted results first. Each trial event in the timetable SHALL lead to its trial. A claim with no trial SHALL show no such section.

#### Scenario: Claim with one completed Phase 2 trial
- **WHEN** a reader opens a claim whose one trial enrolled 83 participants, was randomised and has posted results
- **THEN** the page shows that trial once with its identifier, "Phase 2", its state, 83 participants, its design and its posted primary outcome

#### Scenario: Reader follows a timetable entry
- **WHEN** a reader presses a trial's "results posted" entry in the timetable
- **THEN** they can reach that trial's entry and its posted results

#### Scenario: Claim with no trial
- **WHEN** a claim has no trial
- **THEN** the page shows no trials section and no placeholder for one

### Requirement: A long list of trials opens with the furthest
When a claim has more than five trials, the claim page SHALL show the first five and SHALL keep the rest reachable on the same page without loading anything.

#### Scenario: Claim with thirty-three trials
- **WHEN** a reader opens a claim with thirty-three trials
- **THEN** five are shown, furthest phase first, and the other twenty-eight open on request

#### Scenario: Posted results among the trials not shown
- **WHEN** three of the twenty-eight trials not shown have posted results
- **THEN** the control that opens them says that three have results posted

### Requirement: The claim page counts its trials
A claim page for a claim with at least one trial SHALL state, among its facts, how many trials are on record and the largest number of participants any of them states, with whether that number is actual or planned. The statement SHALL be a count and SHALL NOT add participants across trials.

#### Scenario: Three trials, the largest of 1,200
- **WHEN** a claim has three trials and the largest states 1,200 actual participants
- **THEN** the page states three trials on record and the largest with 1,200 participants

#### Scenario: Trials that state no number
- **WHEN** none of a claim's trials states a number of participants
- **THEN** the page states the number of trials and no size

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
Above its lists, the home page SHALL show a reader with scripting on one line counting the news reports, status changes and promised dates that are dated from the day of their last visit to today, each count opening the list that holds its rows. Rows of news reports and status changes dated in that span SHALL carry the word "New". On a first visit, or where the browser keeps nothing, the line SHALL cover the last thirty days and no row SHALL be marked. When nothing is dated in the span the line SHALL say so. The day of a visit SHALL be kept in the reader's browser only and SHALL NOT be sent to the site. The line SHALL state counts only.

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
A claim page's status panel SHALL link to the page's reminders where they can be offered. The notice that a page has not been checked by a person SHALL follow the status panel, never precede it. The home page SHALL link the feed of status changes in the open, and each topic page SHALL link a feed of that topic's status changes and offer to share the page. A claim page SHALL end with a link to look up another headline, and the home page SHALL end with the link to suggest a headline when a suggestion address is configured.

#### Scenario: Following from a claim page
- **WHEN** a reader opens a claim page
- **THEN** the status panel holds a link to "Check again later", and the page's last section leads to the lookup

#### Scenario: A topic's status changes as a feed
- **WHEN** a topic has a claim whose status has changed twice
- **THEN** the topic page links a feed holding those changes, newest first

### Requirement: The home page's controls fit a phone
Below the site's one breakpoint, with scripting on, the status counts and the topic choice SHALL be reached from one control and SHALL start open when the address already narrows the lists. The four lists' tabs SHALL all be in view without scrolling sideways. Every pressed thing SHALL be at least 44 pixels tall, except a link inside a sentence.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 pixels wide
- **THEN** all four tabs are in view and the counts are behind "Narrow these lists"

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
At 375 by 812 pixels, with scripting on and nothing followed, the first row of the home page's first list SHALL start within the first screen, and all four tabs SHALL be in view. The order a keyboard moves in SHALL be the page's own.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** the first headline row starts above 812 pixels and the four tabs sit in one row

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
A claim page, and the extension's view of a claim, SHALL say when no person has checked the claim, and SHALL say nothing of the kind for a claim a person checked. A site built from an older export that calls itself a preview SHALL show on every page that it is a preview and not for publication, and SHALL ask search engines not to index any page.

#### Scenario: Unchecked claim page
- **WHEN** a reader opens the page of a claim no person checked
- **THEN** the page says it has not yet been checked by a person

#### Scenario: Checked claim in the extension
- **WHEN** the extension shows a claim a person checked
- **THEN** it carries no unchecked note

#### Scenario: Older preview export
- **WHEN** the site is built from an export that calls itself a preview
- **THEN** every page carries the preview note and a noindex tag
