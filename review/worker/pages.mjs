// The page inventory (openspec change `review-dashboard`, phase 3): every address the public
// site answers for a pair or for an old claim, and what decides each answer.
//
// Two sources, never merged into one verdict:
//   - the store's bundle (D1): each pair's address, and the lab's claim scope
//     (PairClaimScopePage, thenwhat-lab #174): which old claims it verified to lead to a pair of
//     their scope, and which it holds, with the pair each would lead to and why it is held;
//   - what staging was published with: gone.json (301s and 410s), kept-claims.json (claims
//     that keep their own page), held-redirects.json (claims the site held from a pair of
//     another scope) and the kept claims' search entries in lookup/2.json, all written by
//     site/scripts/redirects.mjs.
// A held claim is shown with the pair it would lead to beside its own kept page. Neither source
// is read as a redirect the other did not make (the operator, 2026-11-21: "show a held address
// alongside an original kept page rather than inferring a redirect"). Where they differ, the row
// says so.
import { allow, read } from "./reads.mjs";
import { bundleFor, joined, present, VERSION } from "./inventory.mjs";

const S = {
  pairs: allow(
    "SELECT p.address, i.preferred_name AS treatment, c.label AS condition, p.status_code, p.trials, p.claim_slug " +
      "FROM pair p JOIN pair_intervention i ON i.version = p.version AND i.id = p.intervention_id " +
      "JOIN pair_condition c ON c.version = p.version AND c.descriptor_id = p.condition_id " +
      "WHERE p.version = ? ORDER BY p.address",
  ),
  scopeParts: allow("SELECT body FROM pair_page WHERE version = ? AND model = 'PairClaimScopePage' AND key = 'claim-scope' ORDER BY part"),
};

/** The files staging was published with that say what each old address answers. */
const FILES = ["gone.json", "kept-claims.json", "held-redirects.json", "lookup/2.json"];

async function file(origin, pathname) {
  try {
    const response = await fetch(new URL(pathname, origin), { redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(8000) });
    if (response.status !== 200) {
      await response.body?.cancel();
      return { pathname, status: response.status, body: null };
    }
    return { pathname, status: 200, body: await response.json() };
  } catch (error) {
    return { pathname, status: null, error: String(error?.message ?? error), body: null };
  }
}

/** What staging's own files say an old claim address answers. */
function siteAnswers({ gone, kept, held, lookup }) {
  const answers = new Map();
  for (const entry of Array.isArray(gone) ? gone : []) {
    if (entry.on) answers.set(entry.slug, { answer: "archived", status: 410, on: entry.on });
    else if (entry.kept) answers.set(entry.slug, { answer: "leads to a kept claim", status: 301, to: `/${entry.to}` });
    else if (entry.to) answers.set(entry.slug, { answer: "leads to a pair", status: 301, to: `/${entry.to}` });
    else answers.set(entry.slug, { answer: "gone", status: 410 });
  }
  for (const slug of Array.isArray(kept) ? kept : []) {
    const entry = lookup?.kept?.[slug];
    answers.set(slug, { answer: "kept page", status: 200, title: entry?.headline ?? null, searchable: !!entry });
  }
  const heldFrom = new Map((Array.isArray(held) ? held : []).map((entry) => [entry.slug, entry.pair]));
  return { answers, heldFrom };
}

/** The lab's claim scope, by slug: verified to lead to a pair, or held with a reason. */
function labScope(scope) {
  const bySlug = new Map();
  for (const { slug, pair } of scope?.redirects ?? []) bySlug.set(slug, { scope: "verified", pair });
  for (const { slug, pair, reason } of scope?.held ?? []) bySlug.set(slug, { scope: "held", pair, reason });
  return bySlug;
}

/**
 * Where the two sources part: the lab verified a redirect staging does not make, or holds a
 * claim staging leads to a pair. Each is named, not resolved: which one is right is the
 * operator's call (the site's data/redirect-scope.json lists the redirects it has verified).
 */
function differences(site, lab) {
  if (!lab || !site) return null;
  if (lab.scope === "verified" && !(site.status === 301 && site.to === `/${lab.pair}`)) {
    return `The lab verified /${lab.pair}; staging answers ${site.status} (${site.answer}).`;
  }
  if (lab.scope === "held" && site.status === 301 && site.answer === "leads to a pair") {
    return `The lab holds this claim (${lab.reason}); staging leads it to ${site.to}.`;
  }
  return null;
}

/**
 * Every address, from staging's store (bound to one bundle version) and staging's published
 * files. `version` null reads the current bundle.
 */
export async function pages(db, origin, version = null) {
  if (version !== null && !VERSION.test(version)) return { bad: "version" };
  const tables = await present(db);
  const bundle = await bundleFor(db, tables, version);
  if (bundle?.gone) return bundle;
  const [pairRows, scopeParts, ...fetched] = await Promise.all([
    bundle && tables.has("pair") ? read(db, S.pairs, bundle.version) : [],
    bundle && tables.has("pair_page") ? read(db, S.scopeParts, bundle.version) : [],
    ...FILES.map((name) => (origin ? file(origin, `/${name}`) : { pathname: `/${name}`, status: null, body: null })),
  ]);
  const [gone, kept, held, lookup] = fetched.map((one) => one.body);
  const scope = scopeParts.length ? joined(scopeParts) : null;
  const { answers, heldFrom } = siteAnswers({ gone, kept, held, lookup });
  const lab = labScope(scope);

  const rows = pairRows.map((pair) => ({
    address: `/${pair.address}`,
    kind: "pair",
    title: `${pair.treatment} for ${pair.condition}`,
    status: pair.status_code,
    trials: pair.trials,
    claim: pair.claim_slug,
  }));
  for (const slug of [...new Set([...answers.keys(), ...lab.keys()])].sort()) {
    const site = answers.get(slug) ?? null;
    const scoped = lab.get(slug) ?? null;
    rows.push({
      address: `/${slug}`,
      kind: "old claim",
      title: site?.title ?? null,
      site,
      // The site held it from this pair (held-redirects.json): shown beside its own page.
      heldFrom: heldFrom.has(slug) ? `/${heldFrom.get(slug)}` : null,
      lab: scoped && { ...scoped, pair: scoped.pair ? `/${scoped.pair}` : null },
      differs: differences(site, scoped),
    });
  }
  const count = (test) => rows.filter(test).length;
  return {
    version: bundle?.version ?? null,
    current: bundle ? bundle.current === 1 || version === null : null,
    origin: origin ?? null,
    files: fetched.map(({ pathname, status, error }) => ({ pathname, status, ...(error ? { error } : {}) })),
    scope: scope ? { redirects: scope.redirects?.length ?? 0, held: scope.held?.length ?? 0 } : null,
    counts: {
      pairs: count((r) => r.kind === "pair"),
      kept: count((r) => r.site?.status === 200),
      redirects: count((r) => r.site?.status === 301),
      gone: count((r) => r.site?.status === 410),
      held: count((r) => r.lab?.scope === "held" || r.heldFrom),
      differs: count((r) => r.differs),
    },
    rows,
  };
}

/** Paths an operator may ask staging about: one absolute path, no scheme, host or dot segments. */
const PATH = /^\/[A-Za-z0-9._~!$&'()*+,;=:@%/-]{0,300}$/;

/**
 * What staging answers for one path, without following a redirect: the status, where a
 * redirect leads, and the headers that say how the page is served. Only staging's own origin
 * is asked; a path that would leave it is refused.
 */
export async function check(origin, pathname) {
  if (!origin) return { error: "no staging address configured" };
  if (!PATH.test(pathname) || pathname.startsWith("//") || /(^|\/)\.\.?(\/|$)/.test(pathname)) return { bad: "path" };
  const url = new URL(pathname, origin);
  if (url.origin !== new URL(origin).origin) return { bad: "path" };
  try {
    const response = await fetch(url, { redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(8000) });
    await response.body?.cancel();
    const header = (name) => response.headers.get(name);
    return {
      url: url.href,
      status: response.status,
      location: header("Location"),
      type: header("Content-Type"),
      robots: header("X-Robots-Tag"),
      cache: header("Cache-Control"),
    };
  } catch (error) {
    return { url: url.href, status: null, error: String(error?.message ?? error) };
  }
}
