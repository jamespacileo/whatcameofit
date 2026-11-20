// Pair pages in `make deploy` (openspec pairs-site, task 4.4): read the current bundle
// version from a D1 database, export that version to a folder, check it, and give deploy.mjs
// the folder to build from and the configuration that binds the database as PAIRS. The build
// and the Worker then read one version (design decision 4): the build's pages from the
// folder, the pages made on request from D1 at the version the build recorded.
//
// Until the cutover (task 5.2) this runs only as a dry run: deploy.mjs refuses to publish
// with pair pages unless it is given --cutover, which the operator gives once.
import fs from "node:fs";
import path from "node:path";
import { exportBundle } from "../../store/ingest/scripts/export-pairs.mjs";
import { json, lastError, pairsConfig, wrangler } from "./pairs-preview.mjs";

/** The site's production Worker, as wrangler.jsonc names it. */
export const PRODUCTION_WORKER = "thenwhat";
// A stand-in id for D1's local engine, which keys its file by the id and asks Cloudflare nothing.
const LOCAL_ID = "00000000-0000-4000-8000-000000000044";

/**
 * The database a deployment reads its bundle from, with its id. Remote, it is read back with
 * `wrangler d1 info` and refused unless its jurisdiction is the EU, as every store database is
 * (docs/deploy.md, "The deployment check: read the jurisdiction back"). With `localState` it
 * is D1's local engine at that folder, for a rehearsal on this machine.
 * @returns {{ name: string, id: string, local: boolean, persistTo?: string }}
 */
export function findDeployDatabase(name, { localState } = {}) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(name ?? "")) throw new Error(`"${name}" is not a D1 database's name`);
  if (localState) return { name, id: LOCAL_ID, local: true, persistTo: path.resolve(localState) };
  const answer = wrangler(["d1", "info", name, "--json"]);
  if (answer.status !== 0) throw new Error(`${name} could not be read: ${lastError(`${answer.stdout}${answer.stderr}`)}`);
  const info = json(answer.stdout);
  if (info.jurisdiction !== "eu") throw new Error(`${name} does not read back as in the EU jurisdiction, so nothing is read from it`);
  if (typeof info.uuid !== "string") throw new Error(`Wrangler gave no id for ${name}`);
  return { name, id: info.uuid, local: false };
}

/**
 * The preview database staging reads, found through D1's REST API with D1 Read: `wrangler d1
 * info` also asks the analytics API, which the staging token does not hold. Refused
 * unless the id given is the one pinned for staging (`STAGING_PAIRS_DATABASE_ID`), the name is the
 * one asked for and ends in -preview, and the jurisdiction reads back as the EU. The token is
 * account-wide, so the pinned id is what keeps staging to this one database.
 * https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/get/
 * @returns {Promise<{ name: string, id: string, local: false }>}
 */
export async function findStagingDatabase(name, { accountId, pinnedId, token, request = fetch }) {
  if (!/^[a-z0-9][a-z0-9-]*-preview$/.test(name ?? "")) throw new Error(`staging reads only a database whose name ends in -preview, not ${name}`);
  if (!/^[0-9a-f-]{36}$/.test(pinnedId ?? "")) throw new Error("STAGING_PAIRS_DATABASE_ID is not set to the staging database's id");
  if (!accountId || !token) throw new Error("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are both needed to read the database");
  const answer = await request(`https://api.cloudflare.com/client/v4/accounts/${accountId}/d1/database/${pinnedId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await answer.json().catch(() => null);
  if (!answer.ok || !body?.success) throw new Error(`the staging database ${pinnedId} could not be read (HTTP ${answer.status})`);
  const info = body.result;
  if (info.uuid !== pinnedId) throw new Error(`the API answered for ${info.uuid}, not the pinned ${pinnedId}`);
  if (info.name !== name) throw new Error(`the pinned database is ${info.name}, not ${name}`);
  if (info.jurisdiction !== "eu") throw new Error(`${name} does not read back as in the EU jurisdiction, so nothing is read from it`);
  return { name, id: info.uuid, local: false };
}

/**
 * Export the database's current bundle version, or the one given, into `<scratch>/bundle`: the folder the site is
 * built from. `exportBundle` works the version out again from the files it wrote and removes
 * the folder unless it matches, so the build reads exactly what D1 holds.
 * @returns {Promise<{ version: string, folder: string, pairs: number, config: string }>}
 */
export async function exportForDeploy({ base, database, scratch, version: wanted = null, worker = PRODUCTION_WORKER }) {
  const config = pairsConfig({ base, database, scratch, worker });
  const where = database.local ? ["--local", "--persist-to", database.persistTo] : ["--remote"];
  const read = async (sql) => {
    const answer = wrangler(["d1", "execute", database.name, ...where, "--config", config, "--json", "--command", sql]);
    if (answer.status !== 0) throw new Error(`${database.name} could not be read: ${lastError(`${answer.stdout}${answer.stderr}`)}`);
    return json(answer.stdout)[0]?.results ?? [];
  };
  const folder = path.join(scratch, "bundle");
  const { version, counts } = await exportBundle(read, folder, wanted);
  const pairs = counts.p12_pair_page ?? 0;
  if (pairs === 0) {
    fs.rmSync(folder, { recursive: true, force: true });
    throw new Error(`bundle ${version} in ${database.name} holds no pair page`);
  }
  return { version, folder, pairs, config };
}

/** The bundle version a build recorded in its frame for pages made on request, or null. */
export function builtVersion(dist) {
  const shell = path.join(dist, "pair-shell", "index.html");
  if (!fs.existsSync(shell)) return null;
  return /data-pair-version="([0-9a-f]{16})"/.exec(fs.readFileSync(shell, "utf8"))?.[1] ?? null;
}
