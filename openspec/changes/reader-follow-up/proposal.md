# Proposal

Status: draft for the operator to accept, change or drop. Nothing here is built.

## Why

A reader checks a headline once and leaves. The product's own promise is "we will check again", but the reader has no way to come back at the right moment, and the site has no way to tell them a status moved. On 2026-11-13 the operator asked to explore reminders, updates and a list of recently checked articles and posts as ways to bring readers back and give them something to pass on.

Email alerts are Phase 2 in `SPEC.md` and need scheduled polling, an email provider and double opt-in. This change gives readers the same three things without collecting anything about them.

## What Changes

- **Remind me.** A claim page offers a calendar file for a chosen moment: when the latest dated promise falls due, in six months, in one year, or on the next anniversary of the first report. The file is made in the reader's browser and links back to the claim page. The extension offers the same choices and shows a notification when the moment comes.
- **Follow.** In the extension a reader can follow a claim. The followed list is kept in the browser. When the extension next refreshes the site's lookup file and a followed claim's status has changed, it shows a notification and marks the claim in the popup.
- **Recently checked.** The extension keeps the last ten pages the reader checked, in the browser only: the page title, the outlet, the date checked and the answer. One match opens the claim page, several matches open the list of candidates, and each entry can also open the original page. The reader can clear the list.
- **Status changes feed.** The site publishes a feed of status changes for all published claims and one per claim, beside the existing anniversaries feed.
- **Privacy page.** It says what the extension keeps in the browser, that none of it is sent to the site, and how to clear it.

Not in this change: email alerts, web push, a public list of what other readers checked (live lookup results are unreviewed and reach only the reader who asked), popularity counts, and the explainer video. Each is its own change.

## Capabilities

### New Capabilities

- `reader-follow-up`: reminders, followed claims, the reader's own recently checked list, and the status changes feed.

### Modified Capabilities

None. `site-measurement` already forbids storing an identifier for measurement; what this change stores is the reader's own list, kept for the reader and never sent.

## Impact

- **Site:** a calendar-file control on the claim page (`site/src/pages/[slug].astro`), two feed routes beside `anniversaries.xml.ts`, and new wording on `privacy.astro`. The calendar file and the privacy wording need no change to the export. The status changes feed needs each claim's earlier statuses with their dates. The export carries the dated evidence events and the current status; whether it must also carry the status history is not yet checked, and status is derived only in the pipeline, never on the site.
- **Extension:** two new permissions, `alarms` and `notifications`. Three new keys in `storage.local`: followed claims, reminders, recently checked. A new popup view for the list. The extension still never sends a page's address.
- **Wording:** all new strings live with the site and are copied at build, as the answer wording is now. A notification names the claim and its status label and nothing else: no verdict, no advice.
- **Stores:** new permissions mean a new review in the Chrome Web Store and a rebuilt Safari project.
- **Risk:** a status change is only noticed when the lookup file is refreshed, so a notification can be a day late. The feed carries the exact date.
