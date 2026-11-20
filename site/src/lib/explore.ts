// The explore page's file (openspec pairs-site, task 6.2; design "Browsing by hierarchy, picking
// several, and knowledge cards", https://claude.ai/artifact/7Ge7Qvqct18XkwheBMKWTN): every
// published pair with the nodes it sits at or beneath in each tree, and each tree's nodes by
// name. The reader's browser filters it (src/scripts/explore.ts), so a pick costs no database
// read and a crawler that follows query strings finds no new page to render.
//
// Each pair keeps its most specific condition and treatment, and the trees roll it up, as OMOP
// does through `concept_ancestor` and ClinicalTrials.gov through a record's MeSH ancestors; the
// lab made the same choice for conditions on 2026-11-20 (a trial supports a pair at its most
// specific condition). Until the lab's tree files land (task 6.3) the roll-up is worked out here
// from the descriptors the bundle names, so a MeSH step with no name in the bundle is skipped
// rather than shown as its code.
import { shownName } from "./pair-view.ts";
import { PAIR_APPROACH_LABELS, TREE_LABELS } from "./pair-wording.ts";
import { STATUS_LABELS } from "./status.ts";

/** A tree's key is also its query parameter, so a pick's address reads as words. */
export type TreeKey = "body-system" | "topic" | "kind";

export interface ExploreNode {
  /** The node's slug, unique within its tree. */
  id: string;
  label: string;
  /** The nodes directly above it in its tree; several where the tree is a polyhierarchy. */
  parents: string[];
}

export interface ExploreTree {
  key: TreeKey;
  side: "condition" | "treatment";
  label: string;
  nodes: ExploreNode[];
}

export interface ExplorePair {
  address: string;
  treatment: string;
  condition: string;
  status: string;
  statusCode: string;
  trials: number;
  /** For each tree, every node the pair sits at or beneath. */
  at: Partial<Record<TreeKey, string[]>>;
}

export interface ExploreIndex {
  trees: ExploreTree[];
  pairs: ExplorePair[];
}

interface Descriptor {
  descriptor_id: string;
  label: string;
  tree_numbers: string[];
}

export const slugOf = (label: string): string =>
  label
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

/** The MeSH tree as far as the bundle names it: a node per descriptor, its parents the nearest
 * named descriptor above each of its tree numbers. */
function meshTree(descriptors: Descriptor[]): { tree: ExploreTree; above: (descriptor: Descriptor) => string[] } {
  const byId = new Map<string, Descriptor>();
  for (const one of descriptors) byId.set(one.descriptor_id, one);
  const byNumber = new Map<string, Descriptor>();
  for (const one of byId.values()) for (const number of one.tree_numbers) byNumber.set(number, one);
  // Two descriptors can share a label only in different branches' wording; the id keeps them apart.
  const ids = new Map<string, string>();
  const taken = new Set<string>();
  for (const one of [...byId.values()].sort((a, b) => a.descriptor_id.localeCompare(b.descriptor_id))) {
    let id = slugOf(one.label);
    if (taken.has(id)) id = `${id}-${one.descriptor_id.toLowerCase()}`;
    taken.add(id);
    ids.set(one.descriptor_id, id);
  }
  const parentsOf = (one: Descriptor): string[] => {
    const parents = new Set<string>();
    for (const number of one.tree_numbers) {
      const parts = number.split(".");
      for (let depth = parts.length - 1; depth >= 1; depth--) {
        const step = byNumber.get(parts.slice(0, depth).join("."));
        if (step && step.descriptor_id !== one.descriptor_id) {
          parents.add(ids.get(step.descriptor_id)!);
          break;
        }
      }
    }
    return [...parents].sort();
  };
  const nodes = [...byId.values()]
    .map((one) => ({ id: ids.get(one.descriptor_id)!, label: one.label, parents: parentsOf(one) }))
    .sort((a, b) => a.label.localeCompare(b.label));
  const parentMap = new Map(nodes.map((node) => [node.id, node.parents]));
  const above = (one: Descriptor): string[] => {
    const found = new Set<string>();
    const walk = (id: string) => {
      if (found.has(id)) return;
      found.add(id);
      for (const parent of parentMap.get(id) ?? []) walk(parent);
    };
    walk(ids.get(one.descriptor_id)!);
    return [...found].sort();
  };
  return { tree: { key: "body-system", side: "condition", label: TREE_LABELS.mesh, nodes }, above };
}

/** The explore file from the bundle's page files, for the pairs this build publishes. */
export function exploreIndex(pages: Record<string, any>, categoryFiles: any[], topicsPage: any | undefined): ExploreIndex {
  const descriptors: Descriptor[] = [
    ...Object.values(pages).map((page: any) => page.row.descriptor),
    ...categoryFiles.flatMap((file: any) => [file.descriptor, ...file.broader, ...file.narrower]),
  ];
  const mesh = meshTree(descriptors);

  // Health topic: the lab's groups over its verticals. A pair no topic files sits in no node
  // of this tree (every cleared pair has a page, filed or not; lab decision of 2026-11-20).
  const groups = new Map<string, any>((topicsPage?.groups ?? []).map((group: any) => [group.slug, group]));
  const verticals = new Map<string, any>((topicsPage?.verticals ?? []).map((vertical: any) => [vertical.slug, vertical]));
  const groupId = (slug: string) => `area-${slug}`;
  const topicNodes: ExploreNode[] = [
    ...[...groups.values()].map((group: any) => ({ id: groupId(group.slug), label: group.title, parents: [] })),
    ...[...verticals.values()]
      // A vertical named the same as its own group is that group's single topic: one node, not two.
      .filter((vertical: any) => !(vertical.group && groups.get(vertical.group)?.title === vertical.title))
      .map((vertical: any) => ({ id: vertical.slug, label: vertical.title, parents: vertical.group && groups.has(vertical.group) ? [groupId(vertical.group)] : [] })),
  ];
  const topicIds = new Set(topicNodes.map((node) => node.id));
  const topicAt = (slug: string | undefined): string[] => {
    const vertical = slug ? verticals.get(slug) : undefined;
    if (!vertical) return [];
    const group = vertical.group && groups.has(vertical.group) ? groupId(vertical.group) : null;
    return [...(topicIds.has(vertical.slug) ? [vertical.slug] : []), ...(group ? [group] : [])];
  };

  // Kind of treatment: the registry's intervention type, read by rule. One level for now.
  const kindNodes = Object.entries(PAIR_APPROACH_LABELS).map(([code, label]) => ({ id: slugOf(code), label, parents: [] }));
  const kindAt = (code: string | null | undefined) => (code && Object.hasOwn(PAIR_APPROACH_LABELS, code) ? [slugOf(code)] : []);

  const pairs: ExplorePair[] = Object.values(pages)
    .map((page: any) => ({
      address: page.row.pair.address,
      treatment: shownName(page.row.intervention.preferred_name),
      condition: page.row.descriptor.label,
      status: STATUS_LABELS[page.row.status.code as keyof typeof STATUS_LABELS],
      statusCode: page.row.status.code,
      trials: page.trials.length,
      at: {
        "body-system": mesh.above(page.row.descriptor),
        topic: topicAt(page.row.filing?.vertical),
        kind: kindAt(page.approach?.approach),
      },
    }))
    .sort((a, b) => a.treatment.localeCompare(b.treatment) || a.condition.localeCompare(b.condition));

  // A node with no pair at or beneath it is left out: it would be a choice that finds nothing.
  const used = (key: TreeKey) => new Set(pairs.flatMap((pair) => pair.at[key] ?? []));
  const keep = (tree: ExploreTree): ExploreTree => {
    const ids = used(tree.key);
    return { ...tree, nodes: tree.nodes.filter((node) => ids.has(node.id)).map((node) => ({ ...node, parents: node.parents.filter((parent) => ids.has(parent)) })) };
  };
  return {
    trees: [
      keep(mesh.tree),
      keep({ key: "topic", side: "condition", label: TREE_LABELS.topic, nodes: topicNodes }),
      keep({ key: "kind", side: "treatment", label: TREE_LABELS.approach, nodes: kindNodes }),
    ],
    pairs,
  };
}
