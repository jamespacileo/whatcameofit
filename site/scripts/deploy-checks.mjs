// What must be true before the site is deployed. Pure: no files, no network.
// Behaviour: openspec deployment.

// Hosts that are never a public address: this machine, and names kept for local use
// and testing. The public-build check in src/lib/public-build.ts refuses the same.
export const LOCAL_HOST = /^(localhost|.+\.localhost|.+\.test|127(\.\d{1,3}){3}|0\.0\.0\.0|\[::1\])$/i;

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
 * The Worker that serves one pull request's copy of the site, or null when the
 * number is not a pull request's. The name is the only thing that separates a
 * copy from production, so nothing but a plain positive number is accepted.
 */
export function pullRequestWorker(number) {
  return /^[1-9]\d{0,6}$/.test(String(number ?? "")) ? `thenwhat-pr-${number}` : null;
}

/**
 * Why the site must not be deployed to this address: one sentence each, all at once.
 * An empty list means the deployment may go ahead.
 */
export function deployProblems({ siteUrl }) {
  const address = addressProblem(siteUrl);
  return address ? [address] : [];
}

const NOT_YET_REGISTERED = /\[code: 10007\]/;
const HALF_REGISTERED = /Cannot read properties of null \(reading 'tag'\)/;

/**
 * Whether a failed preview publish is sent again, from what Wrangler printed, and whether this
 * publish has now seen Cloudflare not yet know the new Worker.
 *
 * A pull request's first publish creates its Worker, and Cloudflare can answer "This Worker
 * does not exist on your account. [code: 10007]" before it has registered it (pull requests
 * 368 and 369). The next send can then find it half registered: Wrangler reads
 * `default_environment.script.tag` from /workers/services/{name} with no null check and stops
 * with "Cannot read properties of null (reading 'tag')" (pull request 383, run 44738112545).
 * Wrangler 4.165 reads the field the same way, so an upgrade does not help. That second answer
 * is sent again only after a 10007 in the same publish; from any other cause it stops at once.
 * @param {string} said Wrangler's output of one send
 * @param {boolean} unregistered whether an earlier send of this publish got a 10007
 */
export function publishAgain(said, unregistered) {
  const missing = NOT_YET_REGISTERED.test(said);
  const seen = unregistered || missing;
  return { again: missing || (seen && HALF_REGISTERED.test(said)), unregistered: seen };
}
