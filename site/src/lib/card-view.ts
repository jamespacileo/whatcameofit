// A knowledge card: what one treatment, condition or group is, and where it sits in each tree
// that classifies it (design "Browsing by hierarchy, picking several, and knowledge cards",
// https://claude.ai/artifact/7Ge7Qvqct18XkwheBMKWTN, operator's ask of 2026-11-20 16:50).
//
// One shape for every kind of entity, after the established cards that are generated rather
// than written: Google's knowledge panel (name, type, key facts, related things), the
// Wikidata infobox (every fact a statement read from a source) and the Open Targets and
// DrugBank headers (name, type, other names, classification). So a card is built from fixed
// slots, never free text, and a slot with nothing in the page file is left out rather than
// filled from somewhere else. Codes stay in addresses: a card shows names only.
//
// Pure, so a card built ahead and one the Worker makes on request are the same.
import { shownName } from "./pair-view.ts";
import { PAIR_APPROACH_LABELS, TREE_LABELS } from "./pair-wording.ts";

export interface CardLink {
  label: string;
  href?: string;
}

export interface CardFact {
  label: string;
  values: CardLink[];
}

/** One place the entity sits in one tree: the tree's name, then its path from the top. */
export interface CardPlace {
  tree: string;
  path: CardLink[];
}

export interface CardView {
  kind: "treatment" | "condition";
  name: string;
  /** What kind of thing it is, in the site's words. */
  type: string;
  facts: CardFact[];
  places: CardPlace[];
}

const approachLabel = (code: string | null | undefined): string | null =>
  code && Object.hasOwn(PAIR_APPROACH_LABELS, code) ? PAIR_APPROACH_LABELS[code] : null;

/** A treatment's card, from its `PairInterventionPage` file: its other names, whether it is a
 * combination, and its kind of treatment as a place in that tree. */
export function treatmentCard(file: any): CardView {
  const preferred = file.intervention.preferred_name;
  const otherNames = [
    ...new Set(
      file.names
        .filter((held: any) => held.role !== "preferred" && held.name.toLowerCase() !== preferred.toLowerCase())
        .map((held: any) => shownName(held.name)),
    ),
  ] as string[];
  // A regimen's components are intervention keys, not names (`Intervention.components`), and a
  // card shows no codes, so it says only that the treatment is a combination until the lab's
  // page file names its parts.
  const combination = (file.intervention.components ?? []).length > 0;
  const approach = approachLabel(file.approach?.approach);
  return {
    kind: "treatment",
    name: shownName(preferred),
    type: combination ? "Combination treatment" : "Treatment",
    facts: otherNames.length ? [{ label: "Also known as", values: otherNames.map((label) => ({ label })) }] : [],
    // The registry's intervention type, read by rule (`approach.basis`). A treatment the rule
    // gives no kind has no place in this tree, and the card says nothing rather than guess.
    places: approach ? [{ tree: TREE_LABELS.approach, path: [{ label: approach }] }] : [],
  };
}

/** A MeSH descriptor as page files carry it. */
interface Descriptor {
  descriptor_id: string;
  label: string;
  tree_numbers: string[];
}

/**
 * A condition's places in MeSH: one path per tree number, each step named by a descriptor the
 * page file holds. MeSH is a polyhierarchy, one descriptor in several branches with none
 * primary (NLM, https://www.nlm.nih.gov/mesh/intro_trees.html), so every branch is shown, as
 * ClinicalTrials.gov lists every ancestor. A step no descriptor in the file names is left out
 * of the path instead of shown as its code; the lab's tree files will name every step.
 * Paths that come out the same once unnamed steps are dropped are shown once.
 */
export function meshPlaces(descriptor: Descriptor, known: Descriptor[], hrefOf: (descriptorId: string) => string | undefined): CardPlace[] {
  const byNumber = new Map<string, Descriptor>();
  for (const one of [...known, descriptor]) for (const number of one.tree_numbers) byNumber.set(number, one);
  const seen = new Set<string>();
  const places: CardPlace[] = [];
  for (const number of [...descriptor.tree_numbers].sort()) {
    const parts = number.split(".");
    const path: CardLink[] = [];
    for (let depth = 1; depth <= parts.length; depth++) {
      const step = byNumber.get(parts.slice(0, depth).join("."));
      if (!step || path.some((held) => held.label === step.label)) continue;
      const href = step.descriptor_id === descriptor.descriptor_id ? undefined : hrefOf(step.descriptor_id);
      path.push({ label: step.label, ...(href ? { href } : {}) });
    }
    const said = path.map((step) => step.label).join("|");
    if (path.length > 1 && !seen.has(said)) {
      seen.add(said);
      places.push({ tree: TREE_LABELS.mesh, path });
    }
  }
  return places;
}

/** A condition's or clinical category's card: its name and where it sits in MeSH. */
export function conditionCard(descriptor: Descriptor, known: Descriptor[], hrefOf: (descriptorId: string) => string | undefined): CardView {
  return {
    kind: "condition",
    name: descriptor.label,
    type: "Condition",
    facts: [],
    places: meshPlaces(descriptor, known, hrefOf),
  };
}
