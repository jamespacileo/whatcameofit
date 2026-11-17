// The two kinds the progressive load of trials adds (migration 0006): `trial_paper`, a
// paper a literature index lists under a trial's number, and `trial_slice`, how far a
// slice of trials has come. Each through the service's routes on D1's local engine, with
// the report without applying held to the merge's own report every time.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { Service, engineUnavailable, sha } from "./harness.mjs";

const skip = (await engineUnavailable()) ?? false;
if (skip && process.env.CI) throw new Error(skip);

const at = (day) => `2026-11-${day}T00:00:00.000000+00:00`;
const counts = (resolved, added, conflicts, matched) => ({ resolved, added, conflicts, matched });

// A small payload travels in its record; its checksum is its body's.
function payload(text) {
  return ["payload", sha(text), { sha256: sha(text), bytes: Buffer.byteLength(text), body: text }];
}
const trial = (number) => ["registry_trial", `clinicaltrials.gov|${number}`, { registry_name: "clinicaltrials.gov",
  external_id: number, title: "Semaglutide in obesity", conditions: ["Obesity"], interventions: [{ type: "DRUG", name: "Semaglutide" }],
  intervention_names: "Semaglutide", phases: ["PHASE3"], overall_status: "COMPLETED", payload_sha256: sha(`{"nctId":"${number}"}`), fetched_at: at("01") }];
const paper = (number, pubmed, record, fetched) => ["trial_paper", `clinicaltrials.gov|${number}|pubmed|${pubmed}`, {
  registry_name: "clinicaltrials.gov", trial_id: number, source_name: "pubmed", pubmed_id: pubmed,
  payload_sha256: sha(record), fetched_at: fetched }];
const slice = (number, more = {}) => ["trial_slice", `completed|2024|${number}`, { rule: "completed", year: 2024, number,
  grp: "ended", trials: 500, with_results: 120, ...more }];

let s;
before(async () => {
  if (skip) return;
  s = await Service.open();
  assert.equal(await s.hand("trials", [payload('{"nctId":"NCT1"}'), trial("NCT1")], { as: "operator" }), null);
  assert.equal((await s.merge("trials", "operator")).body.status, "merged");
});
after(async () => { if (s) await s.close(); });

// The report without applying comes from a twin run, which the service drops once it has
// answered; then the run itself is handed over and merged.
async function merged(id, records) {
  assert.equal(await s.hand(`${id}-twin`, records, { as: "operator" }), null);
  const counted = (await s.preview(`${id}-twin`, "operator")).body;
  const handed = await s.hand(id, records, { as: "operator" });
  assert.equal(handed, null, `handing over ${id}: ${handed?.text}`);
  const done = (await s.merge(id, "operator")).body;
  if (done.status === "merged") assert.deepEqual(counted.report, done.report, "the report without applying says what the merge says");
  return { ...done, reconciles: counted.reconciles };
}

test("a trial's paper is added once, matched after, and replaced only by a later fetch", { skip }, async () => {
  const first = '{"pmid":"111","title":"first fetch"}', later = '{"pmid":"111","title":"later fetch"}', other = '{"pmid":"222"}';
  const stored = () => s.all("SELECT p.pubmed_id, p.payload_sha256, p.fetched_at FROM trial_paper p JOIN registry_trial t ON t.id = p.trial_id WHERE t.external_id = 'NCT1' ORDER BY 1");

  assert.deepEqual((await merged("paper-1", [payload(first), paper("NCT1", "111", first, at("05"))])).report.trial_paper, counts(1, 1, 0, 0));
  assert.deepEqual(await stored(), [["111", sha(first), at("05")]]);

  // An older fetch of the same paper, beside a paper the trial did not have.
  const older = '{"pmid":"111","title":"older fetch"}';
  const second = await merged("paper-2", [payload(older), payload(other), paper("NCT1", "111", older, at("03")), paper("NCT1", "222", other, at("05"))]);
  assert.deepEqual(second.report.trial_paper, counts(2, 1, 0, 1));
  assert.deepEqual(await stored(), [["111", sha(first), at("05")], ["222", sha(other), at("05")]], "an older fetch never replaces a newer record");

  assert.deepEqual((await merged("paper-3", [payload(later), paper("NCT1", "111", later, at("09"))])).report.trial_paper, counts(1, 0, 0, 1));
  assert.deepEqual((await stored())[0], ["111", sha(later), at("09")], "a later fetch replaces the record and its time");
});

test("a paper for a trial the store does not hold undoes the merge", { skip }, async () => {
  const record = '{"pmid":"333"}';
  const before = await s.one("SELECT count(*) FROM trial_paper");
  const undone = await merged("paper-orphan", [payload(record), paper("NCT404", "333", record, at("05"))]);
  assert.notEqual(undone.status, "merged");
  assert.equal(undone.reconciles, false, "the report without applying says the counts would not reconcile");
  assert.equal(await s.one("SELECT count(*) FROM trial_paper"), before);
  assert.equal(await s.one("SELECT count(*) FROM payload WHERE sha256 = ?", sha(record)), 0, "nothing of the run is kept");
});

test("a slice of trials is added once, and no merge takes it back a stage", { skip }, async () => {
  const row = (number) => s.all(`SELECT grp, trials, with_results, registry_papers, pubmed_asked, pubmed_found, in_store,
    record_at, registry_papers_at, pubmed_papers_at, in_store_at, page_at FROM trial_slice WHERE rule = 'completed' AND year = 2024 AND number = ?`, number);

  assert.deepEqual((await merged("slice-1", [slice(1, { record_at: at("05") })])).report.trial_slice, counts(1, 1, 0, 0));
  assert.deepEqual(await row(1), [["ended", 500, 120, null, null, null, 0, at("05"), null, null, null, null]]);

  // The next stage, beside a slice the store did not have.
  const next = await merged("slice-2", [slice(1, { record_at: at("05"), registry_papers: 40, registry_papers_at: at("06"), in_store: 500, in_store_at: at("07") }), slice(2)]);
  assert.deepEqual(next.report.trial_slice, counts(2, 1, 0, 1));
  assert.deepEqual(await row(1), [["ended", 500, 120, 40, null, null, 500, at("05"), at("06"), null, at("07"), null]]);

  // A device that is behind: an earlier state of the slice, with smaller counts, an
  // earlier time and no later stage. Nothing goes back, and what it adds is kept.
  await merged("slice-3", [slice(1, { grp: "active updated", trials: 480, with_results: 100, record_at: at("02"), registry_papers: 12,
    registry_papers_at: at("03"), pubmed_asked: 480, pubmed_found: 9, pubmed_papers_at: at("04") })]);
  assert.deepEqual(await row(1), [["ended", 500, 120, 40, 480, 9, 500, at("05"), at("06"), at("04"), at("07"), null]]);

  // A later record states the group again; the page is made.
  await merged("slice-4", [slice(1, { grp: "ended with results", record_at: at("10"), page_at: at("11") })]);
  assert.deepEqual(await row(1), [["ended with results", 500, 120, 40, 480, 9, 500, at("10"), at("06"), at("04"), at("07"), at("11")]]);
});

test("the same slices in either order leave the same store", { skip }, async () => {
  const a = slice(7, { record_at: at("05"), registry_papers: 3, registry_papers_at: at("06") });
  const b = slice(7, { grp: "ended with results", trials: 510, record_at: at("08"), in_store: 510, in_store_at: at("09") });
  const read = (number) => s.all("SELECT grp, trials, registry_papers, in_store, record_at, registry_papers_at, in_store_at FROM trial_slice WHERE number = ?", number);
  await merged("order-ab-1", [a]);
  await merged("order-ab-2", [b]);
  const ab = await read(7);
  const [a8, b8] = [a, b].map(([kind, , body]) => [kind, "completed|2024|8", { ...body, number: 8 }]);
  await merged("order-ba-1", [b8]);
  await merged("order-ba-2", [a8]);
  assert.deepEqual(await read(8), ab);
  assert.deepEqual(ab, [["ended with results", 510, 3, 510, at("08"), at("06"), at("09")]]);
});

test("a slice in a group the schema does not know is refused whole", { skip }, async () => {
  const held = await s.one("SELECT count(*) FROM trial_slice");
  const refused = await merged("slice-bad", [slice(9, { grp: "abandoned" })]);
  assert.notEqual(refused.status, "merged");
  assert.equal(await s.one("SELECT count(*) FROM trial_slice"), held);
});

test("a pushed trial and its papers stay in D1; the consumer's go to the inbox, and clearing never deletes a trial from under a paper", { skip }, async () => {
  // The fault this guards: a paper merged into D1 but kept out of the inbox never reached
  // the bulk file, and clearing then tried to delete its trial from under it.
  const { clearInbox } = await import("../src/store.mjs");
  const held = (number) => s.one("SELECT count(*) FROM trial_paper p JOIN registry_trial t ON t.id = p.trial_id WHERE t.external_id = ?", number);

  // A push made on purpose (a device's slice of trials) is not for the inbox.
  const pushed = '{"pmid":"444"}';
  assert.equal(await s.hand("pushed", [payload('{"nctId":"NCT8"}'), trial("NCT8"), payload(pushed), paper("NCT8", "444", pushed, at("05"))]), null);
  assert.equal((await s.merge("pushed")).body.status, "merged");
  assert.equal(await s.one("SELECT count(*) FROM inbox WHERE run_id = 'pushed'"), 0);
  assert.equal(await held("NCT8"), 1);

  // What the store-side consumer creates is: a trial with a paper, and one with none.
  const record = '{"pmid":"555"}';
  const records = [payload('{"nctId":"NCT9"}'), trial("NCT9"), payload(record), paper("NCT9", "555", record, at("05")),
    payload('{"nctId":"NCT10"}'), trial("NCT10")];
  assert.equal(await s.hand("inboxed", records, { as: "consumer" }), null);
  assert.equal((await s.merge("inboxed", "consumer")).body.status, "merged");
  const kept = (await s.all("SELECT kind FROM inbox WHERE run_id = 'inboxed' ORDER BY kind")).map(([kind]) => kind);
  assert.ok(kept.includes("registry_trial") && kept.includes("trial_paper"), `the inbox keeps the trial and its paper: ${kept}`);

  const cleared = await clearInbox(s.db, await s.one("SELECT max(seq) FROM inbox"));
  assert.equal(cleared.left, 0, "the clearing went through: no row was deleted from under another");
  assert.equal(await s.one("SELECT count(*) FROM registry_trial WHERE external_id = 'NCT10'"), 0, "a trial with no paper is in the bulk file now, not in D1");
  assert.equal(await held("NCT9"), 1, "a trial a paper is stored for stays, with its paper");
  assert.equal(await held("NCT8"), 1, "and the pushed one was never the inbox's to clear");
});
