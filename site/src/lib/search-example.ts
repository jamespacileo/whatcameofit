// The example words the lookup box offers, worked out once for a build: by the rule in
// `searchExample`, over the pairs in the order the site prefers its examples.
import { examplePairs } from "./extension-page";
import { pairPages, pairView } from "./pairs";
import { searchExample } from "./search-order";

export const SEARCH_EXAMPLE = searchExample(
  examplePairs(Object.values(pairPages()))
    .map(pairView)
    .map((pair) => ({
      slug: pair.address,
      headline: pair.title,
      intervention: { name: pair.intervention, synonyms: pair.otherNames },
      indication: pair.condition,
      articles: [],
    })),
);
