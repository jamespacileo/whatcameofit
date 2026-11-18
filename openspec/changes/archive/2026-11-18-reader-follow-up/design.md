# Design

## Decisions

**No server and no account.** Email follow is Phase 2 and needs polling that does not exist yet. A calendar file, local alarms and a comparison against the lookup file the extension already fetches give the reader the same result today with no personal data.

**The lookup file is the only signal.** The extension already refreshes `lookup.json`, which carries each claim's status code and `place`. Follow compares those two fields with the pair last seen. No new endpoint, and nothing tells the site which claims a reader follows.

**Calendar file over web push.** A push subscription is an identifier held by the site. A calendar file is held by the reader and works in every browser, with no extension.

**Recently checked stays private.** The lookup service stores nothing a reader sends, and the extension never sends a page's address. A public list of other readers' checks would break both rules and would publish unreviewed search results. The list is therefore the reader's own, capped at ten, with a clear control.

**The payoff is the card.** A reminder or a change notification opens the claim page, where the card image and the sentence to copy already sit. Bringing the reader back at a moment worth sharing is what this change adds to sharing; it adds no new share surface.

## Wording

- Reminder choices: "When the promise falls due (2027)", "In six months", "In a year", "On the anniversary (31 March)".
- Reminder notification: "You asked us to remind you." then the claim headline and status label.
- Change notification: claim headline, then "Was: Trial registered. Now: Phase 1 trial."
- Empty list: "Nothing checked yet."

Dry wording is allowed in the extension's own chrome only, never beside a status and never about a condition, as `DESIGN.md` already rules.

## Open questions for the operator

1. Answered 2026-11-13: a change into no signal notifies too, worded plainly ("Now: no signal"), never as dead or abandoned.
2. Answered 2026-11-13: keep ten recently checked entries, and no cap on followed claims.
3. Answered 2026-11-13: yes. A linked report the site does not track gets "Check again later" with six months and a year. The event links to the report and says where to paste it; the file is made in the browser and the link is sent nowhere.

4. Answered 2026-11-13: the export carries a claim's current status only (`ExportedStatus`: code, no-signal years, the events that explain it). The feed therefore needs a status history from the pipeline: `status/rules.py` is pure, so the history is the same derivation run on the approved events up to each event's date, keeping the dates where the status changes. That adds a field to the export, so `site/export.schema.json` and `site/data/seed-export.json` are regenerated. Still to decide: build it inside this change or as its own.

## Risks

- New extension permissions (`alarms`, `notifications`) show a new prompt on update and need store review.
- A status change is noticed on the next lookup refresh, which can be up to a day after publication.
- Safari limits background alarms; the Safari build may need to check due reminders when the popup opens.
