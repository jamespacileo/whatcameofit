// Builds data.js for the front page mocks from the published export.
// Run from the repository root: node .impeccable/mocks/frontpage/build-data.mjs
// Everything a mock shows about a claim comes from this file; nothing is invented here.
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..", "..");
const data = JSON.parse(readFileSync(join(root, "site/data/published-export.json"), "utf8"));

const TODAY = "2026-11-14";
const ICON_LIMIT = 9000; // characters of data URI; larger icons fall back to a letter tile

const topics = Object.fromEntries(data.verticals.map((v) => [v.slug, v.title]));
const host = (url) => new URL(url).hostname.replace(/^www\./, "");

const outlets = {};
for (const outlet of data.outlets) {
  if (outlet.icon && outlet.icon.length <= ICON_LIMIT) outlets[outlet.domain] = outlet.icon;
}

const EVENT_LABELS = {
  trial_registered: "Trial registered",
  trial_results_posted: "Trial results posted",
  followup_paper: "Follow-up paper",
};
const STATE_LABELS = {
  started: "Trial started",
  completed: "Trial completed",
  terminated: "Trial terminated",
  withdrawn: "Trial withdrawn",
  suspended: "Trial suspended",
};
function eventLabel(event) {
  if (event.type === "trial_status_change") return STATE_LABELS[event.trial_state] ?? "Trial status changed";
  if (event.type === "regulatory_decision")
    return event.regulatory_outcome === "approved" ? "Regulatory approval" : "Regulatory refusal";
  return EVENT_LABELS[event.type] ?? event.type;
}

const claims = data.claims.map((claim) => {
  const past = claim.events.filter((e) => e.event_date <= TODAY);
  const trialIds = new Set(past.filter((e) => e.trial_id).map((e) => e.trial_id));
  const withState = (state) =>
    new Set(past.filter((e) => e.trial_state === state).map((e) => e.trial_id)).size;
  const results = new Set(
    past.filter((e) => e.type === "trial_results_posted").map((e) => e.trial_id),
  ).size;
  const registered = past.filter((e) => e.type === "trial_registered").map((e) => e.event_date).sort();
  const latest = [...past].sort((a, b) => (a.event_date < b.event_date ? 1 : -1))[0] ?? null;
  const approval = past.find((e) => e.type === "regulatory_decision") ?? null;
  const dated = claim.promises
    .filter((p) => p.parsed_date)
    .sort((a, b) => (a.parsed_date < b.parsed_date ? 1 : -1));
  const promise = dated[0] ?? claim.promises[0] ?? null;
  const articles = [...claim.articles].sort((a, b) => (a.published_date < b.published_date ? -1 : 1));

  return {
    slug: claim.slug,
    head: claim.headline,
    iv: claim.intervention.name,
    aka: claim.intervention.synonyms.slice(0, 3),
    ind: claim.indication,
    topic: topics[claim.vertical] ?? claim.vertical,
    approach: claim.approach,
    first: claim.first_reported_date,
    stage: claim.evidence_stage,
    status: claim.status.code,
    quiet: claim.status.overlay_years,
    hist: claim.status.history,
    arts: articles.map((a) => ({ o: a.outlet, t: a.title, d: a.published_date, dom: host(a.url) })),
    promise: promise ? { text: promise.description, date: promise.parsed_date } : null,
    promises: claim.promises.length,
    trials: {
      n: trialIds.size,
      started: withState("started"),
      completed: withState("completed"),
      results,
      firstReg: registered[0] ?? null,
    },
    latest: latest ? { date: latest.event_date, label: eventLabel(latest), id: latest.trial_id } : null,
    approval: approval ? { date: approval.event_date, text: approval.summary } : null,
    matches: claim.matches.length,
  };
});

// Registry records dated in the last 45 days, across every claim: the "what moved" lists.
const since = new Date(Date.parse(TODAY) - 45 * 864e5).toISOString().slice(0, 10);
const recent = data.claims
  .flatMap((claim) =>
    claim.events
      .filter((e) => e.event_date > since && e.event_date <= TODAY)
      .map((e) => ({ slug: claim.slug, date: e.event_date, label: eventLabel(e), id: e.trial_id, src: e.source_name })),
  )
  .sort((a, b) => (a.date < b.date ? 1 : -1));

const out = {
  today: TODAY,
  checked: data.last_checked_at.slice(0, 10),
  claims,
  recent,
  outlets,
};
writeFileSync(join(here, "data.js"), `window.MOCK = ${JSON.stringify(out)};\n`);

const count = (key) => claims.reduce((a, c) => ((a[key(c)] = (a[key(c)] ?? 0) + 1), a), {});
console.log("claims", claims.length, "| recent records", recent.length, "| icons kept", Object.keys(outlets).length, "of", data.outlets.length);
console.log("bytes", JSON.stringify(out).length);
console.log("dated promises", claims.filter((c) => c.promise?.date).length, "| undated only", claims.filter((c) => c.promise && !c.promise.date).length);
console.log("trial before report", claims.filter((c) => c.trials.firstReg && c.trials.firstReg < c.first).length);
console.log("status moves (2+ history)", claims.filter((c) => c.hist.length > 1).length);
console.log("statuses", JSON.stringify(count((c) => c.status)));
