// The small bundle against the lab's published schemas, unmodified, under strict Ajv 2020 with
// ajv-formats (openspec pairs-site, task 2.5). The site's own reader, `readBundle`, reads a
// `date-time` with no UTC offset as a time, because the lab writes `PairOrigin.created_at` with
// none, which RFC 3339 (section 5.6, `time-offset` is required) and so JSON Schema's
// `date-time` format do not allow. This test records exactly which files that leaves failing
// and why. When the lab's fixed bundle is cut into tests/bundle, the list is empty, this test
// fails, and the allowance in bundle.ts is removed with it (task 2.5).
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { test } from "node:test";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { modelOf } from "../src/lib/bundle.ts";

const bundle = "tests/bundle";

/** Each failing file, with the distinct reasons. */
function strictFailures(folder) {
  const ajv = new Ajv2020({ strict: true, allErrors: true });
  addFormats(ajv);
  const failures = {};
  for (const name of fs.readdirSync(folder).filter((entry) => entry.startsWith("p12_")).sort()) {
    const validate = ajv.compile(JSON.parse(fs.readFileSync(path.join(folder, "schemas", `${modelOf(name)}.json`), "utf8")));
    for (const file of fs.readdirSync(path.join(folder, name)).sort()) {
      const page = JSON.parse(fs.readFileSync(path.join(folder, name, file), "utf8"));
      if (!validate(page)) failures[`${name}/${file}`] = [...new Set(validate.errors.map((error) => `${error.instancePath} ${error.message}`))];
    }
  }
  return failures;
}

// The files that hold a pair with a claim origin, the only place `created_at` is written.
const KNOWN = [
  "p12_pair_changes_feed/changes.json",
  "p12_pair_clinical_category_page/D007239.json",
  "p12_pair_clinical_category_page/D009468.json",
  "p12_pair_clinical_category_page/D009765.json",
  "p12_pair_clinical_category_page/D017563.json",
  "p12_pair_clinical_category_page/D050177.json",
  "p12_pair_data_file/acoziborole--infections.json",
  "p12_pair_data_file/ambroxol--dementia.json",
  "p12_pair_data_file/apitegromab--neuromuscular-diseases.json",
  "p12_pair_data_file/apitegromab--obesity.json",
  "p12_pair_data_file/tulisokibart--hidradenitis-suppurativa.json",
  "p12_pair_data_file/tulisokibart--lung-diseases-interstitial.json",
  "p12_pair_intervention_page/acoziborole.json",
  "p12_pair_intervention_page/ambroxol.json",
  "p12_pair_intervention_page/apitegromab.json",
  "p12_pair_intervention_page/tulisokibart.json",
  "p12_pair_page/acoziborole--infections.json",
  "p12_pair_page/ambroxol--dementia.json",
  "p12_pair_page/apitegromab--neuromuscular-diseases.json",
  "p12_pair_page/apitegromab--obesity.json",
  "p12_pair_page/tulisokibart--hidradenitis-suppurativa.json",
  "p12_pair_page/tulisokibart--lung-diseases-interstitial.json",
  "p12_pair_topic_page/brain-and-nerves.json",
  "p12_pair_topic_page/diabetes-and-hormones.json",
  "p12_pair_topic_page/infections.json",
  "p12_pair_topic_page/lungs-and-breathing.json",
];

// The one fault, and the two errors Ajv reports with it: the origin then fits neither branch
// of its `anyOf` (an object, or null).
const ONE_FAULT = /\/origin\/created_at must match format "date-time"$|\/origin must be null$|\/origin must match a schema in anyOf$/;

test("strictly, only the files with a claim origin fail, and only for created_at's missing offset", () => {
  const failures = strictFailures(bundle);
  assert.deepEqual(Object.keys(failures).sort(), KNOWN);
  for (const [file, reasons] of Object.entries(failures)) {
    for (const reason of reasons) assert.match(reason, ONE_FAULT, file);
    assert.ok(reasons.some((reason) => reason.endsWith('/origin/created_at must match format "date-time"')), file);
  }
  // Written as the lab writes it: a time with no offset.
  const page = JSON.parse(fs.readFileSync(path.join(bundle, "p12_pair_page", "apitegromab--obesity.json"), "utf8"));
  assert.match(page.row.origin.created_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/);
});
