// Clinical categories: MeSH descriptors, in NLM's own names and NLM's own hierarchy.
// The export gives each claim its categories and, once, the part of the tree they sit in.
// Everything here is worked out from those two, with no wording of the site's own for a
// category. Openspec site-publishing: "Clinical index", "Clinical category page".

export interface MeshNode {
  identifier: string;
  label: string;
  tree_numbers: string[];
  /** The descriptors directly broader. Empty at the top of a tree. */
  broader: string[];
}

export interface Clinical {
  mesh_years: string[];
  nodes: MeshNode[];
  claims_not_read?: number;
}

export interface CategorySource {
  /**
   * A trial or a paper that states the category itself, or "term": the claim's own
   * condition, found in MeSH by its name and read as this category by the pipeline's
   * term check. That reading is a model's, so its score is shown with it.
   */
  kind: "trial" | "paper" | "term";
  identifier: string;
  score?: number | null;
}

/** How a category that rests on the reading of the claim's own condition says so. */
export function termSourceSentence(score: number | null | undefined): string {
  return score == null
    ? "the claim's own condition, read as this category"
    : `the claim's own condition, read as this category with a score of ${score.toFixed(2)}`;
}

export interface ClinicalCategory {
  identifier: string;
  sources: CategorySource[];
}

interface Filed {
  slug: string;
  clinical_categories?: ClinicalCategory[] | null;
}

export interface Tree {
  nodes: Map<string, MeshNode>;
  /** Each descriptor's directly narrower descriptors. */
  narrower: Map<string, string[]>;
  /** The claims at or below each descriptor, each once. */
  claims: Map<string, Set<string>>;
}

const byLabel = (nodes: Map<string, MeshNode>) => (a: string, b: string) =>
  (nodes.get(a)?.label ?? a).localeCompare(nodes.get(b)?.label ?? b);

/** A descriptor with every descriptor broader than it, at any distance. */
export function atOrAbove(
  identifier: string, nodes: Map<string, MeshNode>, edge?: (parent: string, child: string) => void,
): Set<string> {
  const found = new Set([identifier]);
  const waiting: [string, string][] = (nodes.get(identifier)?.tree_numbers ?? []).map(n => [identifier, n]);
  const seen = new Set<string>();
  while (waiting.length) {
    const [child, number] = waiting.pop()!;
    if (seen.has(number)) continue;
    seen.add(number);
    for (const parent of nodes.get(child)?.broader ?? []) {
      for (const prefix of nodes.get(parent)?.tree_numbers ?? []) {
        if (!number.startsWith(prefix + ".")) continue;
        found.add(parent);
        edge?.(parent, child);
        waiting.push([parent, prefix]);
      }
    }
  }
  return found;
}

/** The tree the export carries, with the claims at or below each descriptor. */
export function buildTree(clinical: Clinical | null | undefined, claims: Filed[]): Tree {
  const nodes = new Map((clinical?.nodes ?? []).map((node) => [node.identifier, node]));
  const narrower = new Map<string, string[]>();
  function keepEdge(parent: string, child: string) {
    const children = narrower.get(parent) ?? [];
    if (!children.includes(child)) children.push(child);
    narrower.set(parent, children);
  }
  const filed = new Map<string, Set<string>>();
  for (const claim of claims) {
    for (const category of claim.clinical_categories ?? []) {
      for (const identifier of atOrAbove(category.identifier, nodes, keepEdge)) {
        if (!nodes.has(identifier)) continue;
        if (!filed.has(identifier)) filed.set(identifier, new Set());
        filed.get(identifier)!.add(claim.slug);
      }
    }
  }
  for (const list of narrower.values()) list.sort(byLabel(nodes));
  return { nodes, narrower, claims: filed };
}

/** How many published claims are at or below the descriptor. */
export const claimCount = (tree: Tree, identifier: string): number =>
  tree.claims.get(identifier)?.size ?? 0;

/** The descriptors at the top of a tree with a claim at or below them, by name. */
export function topCategories(tree: Tree): MeshNode[] {
  return [...tree.nodes.values()]
    .filter((node) => node.broader.length === 0 && claimCount(tree, node.identifier) > 0)
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** Every descriptor with a claim at or below it: each has a page. */
export function listedCategories(tree: Tree): MeshNode[] {
  return [...tree.nodes.values()]
    .filter((node) => claimCount(tree, node.identifier) > 0)
    .sort((a, b) => a.identifier.localeCompare(b.identifier));
}

/** The descriptors directly narrower that have a claim at or below them, by name. */
export function narrowerWithClaims(tree: Tree, identifier: string): MeshNode[] {
  return (tree.narrower.get(identifier) ?? [])
    .filter((narrower) => claimCount(tree, narrower) > 0)
    .map((narrower) => tree.nodes.get(narrower)!);
}

export const categoryPath = (identifier: string): string => `/clinical/${identifier}`;

/** "MeSH 2026", or each year when the records were read from more than one. */
export function meshEdition(years: string[]): string {
  if (years.length === 0) return "MeSH";
  if (years.length === 1) return `MeSH ${years[0]}`;
  return `MeSH ${years.slice(0, -1).join(", ")} and ${years[years.length - 1]}`;
}

/** What is wrong with the export's clinical data, each as a sentence. Empty when sound. */
export function clinicalProblems(clinical: Clinical | null | undefined, claims: Filed[]): string[] {
  const used = new Set(
    claims.flatMap((claim) => (claim.clinical_categories ?? []).map((one) => one.identifier)),
  );
  if (used.size === 0) return [];
  const problems: string[] = [];
  if (!clinical || clinical.mesh_years.length === 0) {
    problems.push("it carries clinical categories and no MeSH year");
  }
  const held = new Set((clinical?.nodes ?? []).map((node) => node.identifier));
  const unplaced = [...used].filter((identifier) => !held.has(identifier)).sort();
  if (unplaced.length > 0) {
    problems.push(`it places no node in the tree for: ${unplaced.join(", ")}`);
  }
  return problems;
}
