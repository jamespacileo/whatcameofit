# Invite a reader back, in the open

## Why

A second design review on 2026-11-14, after `return-to-home` shipped
(`.impeccable/critique/2026-11-14T13-36-29Z__site-src-pages-index-astro.md`, 25/40),
found the machinery to bring a reader back working and the invitation missing. Follow
was one unexplained word above the answer, with its confirmation in a sentence only a
screen reader was given. The home page never told a first-time reader it would differ
next time or that following exists. The since line said "1 status change" above a tab
reading "Status changes 38", and its counts did nothing when their list was already
open. On a phone the first headline was still below the first screen. Topic and
method pages ended with nowhere to go.

The operator chose, on 2026-11-14: explain and confirm Follow first; a count in the
since line narrows its list; on a phone compress what is under the opening band and
leave the band alone; cover every finding.

## What changes

- **Follow, explained and confirmed.** Under a claim's status, and again beside its
  reminders, Follow sits with a sentence: what it does and that it is kept in the
  browser. Once followed, the sentence says so and links to the list. The pill at the
  top stays. A reader who follows a claim and last saw it at another status is told on
  the claim page: "Changed. When you last looked: X. Now: Y."
- **Keep up.** Under the home page's lists: for a reader who follows nothing, what
  following and the last-visit day are; for everyone, "Subscribe to status changes".
- **The since line.** Each count stands beside its list's total ("7 of 104 news
  reports, none of 38 status changes"), none is said for status changes, a count
  narrows its list to the rows dated since with "Show all" to undo, and a changed
  followed claim is counted in the line.
- **Phone.** The since line and the lists are drawn ahead of the tally; the tabs fit
  one row; the control that narrows sits under them. The first headline starts at 784
  pixels of an 812 pixel screen, from 989.
- **Next steps.** A topic page ends with "Another headline?" and, where configured,
  the link to suggest one; its rows first reported since the reader's last visit carry
  "New". The method page gains "Ways to keep up".
- **Small repairs.** A pager step that leads nowhere is passed over by the Tab key.
  Pills have a boundary that can be seen on white. The two pagers that shared a name
  are named apart. The fold for another site's page says who it is for.

## Not changed, on purpose

- The opening band, at the operator's word.
- "No record found for … We say that a lot.", still the operator's to decide.
- No link to install the extension: it has no store listing to link to.
