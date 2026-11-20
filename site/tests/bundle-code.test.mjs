// The code made from the bundle's schemas (openspec pairs-site, task 2.2), from tests/bundle:
// real pair pages and schemas the lab's own pipeline test writes from its recorded slice.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { pathToFileURL } from "node:url";
import { modelOf, readBundle } from "../src/lib/bundle.ts";
import { bundleSchemas, writeBundleCode } from "../scripts/bundle-code.mjs";

const bundle = "tests/bundle";
const out = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-code-"));
let validators;

before(async () => {
  await writeBundleCode(bundle, out);
  validators = await import(pathToFileURL(path.join(out, "validators.mjs")).href);
});

test("each page model has a compiled validator and its types", () => {
  const models = bundleSchemas(bundle).map(({ model }) => model);
  assert.deepEqual(models.sort(), fs.readdirSync(path.join(bundle, "schemas")).map((name) => name.slice(0, -5)).sort());
  for (const model of models) {
    assert.equal(typeof validators[`validate${model}`], "function", model);
    assert.match(fs.readFileSync(path.join(out, "types", `${model}.d.ts`), "utf8"), new RegExp(`export interface ${model} \\{`));
  }
});

test("the compiled validators take every file of the bundle, as the build's reader does", () => {
  const { pages } = readBundle(bundle);
  for (const folder of fs.readdirSync(bundle).filter((name) => name.startsWith("p12_"))) {
    const model = modelOf(folder);
    const validate = validators[`validate${model}`];
    for (const [address, file] of Object.entries(pages[model])) assert.equal(validate(file), true, `${model} ${address}`);
  }
});

test("a pair page with a missing field is refused, naming the field", () => {
  const file = structuredClone(readBundle(bundle).pages.PairPage["acoziborole--infections"]);
  delete file.row.status;
  assert.equal(validators.validatePairPage(file), false);
  const [error] = validators.validatePairPage.errors;
  assert.equal(error.instancePath, "/row");
  assert.equal(error.params.missingProperty, "status");
});

test("the validators run where code cannot be made from strings, as in a Worker", () => {
  const page = path.resolve(bundle, "p12_pair_page", "acoziborole--infections.json");
  const script = `
    const { validatePairPage } = await import(${JSON.stringify(pathToFileURL(path.join(out, "validators.mjs")).href)});
    const fs = await import("node:fs");
    const file = JSON.parse(fs.readFileSync(${JSON.stringify(page)}, "utf8"));
    const broken = structuredClone(file); delete broken.trials;
    console.log(JSON.stringify([validatePairPage(file), validatePairPage(broken)]));
  `;
  const result = spawnSync(process.execPath, ["--disallow-code-generation-from-strings", "--input-type=module", "-e", script], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), [true, false]);
});
