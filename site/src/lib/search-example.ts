// The example words the lookup box offers, worked out once for a build: by the rule in
// `searchExample`, over the claims in the order the site prefers its examples.
import { data } from "./export";
import { exampleClaims } from "./extension-page";
import { searchExample } from "./search-order";

export const SEARCH_EXAMPLE = searchExample(exampleClaims(data.claims));
