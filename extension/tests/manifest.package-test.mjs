import assert from "node:assert/strict";
import { test } from "node:test";

import { HOSTS, PERMISSIONS } from "../../site/src/lib/extension-page.ts";
import { manifest, SITE } from "./package-support.mjs";

test("the site's disclosures list every permission and host in the package", () => {
  assert.deepEqual([...manifest.permissions].sort(), PERMISSIONS.map(permission => permission.name).sort());
  const disclosedHosts = [SITE.url, ...HOSTS.map(entry => `https://${entry.host}`)];
  assert.deepEqual([...manifest.host_permissions].sort(), disclosedHosts.map(host => `${host}/*`).sort());
});
