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

// A claim cites a trial through its events and its approved matches. A candidate match
// may only be about the claim and counts for nothing, so a claim that reaches a trial by
// a candidate alone is marked possible (openspec registry-record-rows).
export function buildTrialIndex(data) {
  const trials = {};
  for (const claim of data.claims ?? []) {
    const citing = [
      ...(claim.events ?? []).map(event => event.source_url),
      ...(claim.matches ?? []).filter(match => match.state !== "candidate").map(match => match.url),
    ];
    const possible = (claim.matches ?? []).filter(match => match.state === "candidate").map(match => match.url);
    for (const [urls, isPossible] of [[citing, false], [possible, true]]) {
      for (const address of urls) {
        const local = trialDetailsPath(address);
        if (!local) continue;
        const id = local.split("/").at(-1);
        const claims = trials[id] ??= [];
        if (claims.some(item => item.slug === claim.slug)) continue;
        claims.push(
          isPossible
            ? { slug: claim.slug, headline: claim.headline, possible: true }
            : { slug: claim.slug, headline: claim.headline },
        );
      }
    }
  }
  return { trials };
}
