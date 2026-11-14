#!/bin/sh
# Lists what an AI assistant decided on one claim, so that the operator can repeat the
# decisions they agree with. A claim is published either way; the export marks it as
# not checked by a person while any assistant decision stands on it, its matches or its
# events.
#
#   sh scripts/assistant-decisions.sh <claim-slug>
#
# Prints the claim's id, then the ids of its matches and events the assistant approved
# or rejected, one line per kind and decision. Reads only; decides nothing.
# Needs the database running (`docker compose up -d`).
set -eu

slug="${1:?Give a claim slug.}"
case "$slug" in
  *[!a-z0-9-]*) echo "A slug holds only lower-case letters, digits and hyphens." >&2; exit 1 ;;
esac

docker compose exec -T db sh -c "psql -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\" -At -F ': ' -c \"
select 'claim (' || c.review_state || ' by ' || coalesce(c.reviewed_by, 'nobody') || ')', c.id::text
  from claim c where c.slug = '$slug'
union all
select 'match ' || m.review_state, string_agg(m.id::text, ' ' order by m.id)
  from entity_match m join entity e on e.id = m.entity_id join claim c on c.id = e.claim_id
  where c.slug = '$slug' and m.reviewed_by = 'assistant' group by m.review_state
union all
select 'event ' || ev.review_state, string_agg(ev.id::text, ' ' order by ev.id)
  from evidence_event ev join claim c on c.id = ev.claim_id
  where c.slug = '$slug' and ev.reviewed_by = 'assistant' group by ev.review_state
\""
