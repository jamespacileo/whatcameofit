#!/bin/sh
# Keeps a long backfill going without anyone watching it. A step that needs more
# requests than a source allows in one period runs for weeks: this job starts
# `thenwhat backfill run` again every half hour, and the run itself stops when the
# source's allowance is used up or the source asks it to wait. A finished record is
# never processed twice, so starting it again is always safe.
#
#   sh scripts/backfill-job.sh install [step]   set the job up for this user (default step: news_search)
#   sh scripts/backfill-job.sh status           what is done, what is due, and the last lines of the log
#   sh scripts/backfill-job.sh pause            stop the run now and do not start it again
#   sh scripts/backfill-job.sh resume           let it start again
#   sh scripts/backfill-job.sh remove           take the job out; the log and the work done stay
#   sh scripts/backfill-job.sh run [step]       one run, as the job does it
#
# The job runs from the checkout this script is in, so keep that checkout where it is
# and on a commit that has the step. It is a launchd agent of the logged-in user: it
# runs only while that user is logged in and the machine is awake.
#
# Settings are read from two files, the second winning:
#   $THENWHAT_ENV_FILE  the operator's .env, with the contact address and source keys
#   $BACKFILL_SETTINGS  settings for this job only, for example which database
# Neither is written to by this script except that `install` creates the second when
# it is missing. Logs and state stay on the internal disk.
set -eu

label="com.thenwhat.backfill"
root=$(cd "$(dirname "$0")/.." && pwd)
state="$HOME/Library/Application Support/thenwhat"
logs="$HOME/Library/Logs/thenwhat"
log="$logs/backfill.log"
plist="$HOME/Library/LaunchAgents/$label.plist"
paused="$state/backfill.paused"
env_file="${THENWHAT_ENV_FILE:-$state/thenwhat.env}"
settings="${BACKFILL_SETTINGS:-$state/backfill.env}"
domain="gui/$(id -u)"

say() { printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; }

load_settings() {
  for file in "$env_file" "$settings"; do
    if [ -f "$file" ]; then
      set -a
      # shellcheck disable=SC1090
      . "$file"
      set +a
    fi
  done
}

thenwhat() { uv run --directory "$root/pipeline" thenwhat "$@"; }

case "${1:-}" in
  run)
    step="${2:-news_search}"
    mkdir -p "$logs" "$state"
    if [ -e "$paused" ]; then
      say "paused: not started. Remove the pause with: sh scripts/backfill-job.sh resume" >>"$log"
      exit 0
    fi
    load_settings
    say "start $step" >>"$log"
    # The run's own report goes to the log: counts and reasons only, never a title.
    if thenwhat backfill run "$step" >>"$log" 2>&1; then
      say "end $step" >>"$log"
    else
      say "end $step: refused or failed, see the lines above" >>"$log"
    fi
    ;;

  install)
    step="${2:-news_search}"
    mkdir -p "$logs" "$state" "$HOME/Library/LaunchAgents"
    if [ ! -f "$settings" ]; then
      umask 077
      cat >"$settings" <<'EOF'
# Settings for the backfill job only. Read after the operator's .env, so a line here wins.
# DATABASE_URL=postgresql+psycopg://thenwhat:thenwhat@127.0.0.1:5433/thenwhat
# MEDIACLOUD_COLLECTION_IDS=
# MEDIACLOUD_SOURCE_IDS=
EOF
      echo "Created $settings. Set the database and what to search in it, then install again."
      exit 1
    fi
    cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/sh</string>
    <string>$root/scripts/backfill-job.sh</string>
    <string>run</string>
    <string>$step</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>THENWHAT_ENV_FILE</key><string>$env_file</string>
    <key>BACKFILL_SETTINGS</key><string>$settings</string>
  </dict>
  <key>WorkingDirectory</key><string>$root</string>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$logs/backfill-launchd.log</string>
  <key>StandardErrorPath</key><string>$logs/backfill-launchd.log</string>
</dict>
</plist>
EOF
    launchctl bootout "$domain/$label" 2>/dev/null || true
    launchctl bootstrap "$domain" "$plist"
    echo "Installed $label for the step '$step'. It starts now and then every half hour."
    echo "Log: $log"
    ;;

  status)
    load_settings
    if launchctl print "$domain/$label" >/dev/null 2>&1; then
      launchctl print "$domain/$label" | grep -E '^\s*(state|pid|last exit code) =' || true
    else
      echo "The job is not installed."
    fi
    [ -e "$paused" ] && echo "Paused: it will not start until 'resume'."
    thenwhat backfill plan
    if [ -f "$log" ]; then
      echo "--- last lines of $log"
      tail -n 12 "$log"
    fi
    ;;

  pause)
    mkdir -p "$state"
    : >"$paused"
    # The run commits each record on its own, so ending it loses at most the record
    # in hand, which stays due.
    launchctl kill TERM "$domain/$label" 2>/dev/null || true
    echo "Paused. The run in hand was told to stop; nothing starts until 'resume'."
    ;;

  resume)
    rm -f "$paused"
    launchctl kickstart "$domain/$label" 2>/dev/null || echo "The job is not installed; run 'install'."
    echo "Resumed."
    ;;

  remove)
    launchctl bootout "$domain/$label" 2>/dev/null || true
    rm -f "$plist"
    echo "Removed $label. The log, the settings and the work already done are kept."
    ;;

  *)
    sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
