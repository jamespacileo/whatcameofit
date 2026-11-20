// A pair page's content as HTML (openspec pairs-site, design decision 3 as revised): one
// renderer for the page built ahead and the page the Worker makes on request, so the two are
// the same for the same file. Every value read from a page file goes through `escape`.
import { UNCHECKED_BYLINE } from "./notices.ts";
import type { NarrowerPair, PairTrialView, PairView } from "./pair-view.ts";
import { assertNoOutcomeVerdict } from "./trial-facts.ts";
import { formatDate } from "./timetable.ts";
import { registryDate } from "./trial-page.mjs";

const ENTITIES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Text made safe to place in HTML, between tags or in a quoted attribute. */
export function escape(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ENTITIES[character]);
}

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

/** The band at the head of the page: the pair, where it stands, and who checked it. */
export function renderPairBand(view: PairView): string {
  return [
    // The search index (Pagefind) reads only pages marked as a body, so only pair pages are
    // found by words; the topic narrows a search to one topic's pairs.
    `<section class="band record" data-pagefind-body${view.topic ? ` data-pagefind-filter="topic:${escape(view.topic)}"` : ""} aria-label="This pair and where it stands"><div class="wrap band-grid"><div class="band-main">`,
    `<nav class="crumbs" aria-label="The treatment and the condition">`,
    `<a href="/intervention/${escape(view.interventionSlug)}" data-pair-intervention>${escape(view.intervention)}</a> · `,
    `<a href="/condition/${escape(view.conditionSlug)}" data-pair-condition>${escape(view.condition)}</a></nav>`,
    `<h1 class="title">${escape(view.title)}</h1>`,
    `<p class="what-this-is" data-pagefind-ignore>A treatment and a condition, followed through the public trial records. Not medical advice. <a href="/how-it-works">How a status is set</a></p>`,
    `<p class="lede" data-pair-status="${escape(view.statusCode)}"><strong>${escape(view.status)}</strong>. ${escape(view.gloss)}. As of ${escape(formatDate(view.asOf))}, from ${escape(trialCount(view))}.</p>`,
    view.checkedByPerson ? "" : `<p class="byline" data-pair-unchecked>${escape(UNCHECKED_BYLINE[0])} ${escape(UNCHECKED_BYLINE[1])}</p>`,
    `</div></div></section>`,
  ].join("");
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
/** The line that names the same treatment's pairs for narrower conditions. */
export const NARROWER_LEAD = "Also followed for narrower conditions:";

assertNoOutcomeVerdict([NARROWER_LEAD]);

export function renderPairSheet(view: PairView, narrower: NarrowerPair[] = []): string {
  const trials = view.trials.map((trial) =>
    [
      `<article class="pair-trial" data-trial="${escape(trial.nctId)}">`,
      `<h3><a href="${escape(trial.registryUrl)}" rel="external">${escape(trial.nctId)}</a>`,
      trial.title ? `<span>: ${escape(trial.title)}</span>` : "",
      `</h3><dl>`,
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
      `</dl><ol class="pair-events">`,
      ...trial.events.map((event) => `<li data-event="${escape(event.key)}">${when(event.day, event.estimated)}: ${escape(event.label)}</li>`),
      `</ol>`,
      trial.outcomes.length ? renderOutcomes(trial.outcomes) : "",
      `</article>`,
    ].join(""),
  );
  return [
    `<div class="frame no-rail"><div class="sheet">`,
    narrower.length
      ? `<p class="note" data-pair-narrower>${escape(NARROWER_LEAD)} ${narrower
          .map((pair) => `<a href="/${escape(pair.address)}" data-narrower="${escape(pair.address)}">${escape(pair.condition)}</a>`)
          .join(", ")}</p>`
      : "",
    `<h2 class="bar sheet-title" id="why">Why this status</h2><ol class="pair-events" data-pair-explained>`,
    ...view.explainedBy.map(
      (event) => `<li data-event="${escape(event.key)}">${when(event.day, event.estimated)}: ${escape(event.label)}, ${escape(event.nctId)}</li>`,
    ),
    `</ol><h2 class="bar sheet-title" id="trials">The trials</h2>`,
    ...trials,
    `<h2 class="bar sheet-title" id="history">How the status changed</h2><ol class="pair-events" data-pair-history>`,
    ...view.history.map(
      (change) =>
        `<li>${escape(formatDate(change.on))}: ${change.before ? `${escape(change.before)} to ${escape(change.after)}` : `First set: ${escape(change.after)}`}</li>`,
    ),
    `</ol>`,
    view.otherNames.length > 0 || view.approach ? `<h2 class="bar sheet-title" id="about">About the treatment</h2>` : "",
    view.approach ? `<p>Kind of treatment: ${escape(view.approach)}.</p>` : "",
    view.otherNames.length > 0 ? `<p data-pair-names>Also known as ${view.otherNames.map(escape).join(", ")}.</p>` : "",
    view.registryChecks.length > 0
      ? `<p class="note" data-pair-checks>Registries searched: ${view.registryChecks
          .map((check) => `${escape(check.registry)}, through ${escape(formatDate(check.through))}`)
          .join("; ")}.</p>`
      : "",
    `</div></div>`,
  ].join("");
}
