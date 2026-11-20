// A readable, cookie-independent copy of a public trial record. No model calls.
// A trial a followed pair holds gets the record's selected text and leads to the pair's page.
// A listed trial no pair holds gets the plain page: registry facts in the site's fixed
// phrases, and the line that no news report is linked yet (openspec trial-pages).
import { peopleIn, withoutPeople } from "./people.mjs";
import { makeRegistry } from "./registry.mjs";
import { SITE } from "../site.config.mjs";
import {
  NO_PHASE, NO_REPORT, NOT_STATED, PAGE_LABELS, RECORD_CHANGE_NOT_STATED, SELECTED_FIELDS, STOPPED_REASON,
  phaseWords, recordChanged, registryDate, resultsPhrase, sponsorIsPerson, sponsorName, statePhrase,
} from "../src/lib/trial-page.mjs";

const DAY = 86400000;
// A record read within the day is reused, with its retrieval date. An older one is never shown:
// when the registry cannot be read, the page says so (no lower-quality fallbacks).
const FRESH = DAY;
// The key is unchanged since the first saved copies, so that a newer copy replaces an
// older one where it lies; `VERSION` is what a copy is refused by.
const PREFIX = "trial-record:v1:";
// Version 2: the copy holds only the fields the pages show, and no person. A copy of
// version 1 was the registry's whole record, contacts included, and is never read.
const VERSION = 2;
// All the registry is asked for: what the two pages show. Its officials, contacts and
// sites are never received. The lead sponsor's class and the responsible party's type
// are asked for only to tell that a sponsor is a person, who is then not named.
const PAGE_FIELDS = [
  "NCTId", "BriefTitle", "OfficialTitle", "StatusModule", "Phase", "StudyType", "EnrollmentInfo",
  "Condition", "LeadSponsorName", "LeadSponsorClass", "ResponsiblePartyType", "InterventionName",
  "InterventionType", "InterventionDescription", "PrimaryOutcome", "BriefSummary", "HasResults",
].join(",");
const text = value => typeof value === "string" ? value : "";
const strings = value => Array.isArray(value) ? value.filter(item => typeof item === "string") : [];
const escape = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[ch]);
const items = value => Array.isArray(value) ? value : [];

function validRecord(record, id) {
  return record?.protocolSection?.identificationModule?.nctId === id &&
    !!text(record.protocolSection.identificationModule.briefTitle).trim();
}

function validCopy(copy, id, now) {
  return copy?.version === VERSION && Number.isFinite(copy.at) && copy.at <= now &&
    now - copy.at < FRESH && validRecord(copy.record, id) && peopleIn(copy.record).length === 0;
}

// Registry dates can be a year, a month or a full date; never invent missing precision.
function date(value) {
  const raw = text(value);
  if (!/^\d{4}(?:-\d{2}(?:-\d{2})?)?$/.test(raw)) return "Not reported";
  const [year, month, day] = raw.split("-");
  const names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  if (!month) return year;
  const name = names[Number(month) - 1];
  if (!name) return "Not reported";
  return day ? `${Number(day)} ${name} ${year}` : `${name} ${year}`;
}

function dated(value) {
  const shown = date(value?.date);
  return `<span class="trial-date">${escape(shown)}</span>${shown !== "Not reported" && value?.type === "ESTIMATED" ? " (estimated)" : ""}`;
}

// The registry's own word for a study type or an intervention's kind. A trial's state and
// phase are never worded here: the site's fixed phrases say them (trial-page.mjs).
function label(code) {
  const words = { INTERVENTIONAL:"Interventional", OBSERVATIONAL:"Observational", EXPANDED_ACCESS:"Expanded access" };
  const plain = text(code).toLowerCase().replaceAll("_", " ");
  return words[code] ?? (plain ? plain[0].toUpperCase() + plain.slice(1) : "Not reported");
}

function paragraphs(value) {
  return text(value).trim().split(/\n\s*\n/).filter(Boolean).map(line => `<p>${escape(line)}</p>`).join("");
}

// The pages of the treatments and conditions whose records hold this trial (the build's
// trial-index.json). A pair's address joins its two parts with a doubled hyphen.
function pairLinks(pairs) {
  const safe = items(pairs).filter(c => /^[a-z0-9]+(?:-+[a-z0-9]+)*$/.test(c?.slug) && text(c.headline));
  if (!safe.length) return `<p><a href="/">Back to ${escape(SITE.name)}</a></p>`;
  return `<nav aria-label="Pages on this site that hold this trial"><h2>Followed on this site</h2><ul class="trial-links">${safe.map(c => `<li><a href="/${escape(c.slug)}">${escape(c.headline)}</a></li>`).join("")}</ul></nav>`;
}

function sourceLink(id) {
  return id ? `<a href="https://clinicaltrials.gov/study/${id}" rel="noopener">Open the full record on ClinicalTrials.gov</a>` : "";
}

function content(copy, id, pairs) {
  const p = copy.record.protocolSection;
  const info = p.identificationModule;
  const status = p.statusModule ?? {};
  const design = p.designModule ?? {};
  const enrollment = design.enrollmentInfo;
  const count = Number.isFinite(enrollment?.count) && enrollment.count >= 0 ? String(enrollment.count) + (enrollment.type === "ESTIMATED" ? " (estimated)" : enrollment.type === "ACTUAL" ? " (actual)" : "") : "Not reported";
  const facts = [
    ["Phase", phaseWords(design.phases) ?? NO_PHASE],
    ["Study type", label(design.studyType)],
    ["Enrolment", count],
    ["Conditions", strings(p.conditionsModule?.conditions).join(", ") || "Not reported"],
    // A sponsor who is a person is not named, on this page or the plain one.
    ...(sponsorIsPerson(p.sponsorCollaboratorsModule) ? [] : [["Lead sponsor", sponsorName(p.sponsorCollaboratorsModule) ?? "Not reported"]]),
  ];
  const interventions = items(p.armsInterventionsModule?.interventions).filter(i => text(i?.name));
  const outcomes = items(p.outcomesModule?.primaryOutcomes).filter(o => text(o?.measure));
  const official = text(info.officialTitle);
  const summary = text(p.descriptionModule?.briefSummary);
  const retrieved = new Date(copy.at).toISOString().slice(0,10);
  return `<p><a href="/">${escape(SITE.name)}</a> / Trial details</p>
    <h1>${escape(info.briefTitle)}</h1>
    <p class="trial-source"><span class="trial-number">${id}</span> · ClinicalTrials.gov</p>
    <p>${sourceLink(id)}</p>
    <p class="trial-source">Selected fields from ClinicalTrials.gov, formatted for reading. Registry text is reproduced without interpretation.</p>
    <p class="trial-source">Retrieved <time datetime="${retrieved}">${date(retrieved)}</time>. Registry last updated ${dated(status.lastUpdatePostDateStruct)}.</p>
    ${pairLinks(pairs)}
    <p class="trial-state">${escape(statePhrase(status.overallStatus))}</p>
    <p class="trial-source">This is the registry’s own record of the study. It may be newer than the records on a page of this site and does not change a status there.</p>
    <dl class="trial-facts">${facts.map(([name,value])=>`<div><dt>${name}</dt><dd>${escape(value)}</dd></div>`).join("")}</dl>
    <section aria-labelledby="trial-overview"><h2 id="trial-overview">Study overview</h2>${summary ? paragraphs(summary) : '<p>No summary is reported in this record.</p>'}</section>
    ${official && official !== info.briefTitle ? `<details><summary>Full study title</summary><p>${escape(official)}</p></details>` : ""}
    <section aria-labelledby="trial-interventions"><h2 id="trial-interventions">Interventions</h2>${interventions.length ? `<ul class="trial-list">${interventions.map(i=>`<li><strong>${escape(i.name)}</strong>${text(i.description) ? paragraphs(i.description) : ""}</li>`).join("")}</ul>` : '<p>Not reported.</p>'}</section>
    ${outcomes.length ? `<section aria-labelledby="trial-outcomes"><h2 id="trial-outcomes">Primary outcome measures</h2>${outcomes.map(o=>`<h3>${escape(o.measure)}</h3>${paragraphs(o.description)}${text(o.timeFrame) ? `<p class="trial-source">Time frame: ${escape(o.timeFrame)}</p>` : ""}`).join("")}</section>` : ""}
    <section aria-labelledby="trial-dates"><h2 id="trial-dates">Study and record dates</h2><dl class="trial-dates">
    ${[["Study start",status.startDateStruct],["Primary completion",status.primaryCompletionDateStruct],["Study completion",status.completionDateStruct],["First posted",status.studyFirstPostDateStruct],["Results first posted",status.resultsFirstPostDateStruct],["Registry last updated",status.lastUpdatePostDateStruct]].map(([name,value])=>`<dt>${name}</dt><dd>${dated(value)}</dd>`).join("")}
    </dl></section>`;
}

// A date as the plain page shows it: as the registry gives it, marked when estimated.
function stated(value) {
  const shown = registryDate(value?.date);
  if (!shown) return escape(NOT_STATED);
  return `<span class="trial-date">${escape(shown)}</span>${value?.type === "ESTIMATED" ? ` (${PAGE_LABELS.estimated})` : ""}`;
}

// The plain page of a listed trial no pair holds. Registry facts only: no summary, no
// outcome, no location, no contact, nothing a sponsor wrote about a result.
function plainContent(copy, id) {
  const p = copy.record.protocolSection;
  const status = p.statusModule ?? {};
  const design = p.designModule ?? {};
  const enrollment = design.enrollmentInfo;
  const basis = enrollment?.type === "ACTUAL" ? PAGE_LABELS.actual : enrollment?.type === "ESTIMATED" ? PAGE_LABELS.planned : "";
  const count = Number.isFinite(enrollment?.count) && enrollment.count >= 0 ? `${enrollment.count}${basis ? ` (${basis})` : ""}` : NOT_STATED;
  const conditions = strings(p.conditionsModule?.conditions);
  const interventions = items(p.armsInterventionsModule?.interventions).filter(i => text(i?.name));
  const sponsors = p.sponsorCollaboratorsModule;
  const list = values => values.length ? `<ul class="trial-list">${values.map(value=>`<li>${value}</li>`).join("")}</ul>` : escape(NOT_STATED);
  const facts = [
    [PAGE_LABELS.phase, escape(phaseWords(design.phases) ?? NO_PHASE)],
    [PAGE_LABELS.enrolment, escape(count)],
    [PAGE_LABELS.conditions, list(conditions.map(escape))],
    [PAGE_LABELS.interventions, list(interventions.map(i => `${text(i.type) ? `${escape(label(i.type))}: ` : ""}${escape(i.name)}`))],
    // A sponsor who is a person is not named: one rule for both pages (trial-page.mjs).
    ...(sponsorIsPerson(sponsors) ? [] : [[PAGE_LABELS.sponsor, escape(sponsorName(sponsors) ?? NOT_STATED)]]),
  ];
  const stopped = text(status.whyStopped).trim();
  // The state is the registry's, as of the day it last changed the record: that day
  // stands with it, since a record can go unchanged for years.
  const changed = registryDate(status.lastUpdatePostDateStruct?.date, true);
  const retrieved = new Date(copy.at).toISOString().slice(0,10);
  const dates = [
    [PAGE_LABELS.start, stated(status.startDateStruct)],
    [PAGE_LABELS.primaryCompletion, stated(status.primaryCompletionDateStruct)],
    [PAGE_LABELS.completion, stated(status.completionDateStruct)],
    [PAGE_LABELS.firstPosted, stated(status.studyFirstPostDateStruct)],
    [PAGE_LABELS.lastChanged, stated(status.lastUpdatePostDateStruct)],
    [PAGE_LABELS.read, `<time datetime="${retrieved}">${escape(registryDate(retrieved))}</time>`],
  ];
  return `<p><a href="/">${escape(SITE.name)}</a> / ${PAGE_LABELS.crumb}</p>
    <h1>${escape(p.identificationModule.briefTitle)}</h1>
    <p class="trial-source"><span class="trial-number">${id}</span> · ClinicalTrials.gov</p>
    <p class="trial-state">${escape(statePhrase(status.overallStatus))}</p>
    <p class="trial-source">${escape(changed ? recordChanged(changed) : RECORD_CHANGE_NOT_STATED)}</p>
    <div class="trial-notice"><p>${NO_REPORT}</p></div>
    <dl class="trial-facts">${facts.map(([name,value])=>`<div><dt>${name}</dt><dd>${value}</dd></div>`).join("")}</dl>
    ${stopped ? `<section aria-labelledby="trial-stopped"><h2 id="trial-stopped">${STOPPED_REASON}</h2><blockquote>${escape(stopped)}</blockquote></section>` : ""}
    <section aria-labelledby="trial-results"><h2 id="trial-results">${PAGE_LABELS.results}</h2><p>${escape(resultsPhrase(copy.record.hasResults, status.resultsFirstPostDateStruct?.date))}</p></section>
    <section aria-labelledby="trial-dates"><h2 id="trial-dates">${PAGE_LABELS.dates}</h2><dl class="trial-dates">
    ${dates.map(([name,value])=>`<dt>${name}</dt><dd>${value}</dd>`).join("")}
    </dl></section>
    <p><a href="https://clinicaltrials.gov/study/${id}" rel="noopener">${PAGE_LABELS.open}</a></p>
    <p class="trial-source">${SELECTED_FIELDS}</p>`;
}

// Whether the build's trial listing holds this registry number. The built file is the
// numbers alone, one a line, so the listing itself is never read here.
async function listed(request, env, id) {
  const response = await env.ASSETS.fetch(new Request(new URL("/trial-listed.txt", request.url)));
  if (!response.ok) return false;
  return `\n${await response.text()}`.includes(`\n${id}\n`);
}

async function page(request, env, {id="", title, html, status=200, age=0}) {
  const headers = {"Content-Type":"text/html; charset=utf-8", "X-Robots-Tag":"noindex, follow", "Cache-Control": status === 200 ? `public, max-age=${Math.max(0, Math.min(300, Math.floor((FRESH-age)/1000)))}` : "no-store"};
  if (status === 405) headers.Allow = "GET, HEAD";
  if (status === 503 || status === 429) headers["Retry-After"] = "60";
  let body;
  try {
    const response = await env.ASSETS.fetch(new Request(new URL("/trial-reader", request.url)));
    if (!response.ok) throw Error("missing template");
    const template = await response.text();
    if (!["__TRIAL_CONTENT__","__TRIAL_TITLE__","__TRIAL_ID__"].every(token=>template.includes(token))) throw Error("invalid template");
    // Replace only markers in the template, never marker-like registry text.
    const values = {__TRIAL_TITLE__:escape(title), __TRIAL_ID__:id, __TRIAL_CONTENT__:html};
    body = template.replace(/__TRIAL_(?:TITLE|ID|CONTENT)__/g, marker=>values[marker]);
  } catch {
    body = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${escape(title)} | ${escape(SITE.name)}</title><main>${html}</main><footer><p>This site gives no medical advice and recommends no treatment.</p><p>A registered clinical trial is not a treatment option. Talk to a clinician about your own care.</p><p>Source: ClinicalTrials.gov. See the record above for its retrieval date.</p></footer></html>`;
  }
  return new Response(request.method === "HEAD" ? null : body, {status,headers});
}

function failure(request, env, id, pairs, status, message) {
  const title = status === 404 ? "Trial record not found" : status === 405 ? "Open this page with a link" : "Trial details are temporarily unavailable";
  return page(request,env,{id,title,status,html:`<h1>${title}</h1><p>${escape(message)}</p>${id ? `<p class="trial-number">${id}</p><p>${sourceLink(id)}</p>` : ""}${status !== 404 && status !== 405 && id ? `<p><a href="/trials/${id}">Try again</a></p>` : ""}${pairLinks(pairs)}`});
}

export async function handleTrial(request, env, {fetch: get=globalThis.fetch, now=()=>Date.now()}={}) {
  const id = new URL(request.url).pathname.match(/^\/trials\/(NCT\d{8})\/?$/)?.[1] ?? "";
  if (!["GET","HEAD"].includes(request.method)) return failure(request,env,id,[],405,"Follow the trial link to read this record.");
  if (!id) return failure(request,env,"",[],404,"This address does not identify a trial record.");
  let pairs;
  try {
    const response = await env.ASSETS.fetch(new Request(new URL("/trial-index.json",request.url)));
    if (!response.ok) throw Error("missing index");
    const index = await response.json();
    pairs = index?.trials?.[id];
  } catch { return failure(request,env,id,[],503,"We could not load the records cited on this site. Please try again shortly."); }
  const cited = Array.isArray(pairs) && pairs.length > 0;
  if (!cited) {
    pairs = [];
    let plain = false;
    try { plain = await listed(request, env, id); } catch { /* No listing: no page for an uncited trial. */ }
    if (!plain) return failure(request,env,id,[],404,"This trial is not among the records this site follows, and is not in the site’s list of trials.");
  }
  const at = now();
  const key = PREFIX+id;
  let copy;
  try { copy = await env.LOOKUP_RESULTS?.get(key,"json"); } catch { /* The reader still works without KV. */ }
  if (!validCopy(copy,id,at)) copy = null;
  const render = saved => page(request,env,{id,title:saved.record.protocolSection.identificationModule.briefTitle,html:cited ? content(saved,id,pairs) : plainContent(saved,id),age:at-saved.at});
  if (copy) return render(copy);
  const unavailable = () => failure(request,env,id,pairs,503,"We could not retrieve this record from ClinicalTrials.gov. Please try again shortly, or open the official record.");
  if (!text(env.CONTACT_EMAIL).trim()) return unavailable();
  try {
    // Pages of listed trials no pair holds are many, and have a smaller allowance of
    // their own: reading through them cannot use up what the cited trials' pages need.
    if (!cited && env.LISTED_TRIAL_READS && !(await env.LISTED_TRIAL_READS.limit({key:"all"})).success) {
      return failure(request,env,id,pairs,503,"The registry reader is busy. Please try again in a minute.");
    }
    if (env.TRIAL_RECORD_READS && !(await env.TRIAL_RECORD_READS.limit({key:"all"})).success) {
      return failure(request,env,id,pairs,503,"The registry reader is busy. Please try again in a minute.");
    }
    const registry = makeRegistry({contact:env.CONTACT_EMAIL, fetch:(url,options={})=>get(url,{...options,signal:AbortSignal.timeout(8000)})});
    // People are removed whatever the registry sends: the field list is not relied on.
    const record = withoutPeople(await registry.fetch(id, {fields:PAGE_FIELDS}));
    if (!record) return failure(request,env,id,pairs,404,"ClinicalTrials.gov has no record at this identifier.");
    if (!validRecord(record,id)) throw Error("invalid registry record");
    const saved = {version:VERSION,at:now(),record};
    try { await env.LOOKUP_RESULTS?.put(key,JSON.stringify(saved),{expirationTtl:FRESH/1000}); } catch { /* Saving a public copy is optional. */ }
    return render(saved);
  } catch { return unavailable(); }
}
