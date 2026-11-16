#!/usr/bin/env bash
# Runs the schema and one merge on D1's local engine (Miniflare). No network, no account.
# `wrangler d1 execute --file` cannot bind parameters, so the run's id is written into
# the two statements that take it; in the Worker it is bound as ?1.
set -euo pipefail
cd "$(dirname "$0")"
state="$(mktemp -d)"
d1() { wrangler d1 execute thenwhat-store-proof --local --persist-to "$state" --config wrangler.jsonc "$@"; }

d1 --file ../schema.sql >/dev/null
cat > "$state/stage.sql" <<'SQL'
INSERT INTO run (id, writer, device, commit_sha, registered_at) VALUES ('r1', 'device', 'mini', 'abc1234', '2026-11-16T10:00:00Z');
INSERT INTO run_stated VALUES ('r1', 'claim', 1), ('r1', 'source_article', 1), ('r1', 'registry_trial', 1), ('r1', 'payload', 1);
INSERT INTO stg VALUES ('r1', 'payload', 'p', '{"sha256":"0000000000000000000000000000000000000000000000000000000000000001","bytes":20,"body":"{\"nctId\":\"NCT1\"}"}');
INSERT INTO stg VALUES ('r1', 'claim', 'semaglutide-obesity', '{"slug":"semaglutide-obesity","headline":"h","summary":"s","vertical":"metabolic","indication":"obesity","origin":"backfill","created_at":"2026-11-01","awaiting_audit_at":"2026-11-01"}');
INSERT INTO stg VALUES ('r1', 'source_article', 'a', '{"slug":"semaglutide-obesity","url_key":"bbc.com/a","url":"https://bbc.com/a","outlet":"bbc.com","title":"t","published_date":"2026-10-01"}');
INSERT INTO stg VALUES ('r1', 'registry_trial', 't', '{"registry_name":"clinicaltrials.gov","external_id":"NCT1","title":"Semaglutide in obesity","conditions":["Obesity"],"interventions":[],"intervention_names":"Semaglutide","phases":[],"overall_status":"RECRUITING","payload_sha256":"0000000000000000000000000000000000000000000000000000000000000001","fetched_at":"2026-11-01"}');
SQL
d1 --file "$state/stage.sql" >/dev/null
# One statement a line, comments dropped: the form a batch is sent in.
python3 - "$state/merge.sql" <<'PY'
import pathlib, sys
out = []
for chunk in pathlib.Path("../merge.sql").read_text().split("\n;\n"):
    lines = [l.strip() for l in chunk.splitlines() if l.strip() and not l.startswith("--")]
    if lines:
        out.append(" ".join(lines).replace("?1", "'r1'") + ";")
pathlib.Path(sys.argv[1]).write_text("\n".join(out) + "\n")
PY
d1 --file "$state/merge.sql" >/dev/null
for query in \
  "SELECT r.status, m.kind, m.resolved, m.added FROM run r JOIN merge_report m ON m.run_id = r.id ORDER BY m.kind" \
  "SELECT t.external_id AS found_by_search FROM registry_trial_fts f JOIN registry_trial t ON t.id = f.rowid WHERE registry_trial_fts MATCH 'obesity'"; do
  d1 --json --command "$query" | python3 -c "import json,sys; [print(row) for row in json.load(sys.stdin)[0]['results']]"
done
rm -rf "$state"
