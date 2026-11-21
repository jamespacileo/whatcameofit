// The deployed Worker's settings that keep the site private.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const config = JSON.parse(fs.readFileSync("wrangler.jsonc", "utf8").replace(/^\s*\/\/.*$/gm, ""));

test("the Worker runs before every file and has no address but its own domain", () => {
  assert.equal(config.assets.run_worker_first, true);
  assert.equal(config.workers_dev, false);
  assert.equal(config.preview_urls, false);
  assert.equal(config.observability.enabled, false);
});

test("no Access setting or store id is written into the config", () => {
  for (const name of ["ACCESS_ISSUER", "ACCESS_AUD", "OPERATOR_EMAILS"]) assert.equal(config.vars?.[name], undefined, name);
  assert.equal(config.d1_databases, undefined);
});
