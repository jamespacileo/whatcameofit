// Reassociate completed clinical readings with the available publication index.
// Pure: fresh lookups and reused answers share the same exact claim boundaries.
import { nameKey, regimenKeys, regimenParts } from "./names.mjs";

export function withCurrentClaims(found, index) {
  if (Array.isArray(found?.claims)) return { ...found, tracked: [], claims: found.claims.map(claim => withCurrentClaims(claim, index)) };
  // Exact source-address responses have no clinical reading to reassociate.
  if (found?.about_a_treatment !== true) return found;
  const names = (Array.isArray(found.names) && found.names.length ? found.names : [found.treatment])
    .filter(name => typeof name === "string" && name.trim());
  // Model-known names also include individual regimen components, so they are
  // search terms only. The names stated as whole aliases can associate a card.
  const wanted = new Set(regimenKeys(names));
  const indication = nameKey(found.condition);
  // The Worker's index is version 2 as read by src/lib/lookup-file.mjs (`pairs`); the
  // released extension, which copies this file at build, still holds version 1 (`claims`).
  // Both carry `indication`, `headline` and `page` on each entry.
  const cards = Object.entries(index?.pairs ?? index?.claims ?? {})
    .filter(([, claim]) => indication && nameKey(claim.indication) === indication)
    .map(([slug, claim]) => ({ slug, claim, keys: regimenKeys(claim.names ?? []) }));
  const primary = regimenKeys(names.slice(0, 1))[0];
  const namedCards = cards.filter(card => card.keys.includes(primary));
  const primaryParts = regimenParts(names.slice(0, 1)).filter(parts => parts.length > 1);
  const namedParts = regimenParts(namedCards.flatMap(card => card.claim.names ?? [])).filter(parts => parts.length > 1);
  const fullRegimens = new Set((primaryParts.length ? primaryParts : namedParts.length ? namedParts :
    regimenParts(names).filter(parts => parts.length > 1)).map(parts => JSON.stringify(parts)));
  // A component's brand can look like a whole-regimen alias in a model reading.
  // The published card's own aliases establish that it is actually a component.
  // A named regimen's primary card can also supply its explicit component names.
  const wholeNames = [...names, ...namedCards.flatMap(card => card.claim.names ?? [])];
  const components = new Set(regimenParts(wholeNames).filter(parts => parts.length > 1)
    .flatMap(parts => parts.map(part => JSON.stringify([part]))));
  // Recorded whole aliases already establish equivalence. A direct primary
  // match outranks model-supplied aliases; these cannot add a component card.
  const associated = namedCards.length ? namedCards : cards
    .filter(card => card.keys.some(name => wanted.has(name)) && !card.keys.some(name => components.has(name)))
    .filter(card => {
      const sets = new Set(regimenParts(card.claim.names ?? []).filter(parts => parts.length > 1)
        .map(parts => JSON.stringify(parts)));
      return !fullRegimens.size || !sets.size && fullRegimens.size === 1 ||
        [...fullRegimens].every(parts => sets.has(parts));
    });
  const tracked = associated
    .map(({ slug, claim }) => ({ slug, headline: claim.headline, page: claim.page }))
    .sort((a, b) => a.slug.localeCompare(b.slug));
  return { ...found, tracked };
}
