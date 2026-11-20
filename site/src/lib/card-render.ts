// A knowledge card as HTML (card-view.ts): one renderer for a card built ahead and one the
// Worker makes on request, so the two are the same. Every value goes through `escape`.
import type { CardLink, CardView } from "./card-view.ts";
import { escape } from "./pair-render.ts";

const linked = (step: CardLink) => (step.href ? `<a href="${escape(step.href)}">${escape(step.label)}</a>` : escape(step.label));

/** The card: name and kind, then its facts, then one line per place it sits in a tree. A card
 * with nothing past its name draws no box. */
export function renderCard(card: CardView): string {
  if (card.facts.length === 0 && card.places.length === 0) return "";
  const facts = card.facts.map(
    (fact) => `<div class="card-fact"><dt>${escape(fact.label)}</dt><dd>${fact.values.map(linked).join(", ")}</dd></div>`,
  );
  const places = card.places.map(
    (place) =>
      `<div class="card-fact" data-tree="${escape(place.tree)}"><dt>${escape(place.tree)}</dt>` +
      `<dd><nav aria-label="${escape(`${card.name} in ${place.tree.toLowerCase()}`)}">${place.path.map(linked).join(" › ")}</nav></dd></div>`,
  );
  return (
    `<aside class="knowledge-card" data-card="${escape(card.kind)}" aria-label="About ${escape(card.name)}">` +
    `<p class="card-type">${escape(card.type)}</p>` +
    `<dl>${[...facts, ...places].join("")}</dl>` +
    `</aside>`
  );
}
