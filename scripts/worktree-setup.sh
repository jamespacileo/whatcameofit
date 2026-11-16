#!/bin/sh
# Give a checkout its node_modules without a full install. A new git worktree starts with
# none; the main checkout usually has them. Where the lockfile is the same, they are
# cloned from there copy-on-write (APFS on macOS, reflink on Linux): seconds, and no extra
# disk until a file changes. Otherwise this falls back to `npm ci`.
#
#   sh scripts/worktree-setup.sh            # site and video
#   sh scripts/worktree-setup.sh site       # one of them
set -eu

root=$(git rev-parse --show-toplevel)
main=$(git worktree list --porcelain | sed -n '1s/^worktree //p')

clone() {
  # macOS clones with -c; GNU cp with --reflink. Either fails cleanly where unsupported.
  cp -c -R "$1" "$2" 2>/dev/null || cp -R --reflink=always "$1" "$2" 2>/dev/null
}

setup() {
  dir=$1
  lock="$root/$dir/package-lock.json"
  target="$root/$dir/node_modules"
  [ -f "$lock" ] || return 0

  # Already installed from this lockfile: npm writes its own copy of it inside.
  if [ -f "$target/.package-lock.json" ] && [ ! "$lock" -nt "$target/.package-lock.json" ]; then
    echo "$dir: node_modules is up to date"
    return 0
  fi

  rm -rf "$target"
  source="$main/$dir/node_modules"
  if [ "$main" != "$root" ] && [ -f "$source/.package-lock.json" ] &&
    cmp -s "$main/$dir/package-lock.json" "$lock" && clone "$source" "$target"; then
    touch "$target/.package-lock.json" "$target"
    echo "$dir: node_modules cloned from $main"
    return 0
  fi

  rm -rf "$target"
  echo "$dir: installing with npm ci"
  npm --prefix "$root/$dir" ci
  touch "$target"
}

if [ $# -gt 0 ]; then
  for dir in "$@"; do setup "$dir"; done
else
  setup site
  setup video
fi
