// A pair page's content as HTML (openspec pairs-site, design decision 3 as revised): one
// renderer for the page built ahead and the page the Worker makes on request, so the two are
// the same for the same file. Every value read from a page file goes through `escape`.
import { band, bandTitle, crumbs, escape, eventList, followedLine, sectionList, sheet, sheetHeading, standingCard } from "./blocks.ts";
import { recordStrip, stripKey, stripKinds, stripOf } from "./record-strip.ts";
import { UNCHECKED_BYLINE } from "./notices.ts";
import type { NarrowerPair, PairTrialView, PairView } from "./pair-view.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";
import { formatDate } from "./timetable.ts";
import { trialsTable } from "./trials-table.ts";
import { registryDate } from "./trial-page.mjs";

export { escape };

const trialCount = (view: PairView) =>
  view.trials.length === 1 ? "1 registered trial" : `${view.trials.length} registered trials`;

/** The line a search result and a link preview give for the page. */
export function pairDescription(view: PairView): string {
  return `${view.status}: where the public records show ${view.intervention} for ${view.condition.toLowerCase()} stands, from ${trialCount(view)}.`;
}

/** A registry date as precise as the registry gave it: a day, or a month and year ("Nov 2015"),
 * or a year. A missing day is never filled in. */
const registryDay = (value: string) => (/^\d{4}-\d{2}-\d{2}$/.test(value) ? formatDate(value) : (registryDate(value) ?? value));

const when = (day: string, estimated: boolean) => `${escape(registryDay(day))}${estimated ? " (expected)" : ""}`;

/** An event's date as a page gives it: as precise as the registry gave it, and "(expected)"
 * when the registry expects it rather than records it. HTML. */
export const eventWhen = when;

/** The day of the latest event the registries record for the pair's trials: an expected date
 * is not a record yet, and the day a status was worked out is never given as a record's. */
function latestRecord(view: PairView): string | null {
  return view.trials.flatMap((trial) => trial.events).filter((event) => !event.estimated).map((event) => event.day).sort().at(-1) ?? null;
}

/** The band at the head of the page: the pair and who checked it, and beside them the card
 * that says where it stands (lib/blocks.ts, standingCard). The card holds the status once;
 * the band's own lines no longer repeat it as a sentence. */
export function renderPairBand(view: PairView): string {
  const latest = latestRecord(view);
  const posted = view.trials.filter((trial) => trial.resultsPosted).length;
  // The search index (Pagefind) reads only pages marked as a body, so only pair pages are
  // found by words; the topic narrows a search to one topic's pairs.
  return band(
    ` data-pagefind-body${view.topic ? ` data-pagefind-filter="topic:${escape(view.topic)}"` : ""} aria-label="This pair and where it stands"`,
    [
      crumbs("The treatment and the condition", [
        { href: `/intervention/${view.interventionSlug}`, label: view.intervention, data: "data-pair-intervention" },
        { href: `/condition/${view.conditionSlug}`, label: view.condition, data: "data-pair-condition" },
      ]),
      bandTitle(view.title),
      followedLine("A treatment and a condition,", "what-this-is"),
      view.checkedByPerson ? "" : `<p class="byline" data-pair-unchecked>${escape(UNCHECKED_BYLINE[0])} ${escape(UNCHECKED_BYLINE[1])}</p>`,
    ],
    standingCard(
      view.statusCode,
      view.status,
      view.gloss,
      [
        latest ? `Latest record <a href="#trials">${escape(registryDay(latest))}</a>` : "",
        `<a href="#trials">${escape(trialCount(view))}</a>${posted ? `, ${posted} with results posted` : ""}`,
        `Status set by rule, ${escape(formatDate(view.asOf))}. <a href="#why">Why this status</a>`,
      ],
      ` data-pair-status="${escape(view.statusCode)}"`,
    ),
  );
}

function fact(label: string, value: string | null): string {
  return value === null ? "" : `<dt>${escape(label)}</dt><dd>${value}</dd>`;
}

/** Said once above a trial's posted results. */
export const RESULTS_NOTE =
  "The numbers the trial's sponsor posted to the registry, as written there. The registry record says what each measure runs from and to.";

assertNoOutcomeVerdict([RESULTS_NOTE, "Posted results", "Group", "Analysed", "Value"]);

function renderOutcomes(outcomes: PairTrialView["outcomes"]): string {
  return [
    `<section class="pair-results" data-results><h4>Posted results</h4><p class="note">${escape(RESULTS_NOTE)}</p>`,
    ...outcomes.map((outcome) =>
      [
        `<div class="pair-outcome" data-outcome>`,
        `<p><strong>${escape(outcome.title)}</strong></p>`,
        `<p class="note">${[outcome.kind, outcome.measure, outcome.timeFrame].filter(Boolean).map(escape).join(" · ")}</p>`,
        `<table><thead><tr><th scope="col">Group</th><th scope="col">Analysed</th><th scope="col">Value</th></tr></thead><tbody>`,
        ...outcome.rows.map(
          (row) =>
            `<tr><th scope="row">${escape(row.group)}${row.part ? `<br><span class="note">${escape(row.part)}</span>` : ""}</th><td>${escape(row.analysed ?? "")}</td><td><span class="pair-value">${escape(row.estimate)}</span>${row.spread === null ? "" : ` <span class="pair-spread">(${escape(row.spread)})</span>`}</td></tr>`,
        ),
        `</tbody></table>`,
        outcome.comparisons.length ? `<ul class="pair-comparisons">${outcome.comparisons.map((text) => `<li data-comparison>${escape(text)}</li>`).join("")}</ul>` : "",
        `</div>`,
      ].join(""),
    ),
    `</section>`,
  ].join("");
}

/** Said once above a trial's posted adverse events. The registry counts an event whether or
 * not it is thought related to the treatment (its results data elements, "Adverse Event
 * Information", https://clinicaltrials.gov/policy/results-definitions), and the page says so,
 * since a count beside a treatment's name is otherwise read as the treatment's doing. */
export const HARMS_NOTE =
  "People who had an unwanted medical event during the trial, as the sponsor posted them to the registry: the number affected, of those at risk. An event is counted whether or not the treatment caused it.";
/** For groups the bundle joins to no arm. */
export const HARMS_GROUPS_NOTE = "The registry record names each group.";
const HARMS_COLUMNS = ["Deaths, any cause", "Serious events", "Other events"];
const NOT_POSTED = "Not posted";

assertNoOutcomeVerdict([HARMS_NOTE, HARMS_GROUPS_NOTE, NOT_POSTED, "Adverse events", "Serious events by name", "Event", ...HARMS_COLUMNS]);

function renderHarms(harms: NonNullable<PairTrialView["harms"]>, registryUrl: string): string {
  const count = (text: string | null) => `<td>${escape(text ?? NOT_POSTED)}</td>`;
  const notes = [
    HARMS_NOTE,
    // The registry's time frame is free text and may end with its own full stop.
    harms.timeFrame ? `Counted over: ${harms.timeFrame.replace(/\.\s*$/, "")}.` : "",
    // The registry's threshold is a share of a group, in per cent, that an other event must pass to be listed.
    harms.threshold !== null ? `Other events are listed in the record only above ${harms.threshold}% of a group.` : "",
  ].filter(Boolean);
  return [
    `<section class="pair-results pair-harms" data-harms><h4>Adverse events</h4><p class="note">${escape(notes.join(" "))}`,
    harms.named ? "" : ` <a href="${escape(registryUrl)}" rel="external" data-harms-groups>${escape(HARMS_GROUPS_NOTE)}</a>`,
    `</p><div class="pair-outcome"><table><thead><tr><th scope="col">Group</th>${HARMS_COLUMNS.map((label) => `<th scope="col">${escape(label)}</th>`).join("")}</tr></thead><tbody>`,
    ...harms.groups.map((group) => `<tr data-harm-group><th scope="row">${escape(group.group)}</th>${count(group.deaths)}${count(group.serious)}${count(group.other)}</tr>`),
    `</tbody></table></div>`,
    harms.seriousEvents.length
      ? [
          // Closed until asked for: a large trial lists hundreds of serious events.
          `<details class="pair-outcome" data-serious-events><summary>Serious events by name (${harms.seriousEvents.length})</summary>`,
          `<table><thead><tr><th scope="col">Event</th>${harms.groups.map((group) => `<th scope="col">${escape(group.group)}</th>`).join("")}</tr></thead><tbody>`,
          ...harms.seriousEvents.map(
            (event) =>
              `<tr data-serious-event><th scope="row">${escape(event.term)}${event.organSystem ? `<br><span class="note">${escape(event.organSystem)}</span>` : ""}</th>${event.counts.map(count).join("")}</tr>`,
          ),
          `</tbody></table></details>`,
        ].join("")
      : "",
    `</section>`,
  ].join("");
}

/** The body of the page: why the status, the trials, the history and the treatment. */
/** How many trials a pair has before its page shows them as a table rather than one entry each. */
export const TRIALS_TABLE_FROM = 3;

/** The line that names the same treatment's pairs for narrower conditions. */
export const NARROWER_LEAD = "Also followed for narrower conditions:";

assertNoOutcomeVerdict([NARROWER_LEAD]);

/** Said beside the record strip: what it shows and what it does not. */
export const RECORDS_NOTE = "A stretch with no mark is time with no dated event, not an ending.";

assertNoOutcomeVerdict([RECORDS_NOTE]);

/** A trial's record as the page gives it: its facts, its dated events and its posted results.
 * The trial's own heading is the caller's (a pair page's article, a trials table's row). */
export function trialRecord(trial: PairTrialView): string {
  return [
    `<dl>`,
    fact("State", escape(trial.state)),
    fact("Phase", trial.phases && escape(trial.phases)),
    fact("People", trial.participants && escape(trial.participants)),
    fact("Started", trial.start && escape(registryDay(trial.start))),
    fact("Primary completion", trial.primaryCompletion && escape(registryDay(trial.primaryCompletion))),
    fact(
      "Arms",
      trial.arms.length
        ? trial.arms.map((arm) => (arm === trial.pairArm ? `<strong>${escape(arm)}</strong>` : escape(arm))).join(", ")
        : null,
    ),
    fact("Why it stopped, in the record", trial.whyStopped && escape(trial.whyStopped)),
    fact("Results", `<span data-results-state>${escape(trial.results.words)}${trial.results.asOf ? `, as of ${escape(formatDate(trial.results.asOf))}` : ""}</span>`),
    fact(
      "Papers",
      trial.papers.length
        ? trial.papers
            .map((paper) => (paper.url ? `<a href="${escape(paper.url)}" rel="external" data-paper="${escape(paper.id)}">${escape(paper.label)}</a>` : `<span data-paper="${escape(paper.id)}">${escape(paper.label)}</span>`))
            .join(", ")
        : null,
    ),
    `</dl>`,
    eventList("", trial.events.map((event) => `<li data-event="${escape(event.key)}">${when(event.day, event.estimated)}: ${escape(event.label)}</li>`)),
    trial.outcomes.length ? renderOutcomes(trial.outcomes) : "",
    trial.harms ? renderHarms(trial.harms, trial.registryUrl) : "",
  ].join("");
}

export function renderPairSheet(view: PairView, narrower: NarrowerPair[] = []): string {
  // From a few trials up, the trials read across as a table (lib/trials-table.ts), each row
  // opening to the same record; fewer stay as entries of their own. Only the one used is made.
  const asTable = view.trials.length >= TRIALS_TABLE_FROM;
  const trials = asTable ? [trialsTable(view.trials)] : view.trials.map((trial) =>
    [
      `<article class="pair-trial" data-trial="${escape(trial.nctId)}">`,
      `<h3><a href="${escape(trial.registryUrl)}" rel="external">${escape(trial.nctId)}</a>`,
      trial.title ? `<span>: ${escape(trial.title)}</span>` : "",
      `</h3>`,
      trialRecord(trial),
      `</article>`,
    ].join(""),
  );
  const strip = stripOf(view);
  const about = view.otherNames.length > 0 || view.approach;
  // The page's sections beside the sheet, as the claim pages had them (DESIGN.md, "Section
  // list"): each by name, the trials with their count.
  const rail = sectionList("On this page", [
    { id: "why", name: "Why this status" },
    { id: "trials", name: "The trials", count: view.trials.length },
    { id: "history", name: "How the status changed" },
    ...(about ? [{ id: "about", name: "About the treatment" }] : []),
  ]);
  return sheet([
    narrower.length
      ? `<p class="note" data-pair-narrower>${escape(NARROWER_LEAD)} ${narrower
          .map((pair) => `<a href="/${escape(pair.address)}" data-narrower="${escape(pair.address)}">${escape(pair.condition)}</a>`)
          .join(", ")}</p>`
      : "",
    sheetHeading("Why this status", "why"),
    eventList(
      " data-pair-explained",
      view.explainedBy.map((event) => `<li data-event="${escape(event.key)}">${when(event.day, event.estimated)}: ${escape(event.label)}, ${escape(event.nctId)}</li>`),
    ),
    sheetHeading("The trials", "trials"),
    // Where the trials' dated events fall, on one axis to the last check, with its key
    // (lib/record-strip.ts). No strip without a day the registries were last checked.
    strip ? `<div class="pair-strip" data-pair-strip><p class="note">Trial events by date. ${RECORDS_NOTE}</p>${recordStrip(view)}${stripKey(stripKinds(strip))}</div>` : "",
    ...trials,
    sheetHeading("How the status changed", "history"),
    eventList(
      " data-pair-history",
      view.history.map(
        (change) =>
          `<li>${escape(formatDate(change.on))}: ${change.before ? `${escape(change.before)} to ${escape(change.after)}` : `First set: ${escape(change.after)}`}</li>`,
      ),
    ),
    about ? sheetHeading("About the treatment", "about") : "",
    view.approach ? `<p>Kind of treatment: ${escape(view.approach)}.</p>` : "",
    view.otherNames.length > 0 ? `<p data-pair-names>Also known as ${view.otherNames.map(escape).join(", ")}.</p>` : "",
    view.registryChecks.length > 0
      ? `<p class="note" data-pair-checks>Registries searched: ${view.registryChecks
          .map((check) => `${escape(check.registry)}, through ${escape(formatDate(check.through))}`)
          .join("; ")}.</p>`
      : "",
  ], rail);
}
