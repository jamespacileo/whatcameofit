// A pair page's content as HTML (openspec pairs-site, design decision 3 as revised): one
// renderer for the page built ahead and the page the Worker makes on request, so the two are
// the same for the same file. Every value read from a page file goes through `escape`.
import { UNCHECKED_BYLINE } from "./notices.ts";
import type { PairView } from "./pair-view.ts";
import { formatDate } from "./timetable.ts";

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

const when = (day: string, estimated: boolean) => `${escape(formatDate(day))}${estimated ? " (expected)" : ""}`;

/** The band at the head of the page: the pair, where it stands, and who checked it. */
export function renderPairBand(view: PairView): string {
  return [
    `<section class="band record" aria-label="This pair and where it stands"><div class="wrap band-grid"><div class="band-main">`,
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

/** The body of the page: why the status, the trials, the history and the treatment. */
export function renderPairSheet(view: PairView): string {
  const trials = view.trials.map((trial) =>
    [
      `<article class="pair-trial" data-trial="${escape(trial.nctId)}">`,
      `<h3><a href="${escape(trial.registryUrl)}" rel="external">${escape(trial.nctId)}</a>`,
      trial.title ? `<span>: ${escape(trial.title)}</span>` : "",
      `</h3><dl>`,
      fact("State", escape(trial.state)),
      fact("Phase", trial.phases && escape(trial.phases)),
      fact("People", trial.participants && escape(trial.participants)),
      fact("Started", trial.start && escape(formatDate(trial.start))),
      fact("Primary completion", trial.primaryCompletion && escape(formatDate(trial.primaryCompletion))),
      fact(
        "Arms",
        trial.arms.length
          ? trial.arms.map((arm) => (arm === trial.pairArm ? `<strong>${escape(arm)}</strong>` : escape(arm))).join(", ")
          : null,
      ),
      fact("Why it stopped, in the record", trial.whyStopped && escape(trial.whyStopped)),
      fact("Results", trial.resultsPosted ? "Posted on the registry" : "None posted"),
      fact("Papers", trial.papers > 0 ? (trial.papers === 1 ? "1 paper" : `${trial.papers} papers`) : null),
      `</dl><ol class="pair-events">`,
      ...trial.events.map((event) => `<li data-event="${escape(event.key)}">${when(event.day, event.estimated)}: ${escape(event.label)}</li>`),
      `</ol></article>`,
    ].join(""),
  );
  return [
    `<div class="frame no-rail"><div class="sheet">`,
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
