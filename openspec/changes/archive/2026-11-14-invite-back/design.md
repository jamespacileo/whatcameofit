# Design

## Follow is offered where it is understood

Three controls, one state. The pill at the top keeps Follow on the first screen. The
offer under the status is where a reader has the answer and can be told what following
is; the offer beside the reminders is where the other ways back are. Each offer's
sentence is the confirmation: it changes from what following does to "You follow this
claim" with a link to the list, so a sighted reader is told what a screen reader is.

## A change is confirmed where the reader lands

The home page says a followed claim has changed. Opening the claim brings the kept
status up to date, so without a word there the change would vanish as it was read.
The claim page compares before it updates and says the earlier status once.

## Counts beside totals

"1 status change" above "Status changes 38" made a reader reconcile two systems. Each
count now names its list's total. Status changes are what only this site has, so none
of them is said; a list with none of the others is left out, to keep the line short.

A count narrows its list with a third mark on the rows, `data-out-since`, beside the
status and topic marks. The pager and the tab's count already read any such mark.

## Phone: the order drawn, not the order of the page

Below 40rem the page's own order is kept for a keyboard and a screen reader, and CSS
`order` draws the since line, the tabs, the narrowing control and the list ahead of
the tally. The tabs drop their counts to fit one row and wrap where they cannot. The
list's heading is hidden from the eye there, since the tab above names the list.

The band and masthead take 585 of 812 pixels. With everything under them compressed
the first headline starts at 784: on the first screen, by 28 pixels.
