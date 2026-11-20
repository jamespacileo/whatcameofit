// The checks a staging deployment must pass before it counts (docs/deploy.md, "Staging"). Run by
// the staging job after each deploy, against staging's own address, with the build's folder:
//
//   node scripts/staging-smoke.mjs https://staging.whatcameofit.com dist
//
// Each address must answer with its expected status and carry X-Robots-Tag: noindex: a built
// page, a pair page and its data file made on request, an old claim address that leads to its
// pair (301), one with no pair (410), and an address no pair has (404). /bundle-version.txt must
// name the bundle the build was made from. The addresses are read from the build itself, so the
// checks follow whatever bundle staging holds. An address that does not answer at all (no DNS
// record yet, no certificate yet) fails, and says so: it never counts as a pass.
import fs from "node:fs";
import path from "node:path";
import { setTimeout as wait } from "node:timers/promises";

/** What a fetch that never got an answer means, in the operator's words. */
function unanswered(error, origin) {
  const code = error?.cause?.code ?? error?.code ?? error?.name ?? "";
  return `${new URL(origin).hostname} does not answer yet (${code || error.message}): attach the custom domain in the dashboard and let its certificate issue, then run staging again.`;
}

/**
 * The addresses to check, from the build's folder.
 * @param {string} dist
 */
export function smokeAddresses(dist) {
  const read = (name) => JSON.parse(fs.readFileSync(path.join(dist, name), "utf8"));
  const version = fs.readFileSync(path.join(dist, "bundle-version.txt"), "utf8").trim();
  const onRequest = read("data/pairs.json").entries.find((entry) => !fs.existsSync(path.join(dist, entry.address, "index.html")));
  if (!onRequest) throw new Error("the build made every pair's page, so no page made on request can be checked");
  const gone = read("gone.json");
  const moved = gone.find((entry) => entry.to);
  // An old claim with no pair to lead to: gone, 410 (data/retired-addresses.json, scripts/redirects.mjs).
  const unmatched = gone.find((entry) => entry.gone);
  if (!moved) throw new Error("gone.json holds no old claim address that leads to a pair");
  if (!unmatched) throw new Error("gone.json holds no old claim address with no pair");
  return {
    version,
    checks: [
      { pathname: "/", status: 200 },
      { pathname: `/${onRequest.address}`, status: 200 },
      { pathname: onRequest.record, status: 200, type: /^application\/json\b/ },
      { pathname: `/${moved.slug}`, status: 301, location: `/${moved.to}` },
      { pathname: `/${unmatched.slug}`, status: 410 },
      { pathname: "/no-such--pair", status: 404 },
    ],
  };
}

/**
 * Check a staging deployment. Returns the lines it printed; throws with every failure named.
 * @param {{ origin: string, dist: string, request?: typeof fetch, attempts?: number, waitMs?: number }} options
 */
export async function checkStaging({ origin, dist, request = fetch, attempts = 6, waitMs = 10_000 }) {
  const { version, checks } = smokeAddresses(dist);
  const lines = [];
  const failures = [];
  const say = (line) => {
    lines.push(line);
    console.log(line);
  };

  async function answer(pathname) {
    let last;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      try {
        return await request(new URL(pathname, origin), { cache: "no-store", redirect: "manual", signal: AbortSignal.timeout(10_000) });
      } catch (error) {
        last = error;
        if (attempt < attempts) await wait(waitMs);
      }
    }
    throw Object.assign(new Error(unanswered(last, origin)), { unanswered: true });
  }

  // The version first: at the start of propagation the previous version can still answer.
  try {
    const response = await answer(`/bundle-version.txt?v=${version}`);
    const shown = (await response.text()).trim();
    if (response.status !== 200 || shown !== version) failures.push(`/bundle-version.txt names ${shown || "nothing"} (${response.status}), not bundle ${version}`);
    else say(`OK /bundle-version.txt names bundle ${version}`);
  } catch (error) {
    // Nothing answers: every other address would say the same.
    say(`FAIL ${error.message}`);
    throw new Error(error.message);
  }

  for (const check of checks) {
    let response;
    try {
      response = await answer(check.pathname);
    } catch (error) {
      failures.push(`${check.pathname}: ${error.message}`);
      continue;
    }
    const robots = response.headers.get("x-robots-tag") ?? "";
    const problems = [];
    if (response.status !== check.status) problems.push(`answered ${response.status}, not ${check.status}`);
    if (!/\bnoindex\b/i.test(robots)) problems.push(`carries X-Robots-Tag "${robots}", not noindex`);
    if (check.type && !check.type.test(response.headers.get("content-type") ?? "")) problems.push(`is ${response.headers.get("content-type")}, not JSON`);
    if (check.location && new URL(response.headers.get("location") ?? "", origin).pathname !== check.location) {
      problems.push(`leads to ${response.headers.get("location")}, not ${check.location}`);
    }
    await response.body?.cancel().catch(() => {});
    if (problems.length) failures.push(`${check.pathname} ${problems.join("; ")}`);
    else say(`OK ${check.pathname} ${check.status}, noindex`);
  }
  for (const failure of failures) say(`FAIL ${failure}`);
  if (failures.length) throw new Error(`Staging failed ${failures.length} of ${checks.length + 1} checks.`);
  say(`Staging passed all ${checks.length + 1} checks at ${origin}.`);
  return lines;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [origin, dist = "dist"] = process.argv.slice(2);
  if (!origin) {
    console.error("Usage: node scripts/staging-smoke.mjs STAGING_ORIGIN [DIST]");
    process.exit(2);
  }
  try {
    await checkStaging({ origin, dist });
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
