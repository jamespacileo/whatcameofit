// The clinical tree worked out from the export: pure, no build.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  atOrAbove,
  buildTree,
  claimCount,
  clinicalProblems,
  meshEdition,
  narrowerWithClaims,
  topCategories,
} from "../src/lib/clinical.ts";

const node = (identifier, label, tree_numbers, broader = []) => ({ identifier, label, tree_numbers, broader });
const clinical = {
  mesh_years: ["2026"],
  nodes: [
    node("A", "Top one", ["C01"]),
    node("B", "Top two", ["C02"]),
    node("C", "Under both", ["C01.1", "C02.1"], ["A", "B"]),
    node("D", "Under one", ["C01.2"], ["A"]),
    node("E", "Empty top", ["C03"]),
  ],
};
const claims = [
  { slug: "one", clinical_categories: [{ identifier: "C", sources: [] }, { identifier: "D", sources: [] }] },
  { slug: "two", clinical_categories: [{ identifier: "D", sources: [] }] },
  { slug: "three", clinical_categories: null },
  { slug: "four" },
];

test("a category in two places is below both, and a claim is counted once per category", () => {
  const tree = buildTree(clinical, claims);
  assert.deepEqual([...atOrAbove("C", tree.nodes)].sort(), ["A", "B", "C"]);
  // "one" reaches A through both C and D and is counted once.
  assert.equal(claimCount(tree, "A"), 2);
  assert.equal(claimCount(tree, "B"), 1);
  assert.equal(claimCount(tree, "E"), 0);
});

test("only categories with a claim are listed, by name", () => {
  const tree = buildTree(clinical, claims);
  assert.deepEqual(topCategories(tree).map((one) => one.identifier), ["A", "B"]);
  assert.deepEqual(narrowerWithClaims(tree, "A").map((one) => one.identifier), ["C", "D"]);
  assert.deepEqual(narrowerWithClaims(tree, "E"), []);
});

test("the MeSH edition names every year the records were read from", () => {
  assert.equal(meshEdition(["2026"]), "MeSH 2026");
  assert.equal(meshEdition(["2026", "2027"]), "MeSH 2026 and 2027");
});

test("an export is refused with categories and no year, or a category it places nowhere", () => {
  assert.deepEqual(clinicalProblems(clinical, claims), []);
  assert.deepEqual(clinicalProblems(null, [{ slug: "x", clinical_categories: [] }]), []);
  assert.deepEqual(clinicalProblems({ mesh_years: [], nodes: clinical.nodes }, claims), [
    "it carries clinical categories and no MeSH year",
  ]);
  assert.deepEqual(
    clinicalProblems(clinical, [{ slug: "x", clinical_categories: [{ identifier: "Z", sources: [] }] }]),
    ["it places no node in the tree for: Z"],
  );
});

test("Wolfram syndrome reaches diabetes only on its metabolic placement", () => {
  const nodes = [node("M", "Metabolic diseases", ["C18"]), node("I", "Immune diseases", ["C20"]),
    node("T", "Type 1 diabetes", ["C18.452.394.750.124", "C20.111.327"], ["M", "I"]),
    node("W", "Wolfram syndrome", ["C18.452.394.750.124.960"], ["T"])];
  const filed = (slug, identifier) => ({slug, clinical_categories: [{identifier}]});
  const tree = buildTree({mesh_years:["2026"], nodes}, [filed("wolfram", "W"), filed("diabetes", "T")]);
  assert.deepEqual([...tree.claims.get("I")], ["diabetes"]);
  assert.deepEqual([...tree.claims.get("M")].sort(), ["diabetes", "wolfram"]);
});
