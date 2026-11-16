# Design

## Context

See `proposal.md` for motivation. This document records the assistant's recommendation of 2026-11-16 and the reasoning behind it. What shapes it:

- The unit is a claim, and the export already carries, per published claim: its status with history (`ExportedStatus`, `ExportedStatusChange`), its articles with dates, its organisations with roles and registry identity (`ExportedOrganisation`), its approach and its health area. The two views proposed here need no new stored fact; they are computed from the export.
- The data file is offered under CC BY 4.0 (`LICENSE-DATA`). Anyone, including a company, may already reuse it for money with credit. A paid offer cannot rest on withholding it.
- ChEMBL-derived facts are share-alike and are kept out of the data file (ADR 0002). They stay out of anything sold.
- "Accuracy is the brand, and it is shown, not gated" (ADR 0001). A paid tier that shows more of the truth than the public site would contradict it.
- Status wording is the site's alone and carries no verdict. A claim with no trial on record is not "available", "unlicensed", "abandoned" or "an opportunity"; the tracker does not know any of those things.
- The vendor names below are from the assistant's memory and were not checked against current sources on the day. Task 1.1 checks them.

## Goals / Non-Goals

**Goals:**

- Record the recommendation and the alternatives so the operator can accept, change or reject it.
- Put a validation gate before any build.
- Keep the public site free and the same in substance whether or not anyone pays.

**Non-Goals:**

- Pricing, contracts, invoicing or a customer portal.
- Selling to a large company directly as the first step.
- Any score, ranking or prediction of which research is worth pursuing.
- Any use of readers' lookups in a paid offer.

## Decisions

### 1. Lead with the early-stage list

Pipeline databases (Citeline Pharmaprojects, Clarivate Cortellis) begin where a sponsor files or announces a programme. Scouting marketplaces (Inpart, Wellspring) hold what institutions choose to list. Neither starts from public reports, so neither holds a reported result that was never followed by a registered trial. The tracker's two earliest statuses, with the years since first report and the organisations named, are exactly that set, and the tracker already computes them.

Alternatives considered:

| Idea | Buyer | Why not first |
|------|-------|---------------|
| Media-against-evidence monitor | Medical affairs, communications | Closest to what the site already shows, but it competes with media monitoring (Meltwater, Signal AI) and commercial monitoring of news in the UK is a licensed activity (NLA, CLA). Needs legal reading before anything else. |
| Reader demand in aggregate | Patient engagement, recruitment | `lookup-demand` keeps counts so the operator can choose claims, and promises readers nothing more is done with them. Selling them breaks that promise. Not recommended at all without a new decision and new wording on the privacy page. |
| Answer support for medical information teams | Medical information, field medical staff | A real need, but it sits close to medical advice and inside a regulated process. Later, if ever. |
| Results-disclosure tracker | Transparency, compliance | FDAAA TrialsTracker is free and TrialScope is established. No edge. |
| Research funders and charities | Impact teams | Easier to sell to than a large company and a good second market ("what came of what we funded"). Different buyer, same data. Kept as the fallback if group 1 finds no pull from scouts. |
| University press and technology transfer offices | Communications, licensing | The supply side of the early-stage list. Worth talking to in group 1; not a first customer. |
| Investors | Small-cap biotech analysts | Pulls the product toward verdicts and forecasts. Not recommended. |

### 2. Translation counts are counts

For claims first reported in year Y, the view states how many stand at each status today and how many claims were counted. It also states how the claims were gathered, because the tracker's claims are chosen (seed, backfills, topics, reader lookups), not sampled. A percentage from 84 chosen claims is not a rate of anything. The view therefore gives counts with their denominators, shows no percentage for a group under a minimum size the operator sets, and never uses "probability", "likelihood" or "success rate". Success-probability products (Biomedtracker, Intelligencia) start at Phase 1 and are a different thing; the tracker should not appear to compete with them.

### 3. Both views are public; the service is what is paid for

The early-stage list and the translation counts go on the public site and into public data files under CC BY 4.0, like everything else. What a customer pays for:

- **Coverage on request.** The operator backfills a health area the customer names. Every claim found is prepared, audited and published by the usual rules.
- **Change feed and watch lists.** A keyed route that returns what changed since a date, and the same for a list of claims the customer names.
- **Support.** Answers about method, and a commitment on how soon registries are rechecked.

Alternative considered: a private dataset richer than the public one. Rejected: it gates accuracy, and CC BY data cannot be re-closed in any case.

Alternative considered: licence the data to an aggregator (Clarivate, Citeline, AlphaSense) instead of selling to end customers. Not rejected; it avoids each customer's procurement and is worth raising in group 1. It changes nothing in what is built.

### 4. Paying changes no record

A customer cannot have a claim added out of turn without it being published, removed, reworded, re-scored or held back. A customer who thinks a record is wrong uses the route any reader uses, and the operator archives or does not by the same rule. Funded coverage of a health area is disclosed on the method page by area and date, without naming the customer unless the customer agrees. This is the condition under which taking industry money does not cost the site its standing; if the operator does not want to disclose, the recommendation is not to take the money.

### 5. The first buyers are small

A large company's vendor onboarding (security questionnaire, supplier registration, legal review) commonly takes six to twelve months and assumes a company with insurance and a named security contact. The recommended first conversations are with competitive-intelligence consultancies, scouting teams at mid-size biotechs and technology transfer offices, who can buy on a card or a short agreement.

### 6. One health area, deep

At 84 published claims, 58 of them from 2026, no list is long enough to be worth a scout's time. The offer needs several hundred claims in one area going back at least a decade, which the backfill machinery (`file-based-backfill`, `social-link-backfill`, `growth-loops` group 8) already produces. Which area is the operator's choice; group 1 asks the people who would pay.

## Risks / Trade-offs

- [Industry money weakens trust in a site whose subject is industry claims] → Decision 4: no record changes, coverage funding disclosed, public and paid identical in substance. A decision record states it before the first invoice.
- [The list is read as a list of things to buy, or as a judgement that work stopped] → The site words the list. The neutral-wording check that fails the build on verdict wording covers the new pages. The list states "no trial record found" and the years since first report, and says on the page what the tracker does not know: licensing, funding, unpublished work, trials in registries not yet asked.
- [Counts are quoted as rates] → Decision 2: denominators always, no percentage under the minimum, how claims were gathered stated beside the numbers.
- [A source's terms forbid paid reuse] → Task 2.1 reads each source's terms for this use before any build and records the answer, dated, in `docs/sources.md`. A source that forbids it is left out of the keyed route.
- [A customer contact is personal data the project does not hold today] → Open question 3. Nothing is collected until answered.
- [Nobody wants it] → Group 1 is five conversations and costs nothing but time. The change is abandoned or redirected to funders if they find no pull.
- [Coverage on request skews what the tracker covers] → Disclosed (decision 4). The operator may also refuse an area.

## Open Questions

For the operator. None is answered yet.

1. Will the site take money from the industry it reports on at all? If yes, is the disclosure in decision 4 acceptable?
2. Is coverage of a health area at a customer's request acceptable, given every claim found is published?
3. What may be held about a customer: an organisation's name and one contact address, and under what retention? This is beyond "subscriber emails are the only personal data".
4. Which health area first, if group 1 does not settle it?
5. Should the early-stage list and translation counts be built for the public site regardless of whether anyone pays? They may be worth having as pages in their own right.
6. End customers, or a licence to an aggregator?
