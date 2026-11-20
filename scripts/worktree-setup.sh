#!/bin/sh
# Give a checkout its node_modules. A new git worktree starts with none. pnpm keeps one
# copy of every package in a store shared by all checkouts on this machine and links it
# in, so this takes seconds and downloads nothing the store already holds.
#
#   sh scripts/worktree-setup.sh            # the site
#   sh scripts/worktree-setup.sh site       # one of them
set -eu

root=$(git rev-parse --show-toplevel)

if ! command -v pnpm >/dev/null; then
  echo "pnpm is not installed. Install it with: npm install -g pnpm" >&2
  exit 1
fi

wanted=$(cat "$root/.node-version")
have=$(node -p 'process.versions.node.split(".")[0]')
if [ "$have" != "$wanted" ]; then
  echo "Node $wanted is needed (.node-version); this shell runs Node $have." >&2
  exit 1
fi

setup() {
  dir=$1
  [ -f "$root/$dir/pnpm-lock.yaml" ] || return 0
  pnpm --dir "$root/$dir" install --frozen-lockfile --prefer-offline
  touch "$root/$dir/node_modules"
}

if [ $# -gt 0 ]; then
  for dir in "$@"; do setup "$dir"; done
else
  setup site
fi
