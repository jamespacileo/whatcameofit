# Launch

How the site goes public and how it is passed on. Behaviour is specified in `openspec/specs/` (the `site-publishing`, `sharing`, `open-data`, `anniversaries`, `reader-contact` and `site-measurement` capabilities); this file is the operator's checklist and the reasoning behind its order.

No growth notes existed in the repository when this was written (2026-11-11). The lists of places and people below are starting points drawn from the product's own audience in `PRODUCT.md`, not from research. Replace them as real experience comes in, and record what was passed on at the end of this file.

## Before anything is announced

Nothing below is worth doing until all of these are true.

1. **Every published claim has been reviewed by a person.** A page marked "not checked by a person" must not be the first thing a stranger sees. One wrong status, widely shared, costs more than any announcement gains.
2. **The famous claims are in.** People share what they recognise. Aim for thirty to fifty claims whose headlines a general reader would remember, across several topics, before launch.
3. **The site is deployed at its final address**, and `site/site.config.mjs` holds that address. Deploy with `make deploy` (see `docs/deploy.md`): it refuses a preview export and a local address.
4. **The name is settled** in the site, the extension and the domain.
5. **The two contact addresses are set** (`suggestUrl`, `correctionsUrl`), each either a mail address or a public issue form.
6. **What the host can count is known**, and the "What is counted" section of the method page says exactly that.
7. **Advice has been taken** on the two points under "Questions to settle with advice".

## Settings for a public build

All are environment variables read when the site is built; none is a secret.

| Variable | What it sets |
|---|---|
| `SITE_URL` | The public address. Canonical links, the sitemap, link previews, the embed snippet and the extension's lookup all use it. |
| `PUBLIC_BUILD=1` | Stops the build if the address is still a local one. |
| `SUGGEST_URL` | Where "suggest a headline" leads: a `mailto:` address or a public issue form. Unset, no link is shown. |
| `CORRECTIONS_URL` | Where "report an error" leads, the same two kinds. Unset, no link is shown. |

## Order of release

1. **Quietly live.** Deploy, check five claim pages against their sources, and share with a handful of people who will say what is wrong.
2. **Extension in the stores.** It meets readers at the headline, which is where the question arises. Store review takes days; submit before the announcement.
3. **Announce** (below).
4. **Keep a rhythm.** Post one anniversary a day from `/anniversaries.xml`, by hand. Post each status change when a rebuild shows one.

## Where to say it

Go where the question "whatever happened to that?" is already being asked. Answer it with a link; do not post the same thing everywhere.

- **Communities that follow one topic closely.** Hair loss, longevity, type 1 diabetes, tinnitus, spinal injury and dental regeneration each have forums and subreddits whose members track trials themselves. A topic page is the thing to share there. Read each community's rules on self-promotion first.
- **General science readers.** Large science and futurology forums, and Hacker News with a "Show" post that leads with one plain fact from the data and a link to the method page.
- **People who cover research integrity.** Writers and outlets concerned with how science is reported, retractions and trial transparency. Send the method page and the open data, not a pitch.
- **Journalists who cover health.** Offer the embed: a status box they can place under their own follow-up story.
- **Clinicians and researchers on social networks**, who are asked "is that cure real?" by patients and relatives. The copyable sentence is made for their replies.
- **Patient organisations**, carefully and late. Only after review is complete for their topic, and with the two notices read out in the message.

## What to say, and what never to say

Say what the site does: it shows what was announced beside what the public records show now, with dates and sources.

- Lead with a claim people remember and its status, as dated facts.
- Say how a status is set: fixed rules, public registries, checked by a person.
- Link the method page whenever anyone doubts a status.

Never, in any post, reply or description:

- call a claim, a treatment, a company, a researcher or an outlet dead, failed, debunked, a scam, hype or a lie;
- say or imply that a treatment works, does not work, or is available;
- rank or compare outlets;
- answer a question about someone's own care with anything but "talk to a clinician";
- describe a quiet claim as abandoned. "No record since 2021" is the whole of what is known.

The card and the copyable sentence already hold to these rules. A post written around them must too.

## Short video

A vertical clip of twenty seconds or less: the outlet's headline in quotation marks, a beat, then the status and the two dates. The tall card (1080 by 1920) is the last frame. No voice-over opinion, no music that mocks. One claim per clip.

## Questions to settle with advice

- **Quoting titles.** Cards and pages show an outlet's title as a short, attributed quotation beside a link to the article, to identify what is tracked. Confirm this is acceptable in the jurisdictions that matter before cards are promoted.
- **Outlet icons.** The site shows each outlet's own small icon beside its name. Confirm this use, or switch every outlet to the letter tile, which needs no one's mark.

## When someone reports a wrong status

1. Thank them and ask for the source that shows it. Promise no time.
2. Check the source against the claim's records. If the record is missing, add it through the pipeline and review it; never edit a status by hand, because statuses are derived.
3. Rebuild and deploy. Embeds follow at once. A saved card image cannot be recalled: it carries the month it was checked, which says what it was true as of.
4. Reply with the claim page's address. If the status did not change, say which record it rests on.
5. If the error was the site's, say so plainly on the same channel where it was raised.

## What was passed on

Record here, with dates: where each announcement was made, what was shared from it, and what it showed about which claims to add next.

- (nothing yet)
