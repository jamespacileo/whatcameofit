#!/bin/sh
# The daily run: brings in the newest shared links, screens, scores and reads a capped
# number of them, prepares the claims they draft, loads the trials the registry changed
# since the last load, and reads the registries again for published claims. One run, in
# order, under a lock, each step logged. docs/daily-run.md
#
#   sh scripts/daily-run.sh              one run, as the job does it
#   sh scripts/daily-run.sh --dry-run    print every command a run would start; touch nothing
#   sh scripts/daily-run.sh summary      the summary of the last run
#   sh scripts/daily-run.sh pause        no run starts until `resume`
#   sh scripts/daily-run.sh resume       let runs start again
#   sh scripts/daily-run.sh plist        the launchd property list, with this checkout's paths
#                                        (it holds the database password: install it mode 600)
#
# It never clears an audit, archives, exports, commits or pushes. A claim a read drafts
# is held awaiting audit (docs/adr/0007), and releasing it stays a deliberate act.
#
# Every path comes from the lines below. The checkout is the one this script is in.
set -u

label="com.thenwhat.daily-run"
root=$(cd "$(dirname "$0")/.." && pwd)
env_file="${THENWHAT_ENV_FILE:-$root/.env}"
state="${DAILY_RUN_STATE_DIR:-$HOME/Library/Application Support/thenwhat/daily-run}"
logs="${DAILY_RUN_LOG_DIR:-$HOME/Library/Logs/thenwhat/daily-run}"
# Where scripts/fetch_link_files.py writes and `load-links` reads. On the operator's
# machine this is a link to a folder on an external drive.
link_files="$root/data/link-files"
template="$root/scripts/$label.plist"
paused="$state/paused"
lock="$state/lock"
latest="$state/latest.md"

# A setting: the environment first, then the last line for it in the .env file. The file
# is read as text and never run. Only the names asked for here are looked at.
setting() {
  value=$(printenv "$1" 2>/dev/null || true)
  if [ -z "$value" ] && [ -f "$env_file" ]; then
    value=$(sed -n "s/^$1=//p" "$env_file" | tail -n 1 |
      sed -e 's/[[:space:]]*$//' -e "s/^'\\(.*\\)'\$/\\1/" -e 's/^"\(.*\)"$/\1/')
  fi
  printf '%s' "${value:-${2-}}"
}

whole_number() {
  case "$2" in
    '' | *[!0-9]*) echo "$1 must be a whole number, and is '$2'." >&2; exit 2 ;;
  esac
}

amount() {
  case "$2" in
    '' | *[!0-9.]* | *.*.*) echo "$1 must be an amount in dollars, and is '$2'." >&2; exit 2 ;;
  esac
}

command="run"
dry=0
for word in "$@"; do
  case "$word" in
    --dry-run) dry=1 ;;
    run | summary | pause | resume | plist) command="$word" ;;
    *) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
  esac
done

case "$command" in
  summary)
    if [ -f "$latest" ]; then cat "$latest"; else echo "No run has written a summary yet."; fi
    [ -e "$paused" ] && echo "Paused: no run starts until 'sh scripts/daily-run.sh resume'."
    exit 0
    ;;
  pause)
    mkdir -p "$state"
    : >"$paused"
    echo "Paused. A run in hand finishes; none starts until 'resume'."
    exit 0
    ;;
  resume)
    rm -f "$paused"
    echo "Resumed. The next run starts at its usual hour."
    exit 0
    ;;
  plist)
    # The database as this machine reaches it. Compose gives its containers their own
    # address; the job runs on the host, so it needs the published port on 127.0.0.1.
    # Escaped for XML, and passed to awk through the environment so that no character in
    # it is read as part of a command.
    database=$(setting DAILY_RUN_DATABASE_URL "")
    entry=""
    if [ -n "$database" ]; then
      entry="    <key>DATABASE_URL</key><string>$(printf '%s' "$database" |
        sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g')</string>"
      echo "This property list holds the database password. Install it readable by you alone: (umask 077 && sh scripts/daily-run.sh plist > ~/Library/LaunchAgents/$label.plist), as in docs/daily-run.md." >&2
    else
      echo "DAILY_RUN_DATABASE_URL is not set, so the property list gives the job no database address. Set it in $env_file and write the property list again." >&2
    fi
    hour=$(setting DAILY_RUN_HOUR 4)
    minute=$(setting DAILY_RUN_MINUTE 30)
    whole_number DAILY_RUN_HOUR "$hour"
    whole_number DAILY_RUN_MINUTE "$minute"
    sed -e "s|@ROOT@|$root|g" -e "s|@HOME@|$HOME|g" -e "s|@LOGS@|$logs|g" \
      -e "s|@ENV_FILE@|$env_file|g" -e "s|@HOUR@|$hour|g" -e "s|@MINUTE@|$minute|g" "$template" |
      ENTRY="$entry" awk '/@DATABASE_URL_ENTRY@/ { if (ENVIRON["ENTRY"] != "") print ENVIRON["ENTRY"]; next } { print }'
    exit 0
    ;;
esac

# --- One run -----------------------------------------------------------------

read_limit=$(setting DAILY_RUN_READ_LIMIT 40)
triage_limit=$(setting DAILY_RUN_TRIAGE_LIMIT 2000)
refresh_limit=$(setting DAILY_RUN_REFRESH_LIMIT 150)
read_workers=$(setting DAILY_RUN_READ_WORKERS 2)
fetch_days=$(setting DAILY_RUN_FETCH_DAYS 3)
keep_days=$(setting DAILY_RUN_KEEP_DAYS 30)
margin=$(setting DAILY_RUN_SPEND_MARGIN_USD 1)
day_budget=$(setting DAILY_RUN_DAY_BUDGET_USD "")
ceiling=$(setting LLM_MONTHLY_BUDGET_USD "")
# The database address the pipeline is given. The settings file has none (Compose gives
# its containers their own), so it comes from DATABASE_URL in the environment (the
# property list sets it), else DAILY_RUN_DATABASE_URL, else DATABASE_URL in the file.
# Only where it came from is ever logged: it holds the password.
database_from="DATABASE_URL in the environment"
database=$(printenv DATABASE_URL 2>/dev/null || true)
if [ -z "$database" ]; then
  database_from="DAILY_RUN_DATABASE_URL"
  database=$(setting DAILY_RUN_DATABASE_URL "")
fi
if [ -z "$database" ]; then
  database_from="DATABASE_URL in $env_file"
  database=$(setting DATABASE_URL "")
fi
if [ -n "$database" ]; then
  export DATABASE_URL="$database"
else
  database_from=""
fi
whole_number DAILY_RUN_READ_LIMIT "$read_limit"
whole_number DAILY_RUN_TRIAGE_LIMIT "$triage_limit"
whole_number DAILY_RUN_REFRESH_LIMIT "$refresh_limit"
whole_number DAILY_RUN_READ_WORKERS "$read_workers"
whole_number DAILY_RUN_FETCH_DAYS "$fetch_days"
whole_number DAILY_RUN_KEEP_DAYS "$keep_days"
amount DAILY_RUN_SPEND_MARGIN_USD "$margin"
[ -n "$day_budget" ] && amount DAILY_RUN_DAY_BUDGET_USD "$day_budget"
[ -n "$ceiling" ] && amount LLM_MONTHLY_BUDGET_USD "$ceiling"
if [ "$read_limit" -lt 1 ] || [ "$triage_limit" -lt 1 ]; then
  echo "DAILY_RUN_READ_LIMIT and DAILY_RUN_TRIAGE_LIMIT must be 1 or more." >&2
  exit 2
fi
if [ "$fetch_days" -lt 1 ] || [ "$fetch_days" -gt 28 ]; then
  echo "DAILY_RUN_FETCH_DAYS must be 1 to 28: the window may touch two months at most." >&2
  exit 2
fi
if [ "$read_workers" -lt 1 ] || [ "$read_workers" -gt 4 ]; then
  echo "DAILY_RUN_READ_WORKERS must be 1 to 4: the page reader takes at most 4 at once." >&2
  exit 2
fi

today=$(date '+%Y-%m-%d')
# The months the link window touches, in UTC as the fetch counts them: the month of the
# window's first day and, when it differs, this month. `date -v` on macOS, `-d` elsewhere.
window_first=$(date -u -v-"$fetch_days"d '+%Y-%m' 2>/dev/null || date -u -d "$fetch_days days ago" '+%Y-%m')
window_last=$(date -u '+%Y-%m')
window_months=$window_first
[ "$window_first" != "$window_last" ] && window_months="$window_first $window_last"
log="$logs/$today.log"
summary="$state/summary-$today.md"
work=""
stopped=""   # why the rest of the run is skipped; empty while it goes on
trouble=0    # 1 when something went wrong, as opposed to a stop that was meant
failed=""
notes=""

say() {
  if [ "$dry" = 1 ]; then
    printf '# %s\n' "$*"
  else
    printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >>"$log"
  fi
}

# Print a command as it would be typed.
show() {
  line="+"
  for part in "$@"; do
    case "$part" in
      '' | *[!A-Za-z0-9_./:=@%+,-]*) line="$line '$part'" ;;
      *) line="$line $part" ;;
    esac
  done
  printf '%s\n' "$line"
}

stop() {
  stopped="$1"
  say "stopped: $1"
}

in_pipeline() { uv run --env-file "$env_file" --directory "$root/pipeline" "$@"; }
figures() { in_pipeline python "$root/scripts/daily_run_figures.py" "$@"; }

# run_step <name> <command…>: start, end and outcome go to the log, the command's own
# report with them. A step that fails is recorded and the run goes on: every step picks
# up where it left off, so the next run takes what this one missed.
run_step() {
  name=$1
  shift
  if [ -n "$stopped" ]; then
    say "skip $name"
    return 0
  fi
  say "start $name"
  if [ "$dry" = 1 ]; then
    show "$@"
    return 0
  fi
  "$@" >"$work/$name.out" 2>&1
  code=$?
  cat "$work/$name.out" >>"$log"
  if [ "$code" -eq 0 ]; then
    say "end $name: ok"
  else
    say "end $name: failed, exit $code"
    failed="$failed $name"
    trouble=1
  fi
  return "$code"
}

pipeline_step() {
  name=$1
  shift
  run_step "$name" uv run --env-file "$env_file" --directory "$root/pipeline" thenwhat "$@"
}

# Before each step that spends: stop the run when the month's recorded spend, plus the
# margin, would reach the ceiling, or when today's has reached the day's own ceiling.
# The pipeline refuses a call at the ceiling as well; this stops before a step starts.
# A spend that cannot be read stops the run too.
spend_check() {
  [ -n "$stopped" ] && return 0
  if [ "$dry" = 1 ]; then
    say "spend check before $1"
    show uv run --env-file "$env_file" --directory "$root/pipeline" \
      python "$root/scripts/daily_run_figures.py" spend
    return 0
  fi
  if ! spent=$(figures spend 2>>"$log"); then
    trouble=1
    stop "the month's spend could not be read before $1, so nothing that spends was started"
    return 0
  fi
  spent_month=${spent% *}
  spent_today=${spent#* }
  answer=$(awk -v m="$spent_month" -v t="$spent_today" -v c="$ceiling" -v g="$margin" \
    -v d="$day_budget" 'BEGIN {
      if (m + g >= c) print "month"; else if (d != "" && t + 0 >= d + 0) print "day"; else print "ok"
    }')
  say "spend before $1: \$$spent_month this month of \$$ceiling, \$$spent_today today"
  case "$answer" in
    month) stop "before $1 the month's spend was \$$spent_month, within \$$margin of the \$$ceiling ceiling" ;;
    day) stop "before $1 today's spend was \$$spent_today, at the day's ceiling of \$$day_budget" ;;
  esac
}

# Read the registries again for published claims: `thenwhat fetch`, one claim at a time.
# With a limit, each run takes the next claims in slug order and the one after starts
# where it ended, so every claim is asked about in turn.
refresh() {
  if [ -n "$stopped" ]; then
    say "skip refresh"
    return 0
  fi
  if [ "$dry" = 1 ]; then
    spend_check refresh
    say "start refresh"
    show uv run --env-file "$env_file" --directory "$root/pipeline" \
      python "$root/scripts/daily_run_figures.py" published
    if [ "$refresh_limit" -gt 0 ]; then
      say "then for the next $refresh_limit published claims in turn, the spend check again before every 25th:"
    else
      say "then for every published claim, the spend check again before every 25th:"
    fi
    show uv run --env-file "$env_file" --directory "$root/pipeline" thenwhat fetch "<slug>"
    return 0
  fi
  say "start refresh"
  if ! slugs=$(figures published 2>>"$log"); then
    say "end refresh: failed, the published claims could not be listed"
    failed="$failed refresh"
    trouble=1
    return 0
  fi
  total=$(printf '%s\n' "$slugs" | grep -c . || true)
  if [ "$refresh_limit" -gt 0 ] && [ "$refresh_limit" -lt "$total" ]; then
    offset=$(cat "$state/refresh-offset" 2>/dev/null || echo 0)
    case "$offset" in '' | *[!0-9]*) offset=0 ;; esac
    offset=$((offset % total))
    slugs=$(printf '%s\n' "$slugs" | awk -v s="$offset" -v n="$refresh_limit" \
      '{ a[NR] = $0 } END { for (i = 0; i < n; i++) print a[(s + i) % NR + 1] }')
  else
    offset=""
  fi
  asked=0
  bad=0
  : >"$work/refresh.out"
  for slug in $slugs; do
    if [ $((asked % 25)) -eq 0 ]; then
      spend_check refresh
      [ -n "$stopped" ] && break
    fi
    asked=$((asked + 1))
    if ! in_pipeline thenwhat fetch "$slug" >>"$work/refresh.out" 2>&1; then
      bad=$((bad + 1))
      echo "failed: $slug" >>"$work/refresh.out"
    fi
  done
  cat "$work/refresh.out" >>"$log"
  [ -n "$offset" ] && echo $(((offset + asked) % total)) >"$state/refresh-offset"
  events=$(awk '/^Recorded [0-9]+ new/ { n += $2 } END { print n + 0 }' "$work/refresh.out")
  refresh_line="asked the registries about $asked of $total published claims: $events new events, $bad claims failed"
  if [ "$bad" -gt 0 ]; then
    failed="$failed refresh($bad-of-$asked-claims)"
    trouble=1
  fi
  say "end refresh: $refresh_line"
}

# The first line of a step's report that matches, for the summary.
report_of() {
  if [ -f "$work/$1.out" ]; then
    grep -m 1 -E "$2" "$work/$1.out" || echo "ran; its report is in the log"
  else
    echo "$3"
  fi
}

write_summary() {
  if [ -n "$failed" ]; then
    outcome="finished with failures"
  elif [ -n "$stopped" ]; then
    outcome="stopped early"
  else
    outcome="finished"
  fi
  {
    echo "# Daily run, $today"
    echo
    echo "Started $started, ended $(date '+%H:%M'). Outcome: $outcome."
    [ -n "$database_from" ] && echo "Database address from $database_from."
    [ -n "$stopped" ] && echo "Stopped: $stopped. The steps after that point did not run."
    echo
    echo "## What ran"
    echo
    echo "- Link files: $(report_of fetch-links '^Months written' 'no report')"
    for window_month in $window_months; do
      echo "- Loaded $window_month: $(report_of "load-links $window_month" '^Read ' 'nothing loaded')"
    done
    echo "- Screened: $(report_of screen '^link_screen:' 'did not run')"
    echo "- Scored: $(report_of score '^link_triage:' 'did not run')"
    echo "- Read: $(report_of read '^link_read:' 'did not run')"
    if [ -f "$work/prepare.out" ]; then
      echo "- Prepared: $(grep -c -E ' \([0-9]+s\)$' "$work/prepare.out" || true) claims worked on"
    else
      echo "- Prepared: did not run"
    fi
    echo "- Trials: $(report_of trials '^Loaded ' 'did not run')"
    echo "- Registries: ${refresh_line:-did not run}"
    for name in screen score read trials; do
      [ -f "$work/$name.out" ] && grep -E '^Stopped: ' "$work/$name.out" | sed "s/^/- $name: /"
    done
    echo
    echo "## Claims, before and after"
    echo
    echo "- Awaiting audit: ${audit_before:-?} before, ${audit_after:-?} after. These are what the reads drafted and the rules approved; none is on the site."
    echo "- Awaiting review: ${pending_before:-?} before, ${pending_after:-?} after."
    echo "- Approved and not held: ${published_before:-?} before, ${published_after:-?} after. This run exported and published nothing."
    echo
    echo "## Spend"
    echo
    echo "- Today: \$${spent_today:-?}. This month: \$${spent_month:-?} of the \$${ceiling:-?} ceiling."
    echo
    echo "## Failed"
    echo
    if [ -n "$failed" ]; then
      for name in $failed; do echo "- $name"; done
    else
      echo "- Nothing."
    fi
    if [ -n "$notes" ]; then
      echo
      echo "## Notes"
      echo
      printf '%b' "$notes"
    fi
    echo
    echo "## Next, by a person or an assistant"
    echo
    echo "The audit and the publish are not this job's: \`thenwhat audit list\`, then docs/daily-run.md, \"Audit and publish\"."
    echo
    echo "Log: $log"
  } >"$summary"
  cp "$summary" "$latest"
}

if [ "$dry" = 1 ]; then
  say "dry run: nothing below is started, and no file, lock or log is written"
  say "checkout $root"
  say "settings from $env_file"
  [ -f "$env_file" ] || say "would stop here: that file is missing"
  [ -d "$link_files/" ] || say "would stop here: $link_files is not there (is the drive mounted?)"
  [ -n "$ceiling" ] || say "would stop here: LLM_MONTHLY_BUDGET_USD is not set"
  if [ -n "$database_from" ]; then
    say "database address from $database_from"
  else
    say "would stop here: no database address is set (DAILY_RUN_DATABASE_URL)"
  fi
  [ -e "$paused" ] && say "would not start: paused"
  say "lock $lock, log $log, summary $summary"
else
  mkdir -p "$state" "$logs" || exit 1
  started=$(date '+%H:%M')
  if [ -e "$paused" ]; then
    say "paused: not started. Remove the pause with: sh scripts/daily-run.sh resume"
    exit 0
  fi
  # The lock: a folder, which only one run can make. One left by a run that died is
  # taken over; one whose run is alive means this run does not start.
  if ! mkdir "$lock" 2>/dev/null; then
    holder=$(cat "$lock/pid" 2>/dev/null || true)
    if [ -n "$holder" ] && kill -0 "$holder" 2>/dev/null; then
      say "another run is still going (process $holder): not started"
      exit 0
    fi
    say "a lock was left by a run that is gone (process ${holder:-unknown}): taking it over"
    rm -rf "$lock"
    mkdir "$lock" || exit 1
  fi
  echo $$ >"$lock/pid"
  work=$(mktemp -d "$state/run.XXXXXX") || exit 1
  trap 'rm -rf "$lock" "$work"' EXIT
  trap 'exit 130' INT TERM
  say "run begins: checkout $root, settings from $env_file"

  # Stops that are meant: the run ends here, says why, and changes nothing.
  if [ ! -f "$env_file" ]; then
    trouble=1
    stop "the settings file $env_file is missing"
  elif unquoted=$(grep -n -E "^[A-Za-z_]+=[[:space:]]*[{[]" "$env_file" | cut -d= -f1) && [ -n "$unquoted" ]; then
    # `uv run --env-file` drops every line after an unquoted JSON value, without a word.
    trouble=1
    stop "a JSON value in $env_file is not in single quotes (line:name $(echo "$unquoted" | tr '\n' ' ')), and every setting after it would be lost"
  elif [ -z "$database_from" ]; then
    trouble=1
    stop "no database address is set. Put DAILY_RUN_DATABASE_URL in $env_file, the database's published port on 127.0.0.1 (see .env.example), then write the property list again"
  elif [ -z "$ceiling" ]; then
    trouble=1
    stop "LLM_MONTHLY_BUDGET_USD is not set, so there is no ceiling to hold the run to"
  elif ! command -v uv >/dev/null 2>&1; then
    trouble=1
    stop "uv is not on the PATH ($PATH)"
  elif [ ! -d "$link_files/" ]; then
    stop "$link_files is not there. If it is on an external drive, the drive is not mounted"
  fi
fi

# Is the database there? After a restart it is not until Docker and the db service are up.
db_ok=0
if pipeline_step database db-check; then
  [ -z "$stopped" ] && db_ok=1
else
  stop "the database did not answer. Start it with: docker compose up -d --wait db"
fi

if [ "$dry" = 1 ]; then
  say "claims before"
  show uv run --env-file "$env_file" --directory "$root/pipeline" \
    python "$root/scripts/daily_run_figures.py" counts
elif [ -z "$stopped" ] && before=$(figures counts 2>>"$log"); then
  # shellcheck disable=SC2086
  set -- $before
  published_before=$1 pending_before=$2 audit_before=$3
fi

# 1. The newest link files: the Hacker News stories of the last DAILY_RUN_FETCH_DAYS days,
#    merged into each month's file the window touches. One or two queries to the public
#    ClickHouse copy of Hacker News (docs/sources.md); spends nothing.
if [ -f "$root/scripts/fetch_link_files.py" ] || [ "$dry" = 1 ]; then
  [ -f "$root/scripts/fetch_link_files.py" ] || say "note: scripts/fetch_link_files.py is not in this checkout; a run would skip this step"
  run_step fetch-links uv run --env-file "$env_file" --directory "$root/pipeline" \
    python "$root/scripts/fetch_link_files.py" hackernews --since-days "$fetch_days" || true
elif [ -z "$stopped" ]; then
  say "skip fetch-links: scripts/fetch_link_files.py is not in this checkout"
  notes="$notes- The link files were not fetched: scripts/fetch_link_files.py is not in this checkout.\\n"
fi

# 2. Load each month's file the window touched. Sends no request. Loading a link again
#    adds nothing.
for window_month in $window_months; do
  hn_file="$link_files/hackernews/$window_month.parquet"
  if [ -f "$hn_file" ] || [ "$dry" = 1 ]; then
    pipeline_step "load-links $window_month" backfill load-links hackernews "$hn_file" || true
  elif [ -z "$stopped" ]; then
    say "skip load-links $window_month: $hn_file is not there"
    notes="$notes- Nothing was loaded for $window_month: there is no link file for it.\\n"
  fi
done

# 3. Screen: link each lead to what the database already holds. No source, no model.
pipeline_step screen backfill run link_screen || true

# 4. Score the titles. Calls a model.
spend_check score
pipeline_step score backfill run link_triage --limit "$triage_limit" || true

# 5. Read a capped number of passed leads. Asks the page reader and calls a model. The
#    reader's own settings (READER_READS_AT_ONCE, READER_OUTLET_GAP_SECONDS,
#    SOURCE_ALLOWANCES) pace it; this only says how many records are worked on at once.
spend_check read
pipeline_step read backfill run link_read --limit "$read_limit" --workers "$read_workers" || true

# 6. Search the registries for the claims the reads drafted. Those the rules approve
#    are held awaiting audit; nothing here releases them.
spend_check prepare
pipeline_step prepare prepare --pending || true

# 7. Every stored trial kept current: only the trials ClinicalTrials.gov updated since
#    the last completed load of the set are asked for, a thousand a request. Spends no
#    model money. Each request is claimed against the registry's allowance
#    (SOURCE_ALLOWANCES); when it is used up the load stops, says so, and is not a
#    failure, and the next run asks again from the same date. A trial whose searched
#    fields changed becomes due for news_search, which this job never starts.
pipeline_step trials backfill load-trials --trials interventional --changes-only || true

# 8. Registry status of published claims. The spend check is inside: before the first
#    claim and before every 25th after it.
refresh

# 9. What the day took, into the log. Runs even when the run stopped early for spend.
held="$stopped"
[ "$db_ok" = 1 ] && stopped=""
pipeline_step measure measure --days 1 || true
stopped="$held"

[ "$dry" = 1 ] && {
  say "claims and spend after, for the summary"
  show uv run --env-file "$env_file" --directory "$root/pipeline" \
    python "$root/scripts/daily_run_figures.py" counts
  show uv run --env-file "$env_file" --directory "$root/pipeline" \
    python "$root/scripts/daily_run_figures.py" spend
  say "never run by this job: thenwhat audit clear, thenwhat archive, thenwhat export, make publish-data, git"
  exit 0
}

if [ "$db_ok" = 1 ] && after=$(figures counts 2>>"$log"); then
  # shellcheck disable=SC2086
  set -- $after
  published_after=$1 pending_after=$2 audit_after=$3
fi
if [ "$db_ok" = 1 ] && spent=$(figures spend 2>>"$log"); then
  spent_month=${spent% *}
  spent_today=${spent#* }
fi
write_summary
say "run ends: summary at $summary"
find "$logs" -name '*.log' -mtime +"$keep_days" -delete 2>/dev/null
find "$state" -name 'summary-*.md' -mtime +"$keep_days" -delete 2>/dev/null
exit "$trouble"
