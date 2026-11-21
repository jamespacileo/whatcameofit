// Who may read the review site. Cloudflare Access stands in front of the whole host and signs
// each request it lets through with a JWT in `Cf-Access-Jwt-Assertion`. The Worker checks that
// token again on every request, so a missing or mistaken Access policy never opens the site:
// Cloudflare's guidance is to validate the token rather than trust the header's presence
// (https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/).
// The policy itself (Palladio account members, signed in with the Cloudflare identity
// provider) lives in Access; the operator allowlist is checked here too, as the proposal
// `private-content-review` asks, so that the two must agree before anyone reads.
import { createRemoteJWKSet, jwtVerify } from "jose";

/** One key set per team domain, kept across requests: jose refetches it when a key id is new,
 * which covers Access's key rotation (about every six weeks, old keys valid for seven days). */
const keySets = new Map();

function keySet(teamDomain) {
  if (!keySets.has(teamDomain)) keySets.set(teamDomain, createRemoteJWKSet(new URL("/cdn-cgi/access/certs", teamDomain)));
  return keySets.get(teamDomain);
}

/** The settings a request is checked against, or null when any is missing: the site then
 * answers no one, rather than everyone. Issuer and audience are both set explicitly (the
 * operator, 2026-11-21): the issuer is the team domain Access signs as, and its key set is
 * read from that same origin, so no setting is derived from another. */
export function accessSettings(env) {
  const teamDomain = env.ACCESS_ISSUER?.trim();
  const audience = env.ACCESS_AUD?.trim();
  const operators = (env.OPERATOR_EMAILS ?? "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  if (!teamDomain || !/^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com$/.test(teamDomain) || !audience || !operators.length) return null;
  return { teamDomain, audience, operators: new Set(operators) };
}

/**
 * The signed-in operator's email, or null when the request may not read.
 * @param {Request} request
 * @param {{ teamDomain: string, audience: string, operators: Set<string> }} settings
 */
export async function operatorOf(request, settings) {
  const token = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, keySet(settings.teamDomain), {
      issuer: settings.teamDomain,
      audience: settings.audience,
      algorithms: ["RS256"],
      // jose checks `exp` only when the token carries one, so a token without it would never
      // expire. Access always sets it; a token that lacks it is refused.
      requiredClaims: ["exp"],
    });
    const email = typeof payload.email === "string" ? payload.email.toLowerCase() : null;
    return email && settings.operators.has(email) ? email : null;
  } catch {
    return null;
  }
}
