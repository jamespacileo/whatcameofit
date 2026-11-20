// The explore page in the reader's browser (src/lib/explore.ts writes its file). A reader picks
// nodes from any tree by name; the page lists the pairs that match.
//
// Picks combine as faceted search does on Amazon and in trial registries' advanced search: a
// node includes everything beneath it, several picks in one tree match any of them, and picks
// in different trees must all match. A node's count is what picking it would add to the other
// trees' picks, so a count never promises pairs the page would not then show.
// Every value from the file is set as text, never as markup.
import type { ExploreIndex, ExploreNode, ExplorePair, ExploreTree, TreeKey } from "../lib/explore.ts";

type Picks = Map<TreeKey, Set<string>>;

const root = document.querySelector<HTMLElement>("[data-explore]");
if (root) start(root);

function el<K extends keyof HTMLElementTagNameMap>(tag: K, props: Record<string, string> = {}, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(props)) node.setAttribute(name, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

async function start(root: HTMLElement) {
  const status = root.querySelector<HTMLElement>("[data-explore-status]")!;
  let index: ExploreIndex;
  try {
    const response = await fetch(root.dataset.explore!);
    if (!response.ok) throw new Error(String(response.status));
    index = await response.json();
  } catch {
    status.textContent = "The list could not be loaded. Try again later.";
    return;
  }
  const trees = new Map(index.trees.map((tree) => [tree.key, tree]));
  const picks: Picks = new Map();
  const params = new URLSearchParams(location.search);
  for (const tree of index.trees) {
    const known = new Set(tree.nodes.map((node) => node.id));
    const chosen = params.getAll(tree.key).filter((id) => known.has(id));
    if (chosen.length) picks.set(tree.key, new Set(chosen));
  }

  const matches = (pair: ExplorePair, except?: TreeKey) =>
    [...picks].every(([key, ids]) => key === except || (pair.at[key] ?? []).some((id) => ids.has(id)));

  const chips = root.querySelector<HTMLElement>("[data-explore-chips]")!;
  const facets = root.querySelector<HTMLElement>("[data-explore-facets]")!;
  const results = root.querySelector<HTMLElement>("[data-explore-results]")!;
  const search = root.querySelector<HTMLInputElement>("[data-explore-search]")!;
  const suggestions = root.querySelector<HTMLElement>("[data-explore-suggestions]")!;

  const toggle = (key: TreeKey, id: string) => {
    const ids = picks.get(key) ?? new Set<string>();
    if (ids.has(id)) ids.delete(id);
    else ids.add(id);
    if (ids.size) picks.set(key, ids);
    else picks.delete(key);
    const next = new URLSearchParams();
    for (const [tree, chosen] of picks) for (const one of [...chosen].sort()) next.append(tree, one);
    const query = next.toString();
    history.replaceState(null, "", query ? `?${query}` : location.pathname);
    render();
  };

  // One path from the top for a node, for a suggestion's second line.
  const pathOf = (tree: ExploreTree, node: ExploreNode): string => {
    const byId = new Map(tree.nodes.map((one) => [one.id, one]));
    const steps = [node.label];
    let at = node;
    const seen = new Set([node.id]);
    while (at.parents.length && !seen.has(at.parents[0])) {
      const up = byId.get(at.parents[0]);
      if (!up) break;
      seen.add(up.id);
      steps.unshift(up.label);
      at = up;
    }
    return `${tree.label} › ${steps.join(" › ")}`;
  };

  function renderChips() {
    chips.replaceChildren();
    for (const [key, ids] of picks) {
      const tree = trees.get(key)!;
      for (const id of ids) {
        const node = tree.nodes.find((one) => one.id === id)!;
        const chip = el("button", { type: "button", class: "explore-chip", "data-pick": `${key}:${id}`, "aria-label": `Remove ${node.label}` }, `${node.label} ×`);
        chip.addEventListener("click", () => toggle(key, id));
        chips.append(chip);
      }
    }
    if (picks.size) {
      const clear = el("button", { type: "button", class: "explore-clear" }, "Clear all");
      clear.addEventListener("click", () => {
        picks.clear();
        history.replaceState(null, "", location.pathname);
        render();
      });
      chips.append(clear);
    }
  }

  function renderFacets() {
    facets.replaceChildren();
    for (const tree of index.trees) {
      if (!tree.nodes.length) continue;
      const base = index.pairs.filter((pair) => matches(pair, tree.key));
      const count = new Map<string, number>();
      for (const pair of base) for (const id of pair.at[tree.key] ?? []) count.set(id, (count.get(id) ?? 0) + 1);
      const children = new Map<string, ExploreNode[]>();
      for (const node of tree.nodes) for (const parent of node.parents) children.set(parent, [...(children.get(parent) ?? []), node]);
      const chosen = picks.get(tree.key) ?? new Set<string>();
      const list = (nodes: ExploreNode[], trail: Set<string>): HTMLUListElement => {
        const ul = el("ul");
        for (const node of nodes) {
          const li = el("li");
          const id = `pick-${tree.key}-${node.id}-${trail.size}`;
          const box = el("input", { type: "checkbox", id, "data-node": node.id });
          box.checked = chosen.has(node.id);
          box.addEventListener("change", () => toggle(tree.key, node.id));
          const label = el("label", { for: id }, node.label);
          label.append(" ", el("span", { class: "count" }, String(count.get(node.id) ?? 0)));
          li.append(box, label);
          const below = (children.get(node.id) ?? []).filter((child) => !trail.has(child.id));
          if (below.length) {
            const more = el("details");
            if ([...chosen].some((one) => below.some((child) => child.id === one))) more.open = true;
            more.append(el("summary", {}, `Narrower (${below.length})`), list(below, new Set([...trail, node.id])));
            li.append(more);
          }
          ul.append(li);
        }
        return ul;
      };
      const section = el("section", { class: "explore-tree", "data-tree": tree.key, "aria-labelledby": `tree-${tree.key}` });
      section.append(
        el("h3", { id: `tree-${tree.key}` }, `${tree.label}`),
        el("p", { class: "note" }, tree.side === "condition" ? "Conditions" : "Treatments"),
        list(tree.nodes.filter((node) => node.parents.length === 0), new Set()),
      );
      facets.append(section);
    }
  }

  function renderResults() {
    const shown = index.pairs.filter((pair) => matches(pair));
    status.textContent =
      shown.length === 1 ? "1 treatment and condition matches." : `${shown.length} treatments and conditions match.`;
    results.replaceChildren();
    if (!shown.length) return;
    const table = el("table", { class: "pair-table", "data-pair-table": "" });
    const head = el("tr");
    for (const title of ["Treatment and condition", "Where it stands", "Trials"]) head.append(el("th", { scope: "col" }, title));
    table.append(el("thead"), el("tbody"));
    table.tHead!.append(head);
    for (const pair of shown) {
      const row = el("tr", { "data-pair": pair.address });
      const name = el("th", { scope: "row" });
      name.append(el("a", { href: `/${pair.address}` }, `${pair.treatment} for ${pair.condition.toLowerCase()}`));
      row.append(name, el("td", { "data-status": pair.statusCode }, pair.status), el("td", {}, String(pair.trials)));
      table.tBodies[0].append(row);
    }
    results.append(table);
  }

  search.addEventListener("input", () => {
    const words = search.value.trim().toLowerCase();
    suggestions.replaceChildren();
    if (words.length < 2) return;
    const found: [ExploreTree, ExploreNode][] = [];
    for (const tree of index.trees) for (const node of tree.nodes) if (node.label.toLowerCase().includes(words)) found.push([tree, node]);
    for (const [tree, node] of found.slice(0, 12)) {
      const option = el("button", { type: "button", class: "explore-suggestion", "data-pick": `${tree.key}:${node.id}` });
      option.append(el("span", { class: "suggestion-name" }, node.label), el("span", { class: "suggestion-path" }, pathOf(tree, node)));
      option.addEventListener("click", () => {
        if (!picks.get(tree.key)?.has(node.id)) toggle(tree.key, node.id);
        search.value = "";
        suggestions.replaceChildren();
      });
      suggestions.append(option);
    }
    if (!found.length) suggestions.append(el("p", { class: "note" }, "Nothing in any tree has that name."));
  });

  function render() {
    renderChips();
    renderFacets();
    renderResults();
  }
  render();
}
