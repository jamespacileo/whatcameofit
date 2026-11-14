# Give a reader a reason and a way to come back

## Why

A design review on 2026-11-14 (`.impeccable/critique/2026-11-14T12-41-24Z__site-src-pages-index-astro.md`)
found that the site answers a reader's question and then lets them go. The home page
could not say what had changed since a reader last looked. The ways back (a calendar
reminder, the feeds) sat at the foot of a claim page, in the page's head only, or
nowhere. On a phone a first-time reader met 23 controls and more than a screen before
the first headline, and two of the four lists were off the side of the screen.

The operator chose, on 2026-11-14: fix the return to the home page first; keep a
reader's followed claims and the day of their last visit in their own browser; keep
Headlines as the first list with a summary above it; cover every finding.

## What changes

- **Since your last visit.** Above the home page's lists, one line says what is dated
  since the reader's last visit (news reports, status changes, promised dates reached),
  and each count opens its list. Rows dated since then carry the word "New". On a
  first visit, or where the browser keeps nothing, the line covers the last 30 days
  and nothing is marked new.
- **Following.** A claim page has a "Follow" pill beside "Share". Followed claims are
  listed at the top of the home page, a changed status first with "Was: X. Now: Y.".
  This is the extension's "Following" list, on the site.
- **Both are kept in the reader's browser only.** Nothing is sent to the site. The
  privacy page says so.
- **Ways back beside the answer.** The status panel links to "Check again later". The
  notice that a page was put together by software sits under the status, not above it.
  The home page's status changes and each topic's are linked as feeds in the open.
- **A page ends on a next step.** A claim page ends with "Another headline?" and a
  link to the lookup; the home page ends with "Suggest a headline", which leaves the
  opening band.
- **Passing it on.** Copy link joins the first row of pills; the networks open on
  request. A topic page can be shared.
- **Phone.** The counts and the topic choice open from one control; the four tabs sit
  two by two; pressed things are at least 44 pixels tall.
- **Small repairs.** The first page's "Previous" keeps its contrast. A skipped
  cross-fade is no longer reported as an error. Files named by their content are
  cached for a year.

## Not changed, on purpose

- "No record found for … We say that a lot." The review found it misjudged for a
  reader asking about a relative's condition. `DESIGN.md` lists it as the site's own
  dry wording, chosen by the operator; it is left for the operator to decide.
- No "cite this record" line: the sentence under "Pass it on" already carries the
  status, the month it was checked and the page's address.
- No email alerts. Subscriber email is Phase 2.
- No ranking by what readers follow or look up: the site is never told.
