#!/bin/sh
# Rebuild the extension test corpus and replace the Google Sheet with it.
#   sh extension/test-corpus/sync.sh            check, match, assemble, upload
#   LOOKUPS=1 sh extension/test-corpus/sync.sh  also ask the lookup service about new rows
#                                               (needs `make lookup-dev` running; paid model calls)
# Upload needs an rclone remote for Google Drive, named by GDRIVE_REMOTE (default gdrive).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
remote=${GDRIVE_REMOTE:-gdrive}
target=${SHEET_PATH:-thenwhat/Extension test URLs.xlsx}

mkdir -p "$here/.work"
python3 -I "$here/check.py"
node "$here/match.mjs"
if [ "${LOOKUPS:-0}" = 1 ]; then node "$here/lookups.mjs"; fi
uv run --quiet --with openpyxl python -I "$here/assemble.py"
if [ "${UPLOAD:-1}" = 1 ]; then
  rclone copyto "$here/.work/extension-test-urls.xlsx" "$remote:$target" --drive-import-formats xlsx
  echo "Uploaded to $remote:$target"
fi
