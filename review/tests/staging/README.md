# What staging is published with, recorded for the tests

`gone.json`, `kept-claims.json`, `held-redirects.json` and `lookup/2.json` are written by the
site's own `site/scripts/redirects.mjs`, from the site's test bundle and its frozen kept claims.
`lookup/2.json` holds only what that script adds (kept claims and their article keys): the pair
part comes from an Astro build, which these tests do not read. To write them again, from the
repository root:

```sh
D=$(mktemp -d) && mkdir -p $D/lookup && echo '{}' > $D/lookup/2.json
(cd site && PAIRS_BUNDLE=tests/bundle DIST_DIR=$D KEPT_CLAIMS_DIR=tests/kept-claims node scripts/redirects.mjs)
cp $D/gone.json $D/kept-claims.json $D/held-redirects.json review/tests/staging/ && cp $D/lookup/2.json review/tests/staging/lookup/
```

`claim-scope.json` is the lab's claim scope (thenwhat-lab #174, main c589539) as its replay of
109 claims gave it: the 40 verified redirects and 63 held claims listed in
`/mnt/project-files/release-holds/claim-scope-lists-c589539.md`, in the shape of
`PairClaimScopePage.schema.json` (the lab's schema, verbatim). Held claims the lab listed as
having no pair at all carry `pair: null` and `no_pair_for_the_indication`.
