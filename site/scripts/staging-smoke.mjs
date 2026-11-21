// The checks a staging deployment must pass before it counts (docs/deploy.md, "Staging"). Run by
// the staging job after each deploy, against staging's own address, with the build's folder:
//
//   node scripts/staging-smoke.mjs https://staging.whatcameofit.com dist <commit>
//
// Each address must answer with its expected status and carry X-Robots-Tag: noindex: a built
// page, a pair page and its data file made on request, an old claim address that leads to its
// pair (301), a claim with no pair that keeps its page and its data record (200, as production
// built them: scripts/kept-claims.mjs), one the operator archived (410), and an address no pair
// has (404). First, /build-revision.txt
// must name the commit deployed and /bundle-version.txt the bundle the build was made from: a
// deployment of new code with the same bundle could otherwise be answered by the version before.
// Both are asked again, a bounded number of times, while the new version spreads. The addresses are read from the build itself, so the
// checks follow whatever bundle staging holds. An address that does not answer at all (no DNS
// record yet, no certificate yet) fails, and says so: it never counts as a pass.
import fs from "node:fs";
import path from "node:path";
import { setTimeout as wait } from "node:timers/promises";
import { factsLine } from "./bundle-facts.mjs";

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
  const moved = gone.find((entry) => entry.to && !entry.kept);
  // An old claim with no pair to lead to keeps its page (kept-claims.json, scripts/redirects.mjs);
  // one the operator archived is gone, 410 (data/retired-addresses.json).
  const [kept] = read("kept-claims.json");
  const archived = gone.find((entry) => entry.on);
  if (!moved) throw new Error("gone.json holds no old claim address that leads to a pair");
  if (!kept) throw new Error("the build kept no claim's page: was it built with KEPT_CLAIMS_DIR?");
  if (!archived) throw new Error("gone.json holds no archived claim address");
  return {
    version,
    checks: [
      { pathname: "/", status: 200 },
      { pathname: `/${onRequest.address}`, status: 200 },
      { pathname: onRequest.record, status: 200, type: /^application\/json\b/ },
      { pathname: `/${moved.slug}`, status: 301, location: `/${moved.to}` },
      { pathname: `/${kept}`, status: 200, type: /^text\/html\b/ },
      { pathname: `/data/claims/${kept}.json`, status: 200, type: /^application\/json\b/ },
      { pathname: `/${archived.slug}`, status: 410 },
      { pathname: "/no-such--pair", status: 404 },
    ],
  };
}

/**
 * Check a staging deployment. Returns the lines it printed; throws with every failure named.
 * @param {{ origin: string, dist: string, request?: typeof fetch, attempts?: number, waitMs?: number }} options
 */
export async function checkStaging({ origin, dist, revision, request = fetch, attempts = 6, waitMs = 10_000 }) {
  if (!/^[0-9a-f]{40}$/.test(revision ?? "")) throw new Error("The commit deployed is needed to check staging: a full SHA.");
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

  // What was deployed first: at the start of propagation the version before can still answer.
  // Asked again until it names what was deployed, or the attempts run out.
  async function names(pathname, expected, what) {
    let shown = "";
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      const response = await answer(`${pathname}?v=${expected}`);
      shown = response.status === 200 ? (await response.text()).trim() : `nothing (${response.status})`;
      if (shown === expected) return say(`OK ${pathname} names ${what} ${expected}`);
      if (attempt < attempts) await wait(waitMs);
    }
    failures.push(`${pathname} names ${shown}, not ${what} ${expected}, after ${attempts} attempts`);
  }
  try {
    await names("/build-revision.txt", revision, "commit");
    await names("/bundle-version.txt", version, "bundle");
    // What that bundle holds (scripts/bundle-facts.mjs), printed for the person reading the run:
    // part of the bundle's check, so a facts file of another bundle fails it.
    const facts = await answer(`/bundle-manifest.json?v=${version}`);
    const held = facts.status === 200 ? await facts.json() : null;
    if (held?.version !== version) failures.push(`/bundle-manifest.json names ${held?.version ?? `nothing (${facts.status})`}, not bundle ${version}`);
    else if (held.pairs !== held.counts?.PairPage) failures.push(`/bundle-manifest.json counts ${held.pairs} pair pages, but its manifest ${held.counts?.PairPage}`);
    else say(`   ${factsLine(held)}`);
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
    if (check.type && !check.type.test(response.headers.get("content-type") ?? "")) problems.push(`is ${response.headers.get("content-type")}, not ${check.type}`);
    // The whole address, origin included: a redirect out of staging fails.
    const expected = check.location ? new URL(check.location, origin).href : null;
    if (expected && new URL(response.headers.get("location") ?? "", new URL(check.pathname, origin)).href !== expected) {
      problems.push(`leads to ${response.headers.get("location")}, not ${expected}`);
    }
    await response.body?.cancel().catch(() => {});
    if (problems.length) failures.push(`${check.pathname} ${problems.join("; ")}`);
    else say(`OK ${check.pathname} ${check.status}, noindex`);
  }
  for (const failure of failures) say(`FAIL ${failure}`);
  if (failures.length) throw new Error(`Staging failed ${failures.length} of ${checks.length + 2} checks.`);
  say(`Staging passed all ${checks.length + 2} checks at ${origin}.`);
  return lines;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const [origin, dist = "dist", revision] = process.argv.slice(2);
  if (!origin || !revision) {
    console.error("Usage: node scripts/staging-smoke.mjs STAGING_ORIGIN DIST COMMIT");
    process.exit(2);
  }
  try {
    await checkStaging({ origin, dist, revision });
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }
}
