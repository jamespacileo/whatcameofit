# Design

## The reader's browser is the only memory

Two entries in local storage, read and written only by the page:

- `home-visit`: the day of this visit and of the one before, as dates. A second look
  on the same day keeps the earlier "previous", so what is marked new does not vanish
  on a reload.
- `following`: per claim, its headline, its status in words when the reader last
  opened it, and the day they began following.

Nothing is sent: the site has no endpoint that could receive either. Where storage is
refused (a private window), the Follow pill is not shown and the summary line falls
back to a fixed thirty days.

"Since" is by the date a record carries, not the day the site learned of it: the page
holds no such day. A report published before the reader's last visit and added after
it is not marked new. The line says "dated since" in its counts' meaning and the word
"New" marks a row's own date.

## A followed claim's status is compared in words

The home page reads the status now from `lookup.json`, which already carries each
claim's status label. Comparing labels, not codes, keeps the site and the extension on
one vocabulary and needs no new field. Opening the claim page is seeing the status, so
the kept label is brought up to date there, as the extension does.

## Phone: one control in place of eight

Below 40rem the status counts and the topic choice sit behind "Narrow these lists".
They start open when the address already narrows the lists, so a narrowed list is
never unexplained. Hidden by `@media (scripting: enabled)`: with scripting off
everything is in view, as before.

The opening band is the operator's own choice (2026-11-13) and is left alone, so the
first headline is still below the first phone screen (989 px, from 1070). What changed
is what stands between: 10 controls, from 23, and the summary line is on that screen.
