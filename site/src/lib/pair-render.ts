// A pair page's content as HTML (openspec pairs-site, design decision 3 as revised): one
// renderer for the page built ahead and the page the Worker makes on request, so the two are
// the same for the same file. Every value read from a page file goes through `escape`.
import { band, bandTitle, crumbs, escape, eventList, followedLine, sheet, sheetHeading, statusWords } from "./blocks.ts";
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

/** The band at the head of the page: the pair, where it stands, and who checked it. */
export function renderPairBand(view: PairView): string {
  // The search index (Pagefind) reads only pages marked as a body, so only pair pages are
  // found by words; the topic narrows a search to one topic's pairs.
  return band(` data-pagefind-body${view.topic ? ` data-pagefind-filter="topic:${escape(view.topic)}"` : ""} aria-label="This pair and where it stands"`, [
    crumbs("The treatment and the condition", [
      { href: `/intervention/${view.interventionSlug}`, label: view.intervention, data: "data-pair-intervention" },
      { href: `/condition/${view.conditionSlug}`, label: view.condition, data: "data-pair-condition" },
    ]),
    bandTitle(view.title),
    followedLine("A treatment and a condition,", "what-this-is"),
    `<p class="lede" data-pair-status="${escape(view.statusCode)}">${statusWords(view.status, view.gloss)} As of ${escape(formatDate(view.asOf))}, from ${escape(trialCount(view))}.</p>`,
    view.checkedByPerson ? "" : `<p class="byline" data-pair-unchecked>${escape(UNCHECKED_BYLINE[0])} ${escape(UNCHECKED_BYLINE[1])}</p>`,
  ]);
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

/** The body of the page: why the status, the trials, the history and the treatment. */
/** How many trials a pair has before its page shows them as a table rather than one entry each. */
export const TRIALS_TABLE_FROM = 3;

/** The line that names the same treatment's pairs for narrower conditions. */
export const NARROWER_LEAD = "Also followed for narrower conditions:";

assertNoOutcomeVerdict([NARROWER_LEAD]);

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
    fact("Results", trial.resultsPosted ? "Posted on the registry" : "None posted"),
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
    ...trials,
    sheetHeading("How the status changed", "history"),
    eventList(
      " data-pair-history",
      view.history.map(
        (change) =>
          `<li>${escape(formatDate(change.on))}: ${change.before ? `${escape(change.before)} to ${escape(change.after)}` : `First set: ${escape(change.after)}`}</li>`,
      ),
    ),
    view.otherNames.length > 0 || view.approach ? sheetHeading("About the treatment", "about") : "",
    view.approach ? `<p>Kind of treatment: ${escape(view.approach)}.</p>` : "",
    view.otherNames.length > 0 ? `<p data-pair-names>Also known as ${view.otherNames.map(escape).join(", ")}.</p>` : "",
    view.registryChecks.length > 0
      ? `<p class="note" data-pair-checks>Registries searched: ${view.registryChecks
          .map((check) => `${escape(check.registry)}, through ${escape(formatDate(check.through))}`)
          .join("; ")}.</p>`
      : "",
  ]);
}
