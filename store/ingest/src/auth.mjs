// Who is asking, and what that token may do. A token is known to the service only by its
// SHA-256, read from the secret INGEST_TOKENS: a JSON list of {name, role, device?, sha256}.
// Revoking one is removing its entry; the others are untouched. A token is never logged,
// echoed or stored, and nothing here says why a token was not accepted.
import { ACTIONS, KINDS } from "./kinds.mjs";
import { sha256 } from "./hash.mjs";

const RECORDS = KINDS.filter((kind) => kind !== "action");

// What each kind of token may do: least scope each.
//   writers   the kinds of run it may register; it reaches only runs it could have registered
//   kinds     the kinds of record it may stage
//   actions   the operator's commands it may state (an `action` record)
//   deciders  whose decision a record it stages may carry (reviewed_by, decided_by, labelled_by)
//   withheld  fields of a record it may not send
//   holds     whether a claim it hands over as approved must carry its audit hold
//   may       what else it may ask for
export const ROLES = {
  // A device's backfill: records, payloads, work slices. No action: it cannot clear an
  // audit, archive, publish, merge or rename. A device runs scripts, and a script's
  // decision is never recorded as a person's or an assistant's: those travel only with the
  // operator's token. A claim it hands over as approved carries its audit hold, unless
  // the store already holds that claim approved and released.
  device: { writers: ["device"], kinds: RECORDS, actions: [], deciders: ["rule", "seed"], holds: true, may: ["payload", "slice"] },
  // The daily job: a schedule has no person in it, so no person's or assistant's decision.
  // It is the bulk file's one writer, so it reads the inbox of bulk records and clears it.
  daily: { writers: ["daily"], kinds: RECORDS, actions: [], deciders: ["rule", "seed"], may: ["payload", "inbox"] },
  // A reader's lookup: the lead, its reader share, the trials found, its reading, its spend.
  // No claim, no event, no match, no decision of anyone's, no action, and no tie from a
  // lead to a claim.
  lookup: { writers: ["lookup"], kinds: ["link_lead", "link_share", "payload", "registry_trial", "lead_reading", "usage", "unlisted_domain"], actions: [], deciders: [], withheld: ["claim_slug"], may: ["payload"] },
  // The store-side consumer: what processing a lead and `prepare` produce, by rule.
  consumer: { writers: ["consumer"], kinds: RECORDS, actions: [], deciders: ["rule"], may: ["payload", "work"] },
  // The export: sets a published time, by rule, and nothing else.
  export: { writers: ["export"], kinds: ["action"], actions: ["publish"], deciders: ["rule"], may: [] },
  // The operator: everything a device may, the migration, and every action.
  operator: { writers: ["operator", "migration"], kinds: KINDS, actions: ACTIONS, deciders: ["human", "assistant", "rule", "seed"], may: ["payload", "slice", "work", "inbox"] },
};

// Compared in full whatever the first difference, so the time taken says nothing.
function same(a, b) {
  let diff = a.length ^ b.length;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i % (b.length || 1));
  return diff === 0;
}

// The token's entry, or null. Every entry is compared, so a revoked token and one never
// issued take the same time.
export async function principal(request, env) {
  const given = /^Bearer ([A-Za-z0-9._~+/=-]{20,200})$/.exec(request.headers.get("authorization") || "");
  let entries = [];
  try { entries = JSON.parse(env.INGEST_TOKENS || "[]"); } catch { entries = []; }
  if (!given || !Array.isArray(entries)) return null;
  const digest = await sha256(given[1]);
  let found = null;
  for (const entry of entries) {
    if (entry && typeof entry.sha256 === "string" && same(digest, entry.sha256.toLowerCase()) && ROLES[entry.role]) found = entry;
  }
  if (!found || (found.role === "device" && !found.device)) return null;
  return { name: String(found.name || found.role), role: found.role, device: found.device || null, withheld: [], holds: false, ...ROLES[found.role] };
}
