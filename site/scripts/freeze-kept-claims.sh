#!/bin/sh
# Freeze the kept claims' files once (site/scripts/kept-claims.mjs): build production's last
# claims build, commit KEPT_CLAIMS_COMMIT, in a worktree of its own as its CI built it, and copy
# out every claim's eight files and the styles, scripts and fonts they load.
#
#   sh site/scripts/freeze-kept-claims.sh <folder>
#
# Does nothing when the folder already holds a manifest. Takes about four minutes the first
# time (most of it drawing the claims' cards). Production's build read the repository variables
# SUGGEST_URL, CORRECTIONS_URL, CHROME_STORE_URL, SAFARI_STORE_URL, LLM_MODEL, CONTACT_EMAIL and
# DECISION_BACKEND; set them as its CI did for the same bytes. Deploys and publishes nothing.
set -eu

out=${1:?the folder to freeze into}
if [ -f "$out/manifest.json" ]; then
  echo "Kept claims already frozen at $out."
  exit 0
fi

root=$(git rev-parse --show-toplevel)
commit=$(cd "$root/site" && node --input-type=module -e 'import { KEPT_CLAIMS_COMMIT } from "./scripts/kept-claims.mjs"; console.log(KEPT_CLAIMS_COMMIT)')
git -C "$root" cat-file -e "$commit^{commit}" 2>/dev/null || git -C "$root" fetch --no-tags --depth=1 origin "$commit"

work=$(mktemp -d)
cleanup() {
  git -C "$root" worktree remove --force "$work/build" 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT
git -C "$root" worktree add --detach "$work/build" "$commit"

cd "$work/build"
# Nothing of the calling build reaches the old one: not a make's variables, not a bundle.
unset MAKEFLAGS MFLAGS MAKELEVEL PAIRS_BUNDLE PAIRS_DATABASE PAIRS_VERSION KEPT_CLAIMS_DIR STYLEGUIDE DIST_DIR
sh scripts/worktree-setup.sh site
# As production's CI ran it (make deploy-ci-check): its own export, its own address, a dry run.
SITE_URL=https://whatcameofit.com BUILD_REVISION="$commit" ASTRO_TELEMETRY_DISABLED=1 make deploy-ci-check

cd "$root/site"
rm -rf "$out.partial"
node scripts/kept-claims.mjs freeze "$work/build/site/dist" "$out.partial"
mv "$out.partial" "$out"
