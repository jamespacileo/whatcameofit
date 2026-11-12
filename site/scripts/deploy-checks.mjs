// What must be true before the site is deployed. Pure: no files, no network.
// Behaviour: openspec deployment.

const LOCAL_HOST = /^(localhost|.+\.localhost|.+\.test|127(\.\d{1,3}){3}|0\.0\.0\.0|\[::1\])$/i;
const NAMED_AT_MOST = 5;

function addressProblem(siteUrl) {
  if (!siteUrl) {
    return "SITE_URL is not set. Set it to the public address, for example SITE_URL=https://example.org.";
  }
  let address;
  try {
    address = new URL(siteUrl);
  } catch {
    return `SITE_URL is "${siteUrl}", which is not an address. Use the form https://example.org.`;
  }
  if (LOCAL_HOST.test(address.hostname)) {
    return `SITE_URL is ${siteUrl}, a local address. Set it to the public address.`;
  }
  if (address.protocol !== "https:") {
    return `SITE_URL is ${siteUrl}. The public address must start with https://.`;
  }
  if (address.pathname !== "/" || address.search || address.hash) {
    return `SITE_URL is ${siteUrl}. It must be the site's address alone, with nothing after the domain.`;
  }
  return null;
}

/**
 * Why this export must not be deployed to this address: one sentence each, all at once.
 * An empty list means the deployment may go ahead.
 */
export function deployProblems({ data, siteUrl }) {
  const problems = [];

  const address = addressProblem(siteUrl);
  if (address) problems.push(address);

  if (data.preview) {
    problems.push(
      "The export is a preview: it holds claims decided by the assistant. A preview is never deployed. Write a normal export first (make public-export).",
    );
  }

  const claims = data.claims ?? [];
  if (claims.length === 0) {
    problems.push("The export holds no claims. There is nothing to publish.");
  }

  const unchecked = claims.filter((claim) => !claim.checked_by_person).map((claim) => claim.slug);
  if (unchecked.length > 0) {
    const named = unchecked.slice(0, NAMED_AT_MOST).join(", ");
    const more =
      unchecked.length > NAMED_AT_MOST ? ` and ${unchecked.length - NAMED_AT_MOST} more` : "";
    problems.push(
      `${unchecked.length} of ${claims.length} ${unchecked.length === 1 ? "claim has" : "claims have"} not been checked by a person: ${named}${more}. Approve each yourself (thenwhat review approve claim ID), then export again.`,
    );
  }

  return problems;
}
