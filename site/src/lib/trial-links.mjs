// The same rule powers the claim-page links and the server's record allowlist.
export function trialDetailsPath(address) {
  if (typeof address !== "string") return null;
  try {
    const url = new URL(address);
    if (url.protocol !== "https:" || url.hostname !== "clinicaltrials.gov" || url.port || url.username || url.password) return null;
    const id = url.pathname.match(/^\/(?:study|ct2\/show)\/(NCT\d{8})\/?$/)?.[1];
    return id ? `/trials/${id}` : null;
  } catch { return null; }
}

export function buildTrialIndex(data) {
  const trials = {};
  for (const claim of data.claims ?? []) {
    const urls = [
      ...(claim.events ?? []).map(event => event.source_url),
      ...(claim.matches ?? []).map(match => match.url),
    ];
    for (const address of urls) {
      const local = trialDetailsPath(address);
      if (!local) continue;
      const id = local.split("/").at(-1);
      const claims = trials[id] ??= [];
      if (!claims.some(item => item.slug === claim.slug)) {
        claims.push({ slug: claim.slug, headline: claim.headline });
      }
    }
  }
  return { trials };
}
