// No person of a registry record is saved, shown or handed on by the Worker: a synthetic
// record that names a person in every field the registry has for one. No network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { readFileSync } from "node:fs";
import { peopleIn, withoutPeople } from "../worker/people.mjs";
import { makeRegistry } from "../worker/registry.mjs";
import { handleTrial } from "../worker/trials.mjs";

const CITED = "NCT09000001";
const LISTED = "NCT09000002";
const now = Date.parse("2026-11-17T12:00:00Z");
const template = "<!doctype html><html><head><title>__TRIAL_TITLE__</title></head><body><main>__TRIAL_CONTENT__</main><p>__TRIAL_ID__</p></body></html>";
// Every kind of field the rule names (people.mjs, `peopleIn`).
const EVERY_KIND = [
  "centralContacts", "overallOfficials", "location contacts", "investigator name, title or affiliation",
  "person lead sponsor's name", "person collaborator's name", "results point of contact", "email", "phone",
];

/** A synthetic record with a planted person in every person field. Each planted value
 * starts with PERSON-, so one search finds any that is left. */
function record(id, { lead = { name: "PERSON-LEAD", class: "INDIV" }, party = "SPONSOR" } = {}) {
  return {
    protocolSection: {
      identificationModule: { nctId: id, briefTitle: "A synthetic study of zetamab", officialTitle: "Zetamab in a synthetic condition" },
      statusModule: { overallStatus: "RECRUITING", startDateStruct: { date: "2026-01-10", type: "ACTUAL" }, lastUpdatePostDateStruct: { date: "2026-10-01" } },
      descriptionModule: { briefSummary: "A synthetic summary." },
      conditionsModule: { conditions: ["Synthetic condition"] },
      designModule: { phases: ["PHASE3"], studyType: "INTERVENTIONAL", enrollmentInfo: { count: 120, type: "ESTIMATED" } },
      armsInterventionsModule: { interventions: [{ name: "Zetamab", type: "BIOLOGICAL" }] },
      sponsorCollaboratorsModule: {
        leadSponsor: lead,
        responsibleParty: {
          type: party,
          investigatorFullName: "PERSON-INVESTIGATOR",
          investigatorTitle: "PERSON-TITLE",
          investigatorAffiliation: "PERSON-AFFILIATION",
          oldNameTitle: "PERSON-OLD-NAME",
        },
        collaborators: [{ name: "PERSON-COLLABORATOR", class: "INDIV" }, { name: "Synthetic Institute", class: "OTHER" }],
      },
      contactsLocationsModule: {
        centralContacts: [{ name: "PERSON-CONTACT", role: "CONTACT", email: "PERSON-contact@example.test", phone: "PERSON-555-0100", phoneExt: "PERSON-12" }],
        overallOfficials: [{ name: "PERSON-OFFICIAL", affiliation: "PERSON-OFFICIAL-AFFILIATION", role: "PRINCIPAL_INVESTIGATOR" }],
        locations: [{
          facility: "Synthetic Hospital", city: "Synthetic City", country: "Nowhere",
          contacts: [{ name: "PERSON-SITE-CONTACT", email: "PERSON-site@example.test", phone: "PERSON-555-0101" }],
        }],
      },
    },
    resultsSection: { moreInfoModule: { pointOfContact: { title: "PERSON-POINT", organization: "PERSON-ORG", email: "PERSON-point@example.test", phone: "PERSON-555-0102" } } },
    hasResults: true,
  };
}

function store(entries = []) {
  const kept = new Map(entries);
  const puts = [];
  return {
    kept, puts,
    get: async (key) => (kept.has(key) ? JSON.parse(kept.get(key)) : null),
    put: async (key, value, options) => { puts.push({ key, value, options }); kept.set(key, value); },
  };
}

function served(payload, { entries } = {}) {
  const calls = [];
  const cache = store(entries);
  const env = {
    CONTACT_EMAIL: "corrections@example.test",
    LOOKUP_RESULTS: cache,
    TRIAL_RECORD_READS: { limit: async () => ({ success: true }) },
    ASSETS: {
      fetch: async (request) => {
        const pathname = new URL(request.url).pathname;
        if (pathname === "/trial-index.json") return Response.json({ trials: { [CITED]: [{ slug: "synthetic-claim", headline: "A synthetic claim" }] } });
        if (pathname === "/trial-listed.txt") return new Response(`${LISTED}\n`);
        if (pathname === "/trial-reader") return new Response(template);
        return new Response("missing", { status: 404 });
      },
    },
  };
  const fetch = async (url) => { calls.push(String(url)); return Response.json(payload); };
  const open = (id) => handleTrial(new Request(`https://example.test/trials/${id}`), env, { fetch, now: () => now });
  return { calls, cache, open };
}

test("the synthetic record names a person in every kind of field, and the rule removes each", () => {
  const given = record(CITED);
  const before = JSON.stringify(given);
  assert.deepEqual(peopleIn(given).sort(), [...EVERY_KIND].sort());

  const kept = withoutPeople(given);

  assert.deepEqual(peopleIn(kept), []);
  assert.doesNotMatch(JSON.stringify(kept), /PERSON-/);
  assert.equal(JSON.stringify(given), before, "the record given is not changed");
  // Places and organisations are not people, and what says a sponsor is a person stays.
  const protocol = kept.protocolSection;
  assert.deepEqual(protocol.contactsLocationsModule.locations, [{ facility: "Synthetic Hospital", city: "Synthetic City", country: "Nowhere" }]);
  assert.deepEqual(protocol.sponsorCollaboratorsModule, {
    leadSponsor: { class: "INDIV" },
    responsibleParty: { type: "SPONSOR" },
    collaborators: [{ class: "INDIV" }, { name: "Synthetic Institute", class: "OTHER" }],
  });
  assert.equal(kept.hasResults, true);
});

test("a sponsor-investigator the registry classes as other is not named; an organisation is", () => {
  const investigator = withoutPeople(record(CITED, { lead: { name: "PERSON-LEAD", class: "OTHER" }, party: "SPONSOR_INVESTIGATOR" }));
  assert.deepEqual(investigator.protocolSection.sponsorCollaboratorsModule.leadSponsor, { class: "OTHER" });
  const organisation = withoutPeople(record(CITED, { lead: { name: "Synthetic Pharma", class: "INDUSTRY" } }));
  assert.deepEqual(organisation.protocolSection.sponsorCollaboratorsModule.leadSponsor, { name: "Synthetic Pharma", class: "INDUSTRY" });
  for (const other of [null, "text", [], { studies: [] }]) assert.equal(withoutPeople(other), other);
});

for (const [kind, id] of [["a claim cites", CITED], ["only the listing holds", LISTED]]) {
  test(`the page of a trial ${kind} holds no person, and neither does its saved copy`, async () => {
    // The registry answers with everything, whatever fields it was asked for.
    const site = served(record(id));

    const response = await site.open(id);
    const html = await response.text();

    assert.equal(response.status, 200);
    assert.ok(html.includes("A synthetic study of zetamab"));
    assert.doesNotMatch(html, /PERSON-/);
    assert.equal(site.cache.puts.length, 1);
    const [{ key, value }] = site.cache.puts;
    assert.equal(key, `trial-record:v1:${id}`);
    assert.doesNotMatch(value, /PERSON-|email|phone|centralContacts|overallOfficials|pointOfContact|investigator/);
    const copy = JSON.parse(value);
    assert.equal(copy.version, 2);
    assert.deepEqual(peopleIn(copy.record), []);
  });
}

test("the registry is asked only for the fields the pages show", async () => {
  const site = served(record(CITED));
  await site.open(CITED);

  const asked = new URL(site.calls[0]);
  assert.equal(asked.pathname, `/api/v2/studies/${CITED}`);
  const fields = asked.searchParams.get("fields").split(",");
  assert.ok(fields.includes("BriefTitle") && fields.includes("LeadSponsorClass") && fields.includes("ResponsiblePartyType"));
  for (const field of fields) assert.doesNotMatch(field, /Contact|OverallOfficial|Location|Investigator|Collaborator|ResponsibleParty(?!Type$)|MoreInfo|PointOfContact|Email|Phone/i, field);
});

test("a copy saved before people were removed is refused and replaced where it lies", async () => {
  const key = `trial-record:v1:${CITED}`;
  for (const old of [
    // The whole record, as version 1 saved it.
    { version: 1, at: now - 3_600_000, record: record(CITED) },
    // A copy of this version that holds a person all the same is not shown either.
    { version: 2, at: now - 3_600_000, record: record(CITED) },
  ]) {
    const site = served(record(CITED), { entries: [[key, JSON.stringify(old)]] });

    const html = await (await site.open(CITED)).text();

    assert.equal(site.calls.length, 1, "the registry is read again");
    assert.doesNotMatch(html, /PERSON-/);
    assert.deepEqual([...site.cache.kept.keys()], [key]);
    assert.doesNotMatch(site.cache.kept.get(key), /PERSON-/);
    assert.equal(JSON.parse(site.cache.kept.get(key)).version, 2);
  }
});

test("a clean copy read within the day is reused", async () => {
  const key = `trial-record:v1:${CITED}`;
  const site = served(record(CITED), { entries: [[key, JSON.stringify({ version: 2, at: now - 3_600_000, record: withoutPeople(record(CITED)) })]] });

  assert.equal((await site.open(CITED)).status, 200);
  assert.equal(site.calls.length, 0);
});

test("the lookup's registry keeps and hands on no person: one record, and a page of them", async () => {
  const cache = store();
  const answers = {
    [`/api/v2/studies/${CITED}`]: record(CITED),
    "/api/v2/studies": { studies: [record(CITED), record(LISTED, { lead: { name: "PERSON-LEAD", class: "OTHER" }, party: "SPONSOR_INVESTIGATOR" })], totalCount: 2 },
  };
  const asked = [];
  const registry = makeRegistry({
    contact: "corrections@example.test", cache, cacheTimeoutMs: 1000,
    fetch: async (url) => { asked.push(new URL(url)); return Response.json(answers[new URL(url).pathname]); },
  });

  const one = await registry.fetch(CITED);
  const found = await registry.search("zetamab", null);

  assert.deepEqual(peopleIn(one), []);
  assert.equal(found.length, 2);
  for (const study of found) assert.deepEqual(peopleIn(study), []);
  assert.doesNotMatch(JSON.stringify([one, found]), /PERSON-/);
  // An organisation is still there for the lookup to compare with what a report says.
  assert.equal(found[0].protocolSection.sponsorCollaboratorsModule.collaborators[1].name, "Synthetic Institute");
  // A search asks who a sponsor is, or the rule could not tell a person from a company.
  const fields = asked[1].searchParams.get("fields").split(",");
  for (const field of ["LeadSponsorClass", "CollaboratorClass", "ResponsiblePartyType"]) assert.ok(fields.includes(field), field);
  assert.equal(cache.puts.length, 2);
  for (const { key, value } of cache.puts) {
    assert.match(key, /^source-v2:registry:[0-9a-f]{64}$/);
    assert.doesNotMatch(value, /PERSON-|"email"|"phone/);
  }
});

test("an answer kept before people were removed is not read", async () => {
  const cache = store();
  const registry = (fetch) => makeRegistry({ contact: "corrections@example.test", cache, cacheTimeoutMs: 1000, fetch });
  await registry(async () => Response.json(record(CITED))).fetch(CITED);
  const [{ key, value }] = cache.puts;
  // The same query's entry as version 1 wrote it, people included, under the old key and the new.
  const old = JSON.stringify({ ...JSON.parse(value), version: 1, value: record(CITED) });
  cache.kept.clear();
  cache.kept.set(key.replace("source-v2:", "source-v1:"), old);
  cache.kept.set(key, old);
  let reads = 0;

  const again = await registry(async () => { reads += 1; return Response.json(record(CITED)); }).fetch(CITED);

  assert.equal(reads, 1, "the registry is asked again");
  assert.deepEqual(peopleIn(again), []);
  assert.doesNotMatch(cache.kept.get(key), /PERSON-/);
});

test("a legacy investigator affiliation is removed on initial fetch and old-cache replacement", async () => {
  const given = JSON.parse(readFileSync(new URL("../../pipeline/tests/fixtures/clinicaltrials/synthetic_legacy_affiliation.json", import.meta.url)));
  assert.ok(peopleIn(given).length);
  const clean = withoutPeople(given);
  assert.deepEqual(clean.protocolSection.sponsorCollaboratorsModule.responsibleParty, { type: "PRINCIPAL_INVESTIGATOR" });
  const key = `trial-record:v1:${CITED}`;
  for (const entries of [[], [[key, JSON.stringify({ version: 2, at: now, record: given })]]]) {
    const site = served(given, { entries });
    const response = await site.open(CITED);
    assert.equal(response.status, 200);
    assert.doesNotMatch(await response.text(), /PERSON-LEGACY-PRACTICE/);
    assert.equal(site.calls.length, 1);
    assert.deepEqual(JSON.parse(site.cache.kept.get(key)).record, clean);
  }
});
