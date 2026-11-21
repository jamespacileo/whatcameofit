// What a host actually serves, as distinct from what its store holds: a bundle can be loaded
// into D1 (current = 1) before a deployment builds from it, so the two can differ. Every site
// deploy writes the commit it was built from to /build-revision.txt and the bundle version to
// /bundle-version.txt (site/scripts/deploy.mjs); staging-smoke.mjs reads the same two files.

const VERSION = /^[a-f0-9]{16}$/;
const REVISION = /^[a-f0-9]{40}$/;

async function line(origin, pathname, shape) {
  try {
    const response = await fetch(new URL(pathname, origin), { redirect: "manual", cache: "no-store", signal: AbortSignal.timeout(5000) });
    if (response.status !== 200) {
      await response.body?.cancel();
      return null;
    }
    const text = (await response.text()).trim();
    return shape.test(text) ? text : null;
  } catch {
    return null;
  }
}

/** The revision and bundle a host says it serves; either is null when the host does not say. */
export async function published(origin) {
  if (!origin) return null;
  const [revision, bundle] = await Promise.all([line(origin, "/build-revision.txt", REVISION), line(origin, "/bundle-version.txt", VERSION)]);
  return { host: new URL(origin).host, revision, bundle };
}
