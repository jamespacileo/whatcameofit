// A pair a regulator approved (lab change `regulator-approvals`, pull request 189): the page
// the lab now writes for tirzepatide for obesity (tests/fixtures/approvals/README.md). Its
// status is "Approved", explained by EMA's record, linked, with the credit EMA's terms ask
// for; its Phase 4 trial is still only a Phase 4 trial; and the build stops on a regulator
// or a fit the site has no words for.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { pairView } from "../src/lib/pair-view.ts";
import { APPROVAL_UNDATED, renderPairBand, renderPairSheet } from "../src/lib/pair-render.ts";
import { unwordedPairCodes } from "../src/lib/pair-wording.ts";
import { STAGE_PATH, STATUS_LABELS, NOT_FOLLOWED_YET, assertNeutral } from "../src/lib/status.ts";

const read = (name) => JSON.parse(fs.readFileSync(new URL(`./fixtures/approvals/${name}`, import.meta.url), "utf8"));

/** The page as the lab writes it once its approvals have run: an exact-fit approval that
 * stands makes the pair approved whatever its trials say, the status explained by the
 * approval's key (lab u15 v4), and the page carries the approval (p12 v7). */
function approvedPage() {
  const page = read("staging-tirzepatide--obesity.json");
  const approval = read("lab-approval.json");
  page.row.status.code = "approved";
  page.row.status.explained_by = [approval.key];
  page.approvals = [approval];
  return page;
}

test("the page fits the lab's PairPage schema with its approvals", () => {
  const ajv = new Ajv2020({ allErrors: false, strict: false });
  addFormats(ajv);
  const schema = read("PairPage.schema.json");
  // The staging copy predates `TrialEvent.shown_on` (lab pull request 126), which this
  // schema requires; the shape of the approval is what is checked here.
  const approvals = ajv.compile({ ...schema, ...schema.properties.approvals, $defs: schema.$defs });
  const page = approvedPage();
  assert.ok(approvals(page.approvals), JSON.stringify(approvals.errors));
  assert.ok(!schema.required.includes("approvals"), "a bundle cut before the approvals still fits");
});

test("an approved pair says so once, at the end of the path, explained by the regulator's record", () => {
  const view = pairView(approvedPage());
  const { document } = parseHTML(`<main>${renderPairBand(view)}${renderPairSheet(view)}</main>`);
  const marked = document.querySelectorAll("[data-pair-status]");
  assert.equal(marked.length, 1);
  assert.equal(marked[0].textContent, STATUS_LABELS.approved);
  const steps = [...document.querySelectorAll("[data-standing-card] .track .step")];
  assert.equal(steps.findIndex((step) => step.classList.contains("here")), STAGE_PATH.indexOf("approved"));

  const why = document.querySelector("[data-pair-explained]");
  const lines = [...why.querySelectorAll("li")];
  assert.equal(lines.length, 1, "the approval alone explains the status");
  const line = lines[0];
  assert.equal(line.dataset.approval, "substance:OYN3CCI6QE|D009765|approved_for|EMEA/H/C/005620");
  // EMA dates a medicine's first authorisation only, so the day is said to be absent rather
  // than borrowed from the 2022 authorisation for type 2 diabetes.
  assert.equal(
    line.textContent,
    `${APPROVAL_UNDATED}: Approved by the European Medicines Agency, as Mounjaro (EMEA/H/C/005620)`,
  );
  const link = line.querySelector("a");
  assert.equal(link.getAttribute("href"), "https://www.ema.europa.eu/en/medicines/human/EPAR/mounjaro");
  assert.equal(link.getAttribute("rel"), "external");
  assert.equal(document.querySelector("[data-approval-credit]").textContent, "Source: European Medicines Agency, https://www.ema.europa.eu.");
  assertNeutral([line.textContent]);
});

test("a Phase 4 trial is still named only as one, beside the approval", () => {
  const view = pairView(approvedPage());
  const trial = view.trials.find((t) => t.nctId === "NCT06864026");
  assert.equal(trial.phases, "Phase 4");
  const { document } = parseHTML(`<main>${renderPairSheet(view)}</main>`);
  assert.equal(document.querySelectorAll("[data-approval]").length, 1, "the trial adds no approval");
});

test("a page from a bundle without approvals shows none, and its trials explain it as before", () => {
  const page = read("staging-tirzepatide--obesity.json");
  const view = pairView(page);
  assert.deepEqual(view.approvals, []);
  assert.equal(view.statusCode, "phase_3");
  assert.ok(view.explainedBy.length > 0);
  const { document } = parseHTML(`<main>${renderPairSheet(view)}</main>`);
  assert.equal(document.querySelector("[data-approval-credit]"), null);
});

test("the build stops on a regulator or a fit the site has no words for", () => {
  assert.deepEqual(unwordedPairCodes([approvedPage()]), []);
  const other = approvedPage();
  other.approvals[0].regulator = "MHRA";
  other.approvals[0].fit = "broader";
  assert.deepEqual(unwordedPairCodes([other]), ["approval fit: broader", "regulator: MHRA"]);
});

test("Approved is a place the bundle can fill, so a count of none there is a count", () => {
  assert.ok(!NOT_FOLLOWED_YET.includes("approved"));
});
