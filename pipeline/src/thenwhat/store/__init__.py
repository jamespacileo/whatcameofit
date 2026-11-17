"""The tracker's records in the truth store's natural-key form (`store/README.md`).

- `form.py`: the staged record, and the rules every kind shares (times, payload
  checksums, address keys, an event's content checksum).
- `records.py`: from today's Postgres rows to store records, one function a kind.
- `rows.py`: from a store record back to what finds or creates its Postgres row.
- `gather.py`, `place.py`: the same for a whole database, against a session.

Behavior: openspec change `cloudflare-source-of-truth`, task 4.1.
"""
