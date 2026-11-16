#!/bin/sh
# Tests for scripts/daily-run.sh. No database, no network, no real pipeline: the script
# is copied into a made-up checkout and `uv` is a stand-in that writes down what it was
# asked to run and answers with fixed figures.
#
#   sh scripts/tests/daily-run.test.sh
set -u

here=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
failures=0

fail() {
  echo "FAIL: $1"
  failures=$((failures + 1))
}

# A fresh made-up checkout and home for each case.
fresh() {
  rm -rf "$tmp/case"
  root="$tmp/case/checkout"
  home="$tmp/case/home"
  state="$home/Library/Application Support/thenwhat/daily-run"
  calls="$tmp/case/calls"
  month=$(date '+%Y-%m')
  mkdir -p "$root/scripts" "$root/pipeline" "$root/data/link-files/hackernews" "$home" "$tmp/case/bin"
  cp "$here/daily-run.sh" "$here/com.thenwhat.daily-run.plist" "$root/scripts/"
  : >"$root/scripts/fetch_link_files.py"
  : >"$root/data/link-files/hackernews/$month.parquet"
  : >"$calls"
  printf 'LLM_MONTHLY_BUDGET_USD=30\nDAILY_RUN_REFRESH_LIMIT=2\n' >"$root/.env"
  cat >"$tmp/case/bin/uv" <<'EOF'
#!/bin/sh
echo "$*" >>"$CALLS"
case "$*" in
  *"daily_run_figures.py spend") echo "${FAKE_SPEND:-4.2500 0.5000}" ;;
  *"daily_run_figures.py counts") echo "700 4 12" ;;
  *"daily_run_figures.py published") printf 'claim-a\nclaim-b\nclaim-c\n' ;;
  *"thenwhat db-check") [ "${FAKE_DB:-up}" = up ] ;;
  *"load-links"*) echo "Read 900 posts from file: 31 new link leads, 2 more shares, 867 already stored." ;;
  *"link_read"*) echo "link_read: 40 done, 0 found nothing, 1 failed; 300 still due." ;;
  *"thenwhat fetch claim-b") exit 1 ;;
  *"thenwhat fetch"*) echo "Recorded 2 new events for a claim; 0 await review." ;;
esac
EOF
  chmod +x "$tmp/case/bin/uv"
}

job() {
  HOME="$home" CALLS="$calls" PATH="$tmp/case/bin:$PATH" sh "$root/scripts/daily-run.sh" "$@"
}

# What the job must never start, in any case.
never() {
  if grep -E 'audit clear|thenwhat (archive|unarchive|export)|publish-data|git ' "$1" >/dev/null; then
    fail "$2: a forbidden command appears"
  fi
}

steps_called() { sed -n 's/.* thenwhat //p' "$calls" | awk '{ print ($1 == "backfill" ? $2 " " $3 : $1) }' | uniq | tr '\n' ',' ; }

# 1. A dry run prints the steps in order, starts nothing and writes nothing.
fresh
out=$(job --dry-run) || fail "dry run: exit $?"
[ -s "$calls" ] && fail "dry run: something was started"
[ -e "$home/Library" ] && fail "dry run: a file was written"
echo "$out" >"$tmp/case/dry"
grep '^+' "$tmp/case/dry" >"$tmp/case/dry.cmds"
never "$tmp/case/dry.cmds" "dry run"
order=$(sed -n 's/^# start //p' "$tmp/case/dry" | tr '\n' ',')
[ "$order" = "database,fetch-links,load-links,screen,score,read,prepare,refresh,measure," ] ||
  fail "dry run: steps out of order: $order"

# 2. A run starts every step in order, checks the spend before each one that spends,
#    writes the summary and lets the lock go.
fresh
job || true
never "$calls" "run"
want="db-check,load-links hackernews,run link_screen,run link_triage,run link_read,prepare,fetch,measure,"
[ "$(steps_called)" = "$want" ] || fail "run: steps were $(steps_called)"
[ "$(grep -c 'daily_run_figures.py spend' "$calls")" -ge 4 ] || fail "run: fewer than four spend checks"
[ -e "$state/lock" ] && fail "run: the lock was left"
summary="$state/latest.md"
grep -q '31 new link leads' "$summary" || fail "run: the summary lacks what was loaded"
grep -q 'link_read: 40 done' "$summary" || fail "run: the summary lacks what was read"
grep -q 'Awaiting audit: 12 before, 12 after' "$summary" || fail "run: the summary lacks the audit count"
grep -q 'This month: .4.2500 of the .30 ceiling' "$summary" || fail "run: the summary lacks the spend"
grep -q '2 of 3 published claims: 2 new events, 1 claims failed' "$summary" || fail "run: the summary lacks the refresh"
[ "$(cat "$state/refresh-offset")" = 2 ] || fail "run: the next refresh would not start at the third claim"

# 3. At the ceiling nothing that spends starts; what spends nothing still runs.
fresh
(export FAKE_SPEND="29.2000 1.0000" && job) || fail "ceiling: exit $? for a stop that was meant"
[ "$(steps_called)" = "db-check,load-links hackernews,run link_screen,measure," ] ||
  fail "ceiling: steps were $(steps_called)"
grep -q '^Stopped: before score' "$state/latest.md" || fail "ceiling: the summary does not say why"

# 4. The link files' drive is not mounted: nothing starts, and the summary says so.
fresh
rm -rf "$root/data/link-files"
job || fail "no drive: exit $? for a stop that was meant"
[ -s "$calls" ] && fail "no drive: something was started"
grep -q 'drive is not mounted' "$state/latest.md" || fail "no drive: the summary does not say so"

# 5. A second run does not start while the first holds the lock.
fresh
mkdir -p "$state/lock"
echo $$ >"$state/lock/pid"
job || fail "lock: exit $?"
[ -s "$calls" ] && fail "lock: a second run started"
[ -d "$state/lock" ] || fail "lock: the first run's lock was taken away"

# 6. An unquoted JSON value in the settings file: nothing starts, and the run fails.
fresh
printf 'SOURCE_ALLOWANCES={"reader": {"requests": 10}}\nLLM_MONTHLY_BUDGET_USD=30\n' >"$root/.env"
job && fail "json: exit 0"
[ -s "$calls" ] && fail "json: something was started"
grep -q 'SOURCE_ALLOWANCES' "$state/latest.md" || fail "json: the summary does not name the setting"
grep -q 'requests' "$state/latest.md" && fail "json: the summary shows the setting's value"

# 7. Paused: nothing starts.
fresh
job pause >/dev/null
job || fail "paused: exit $?"
[ -s "$calls" ] && fail "paused: something was started"

# 8. The database is down: nothing after the check starts.
fresh
(export FAKE_DB=down && job) && fail "database: exit 0"
[ "$(steps_called)" = "db-check," ] || fail "database: steps were $(steps_called)"

# 9. The property list is filled in from the checkout's own paths.
fresh
job plist >"$tmp/case/plist"
grep -q "<string>$root/scripts/daily-run.sh</string>" "$tmp/case/plist" || fail "plist: the script's path"
grep -q '@[A-Z_]*@' "$tmp/case/plist" && fail "plist: a blank was left"
if command -v plutil >/dev/null 2>&1; then
  plutil -lint "$tmp/case/plist" >/dev/null || fail "plist: not a property list"
fi

if [ "$failures" -gt 0 ]; then
  echo "$failures failed"
  exit 1
fi
echo "daily-run: all passed"
