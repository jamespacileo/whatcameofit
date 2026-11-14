// A readable, cookie-independent copy of a cited public trial record. No model calls.
import { makeRegistry } from "./registry.mjs";
import { SITE } from "../site.config.mjs";

const DAY = 86400000;
// A record read within the day is reused, with its retrieval date. An older one is never shown:
// when the registry cannot be read, the page says so (no lower-quality fallbacks).
const FRESH = DAY;
const PREFIX = "trial-record:v1:";
const text = value => typeof value === "string" ? value : "";
const strings = value => Array.isArray(value) ? value.filter(item => typeof item === "string") : [];
const escape = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[ch]);
const items = value => Array.isArray(value) ? value : [];

function validRecord(record, id) {
  return record?.protocolSection?.identificationModule?.nctId === id &&
    !!text(record.protocolSection.identificationModule.briefTitle).trim();
}

function validCopy(copy, id, now) {
  return copy?.version === 1 && Number.isFinite(copy.at) && copy.at <= now &&
    now - copy.at < FRESH && validRecord(copy.record, id);
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

function label(code) {
  const words = {
    RECRUITING:"Recruiting", NOT_YET_RECRUITING:"Not yet recruiting", ACTIVE_NOT_RECRUITING:"Active, not recruiting",
    COMPLETED:"Completed", TERMINATED:"Terminated", WITHDRAWN:"Withdrawn", SUSPENDED:"Suspended",
    ENROLLING_BY_INVITATION:"Enrolling by invitation", UNKNOWN:"Unknown",
    PHASE1:"Phase 1", PHASE2:"Phase 2", PHASE3:"Phase 3", PHASE4:"Phase 4", EARLY_PHASE1:"Early Phase 1", NA:"Not applicable",
    INTERVENTIONAL:"Interventional", OBSERVATIONAL:"Observational", EXPANDED_ACCESS:"Expanded access",
  };
  return words[code] ?? (text(code) ? text(code).toLowerCase().replaceAll("_", " ") : "Not reported");
}

function paragraphs(value) {
  return text(value).trim().split(/\n\s*\n/).filter(Boolean).map(line => `<p>${escape(line)}</p>`).join("");
}

function claimLinks(claims) {
  const safe = items(claims).filter(c => /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(c?.slug) && text(c.headline));
  return safe.length ? `<nav aria-label="Claims citing this trial"><h2>Claims citing this record</h2><ul class="trial-links">${safe.map(c => `<li><a href="/${escape(c.slug)}">${escape(c.headline)}</a></li>`).join("")}</ul></nav>` : `<p><a href="/">Back to ${escape(SITE.name)}</a></p>`;
}

function sourceLink(id) {
  return id ? `<a href="https://clinicaltrials.gov/study/${id}" rel="noopener">Open the full record on ClinicalTrials.gov</a>` : "";
}

function content(copy, id, claims) {
  const p = copy.record.protocolSection;
  const info = p.identificationModule;
  const status = p.statusModule ?? {};
  const design = p.designModule ?? {};
  const enrollment = design.enrollmentInfo;
  const count = Number.isFinite(enrollment?.count) && enrollment.count >= 0 ? String(enrollment.count) + (enrollment.type === "ESTIMATED" ? " (estimated)" : enrollment.type === "ACTUAL" ? " (actual)" : "") : "Not reported";
  const facts = [
    ["Study status", label(status.overallStatus)],
    ["Phase", strings(design.phases).map(label).join(", ") || "Not reported"],
    ["Study type", label(design.studyType)],
    ["Enrolment", count],
    ["Conditions", strings(p.conditionsModule?.conditions).join(", ") || "Not reported"],
    ["Lead sponsor", text(p.sponsorCollaboratorsModule?.leadSponsor?.name) || "Not reported"],
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
    <dl class="trial-facts">${facts.map(([name,value])=>`<div><dt>${name}</dt><dd>${escape(value)}</dd></div>`).join("")}</dl>
    <p class="trial-source" style="margin-top:1rem">This is the registry’s study status. It may be newer than the evidence on a claim page and does not change that claim’s status.</p>
    <section aria-labelledby="trial-overview"><h2 id="trial-overview">Study overview</h2>${summary ? paragraphs(summary) : '<p>No summary is reported in this record.</p>'}</section>
    ${official && official !== info.briefTitle ? `<details><summary>Full study title</summary><p>${escape(official)}</p></details>` : ""}
    <section aria-labelledby="trial-interventions"><h2 id="trial-interventions">Interventions</h2>${interventions.length ? `<ul class="trial-list">${interventions.map(i=>`<li><strong>${escape(i.name)}</strong>${text(i.description) ? paragraphs(i.description) : ""}</li>`).join("")}</ul>` : '<p>Not reported.</p>'}</section>
    ${outcomes.length ? `<section aria-labelledby="trial-outcomes"><h2 id="trial-outcomes">Primary outcome measures</h2>${outcomes.map(o=>`<h3>${escape(o.measure)}</h3>${paragraphs(o.description)}${text(o.timeFrame) ? `<p class="trial-source">Time frame: ${escape(o.timeFrame)}</p>` : ""}`).join("")}</section>` : ""}
    <section aria-labelledby="trial-dates"><h2 id="trial-dates">Study and record dates</h2><dl class="trial-dates">
    ${[["Study start",status.startDateStruct],["Primary completion",status.primaryCompletionDateStruct],["Study completion",status.completionDateStruct],["First posted",status.studyFirstPostDateStruct],["Results first posted",status.resultsFirstPostDateStruct],["Registry last updated",status.lastUpdatePostDateStruct]].map(([name,value])=>`<dt>${name}</dt><dd>${dated(value)}</dd>`).join("")}
    </dl></section>${claimLinks(claims)}`;
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

function failure(request, env, id, claims, status, message) {
  const title = status === 404 ? "Trial record not found" : status === 405 ? "Open this page with a link" : "Trial details are temporarily unavailable";
  return page(request,env,{id,title,status,html:`<h1>${title}</h1><p>${escape(message)}</p>${id ? `<p class="trial-number">${id}</p><p>${sourceLink(id)}</p>` : ""}${status !== 404 && status !== 405 && id ? `<p><a href="/trials/${id}">Try again</a></p>` : ""}${claimLinks(claims)}`});
}

export async function handleTrial(request, env, {fetch: get=globalThis.fetch, now=()=>Date.now()}={}) {
  const id = new URL(request.url).pathname.match(/^\/trials\/(NCT\d{8})\/?$/)?.[1] ?? "";
  if (!["GET","HEAD"].includes(request.method)) return failure(request,env,id,[],405,"Follow the trial link to read this record.");
  if (!id) return failure(request,env,"",[],404,"This address does not identify a trial record.");
  let claims;
  try {
    const response = await env.ASSETS.fetch(new Request(new URL("/trial-index.json",request.url)));
    if (!response.ok) throw Error("missing index");
    const index = await response.json();
    claims = index?.trials?.[id];
  } catch { return failure(request,env,id,[],503,"We could not load the records cited on this site. Please try again shortly."); }
  if (!Array.isArray(claims) || !claims.length) return failure(request,env,id,[],404,"This trial is not cited by a published claim on this site.");
  const at = now();
  const key = PREFIX+id;
  let copy;
  try { copy = await env.LOOKUP_RESULTS?.get(key,"json"); } catch { /* The reader still works without KV. */ }
  if (!validCopy(copy,id,at)) copy = null;
  const render = saved => page(request,env,{id,title:saved.record.protocolSection.identificationModule.briefTitle,html:content(saved,id,claims),age:at-saved.at});
  if (copy) return render(copy);
  const unavailable = () => failure(request,env,id,claims,503,"We could not retrieve this record from ClinicalTrials.gov. Please try again shortly, or open the official record.");
  if (!text(env.CONTACT_EMAIL).trim()) return unavailable();
  try {
    if (env.TRIAL_RECORD_READS && !(await env.TRIAL_RECORD_READS.limit({key:"all"})).success) {
      return failure(request,env,id,claims,503,"The registry reader is busy. Please try again in a minute.");
    }
    const registry = makeRegistry({contact:env.CONTACT_EMAIL, fetch:(url,options={})=>get(url,{...options,signal:AbortSignal.timeout(8000)})});
    const record = await registry.fetch(id);
    if (!record) return failure(request,env,id,claims,404,"ClinicalTrials.gov has no record at this identifier.");
    if (!validRecord(record,id)) throw Error("invalid registry record");
    const saved = {version:1,at:now(),record};
    try { await env.LOOKUP_RESULTS?.put(key,JSON.stringify(saved),{expirationTtl:FRESH/1000}); } catch { /* Saving a public copy is optional. */ }
    return render(saved);
  } catch { return unavailable(); }
}
