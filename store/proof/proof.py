"""A local proof of the store's schema and merge path, in plain SQLite. Nothing is deployed.

It builds store/schema.sql, runs every scenario below through store/merge.sql exactly as a
D1 batch would run it (all statements in one transaction, nothing read in between), loads
the sample exported from Postgres through the same path, and projects the store's size at
full data against D1's limits.

    python3 store/proof/proof.py            # scenarios, then the sample when it is present
    python3 store/proof/proof.py --scenarios

Only the standard library is used.
"""

import json
import pathlib
import sqlite3
import sys
import time

STORE = pathlib.Path(__file__).resolve().parent.parent
SAMPLE = STORE / "proof" / "sample" / "records.jsonl"
OUT = STORE / "proof" / "out"

# D1's limits on the paid plan, read from developers.cloudflare.com/d1/platform/limits on
# 2026-11-16.
D1_DATABASE_BYTES = 10 * 1000**3
D1_ROW_BYTES = 2_000_000
D1_STATEMENT_BYTES = 100_000
D1_BOUND_PARAMETERS = 100
D1_QUERY_SECONDS = 30


def statements(path):
    """A file's statements: split at a line holding only `;`, comment lines dropped."""
    out = []
    for chunk in path.read_text().split("\n;\n"):
        lines = [line for line in chunk.splitlines() if line.strip() and not line.startswith("--")]
        if lines:
            out.append("\n".join(lines))
    return out


def named(path):
    out, name, lines = {}, None, []
    for line in path.read_text().splitlines():
        if line.startswith("-- name:"):
            name, lines = line.split(":", 1)[1].strip(), []
        elif line.strip() == ";" and name:
            out[name], name = "\n".join(lines), None
        elif name and not line.startswith("--"):
            lines.append(line)
    return out


MERGE = statements(STORE / "merge.sql")
INGEST = named(STORE / "ingest.sql")
PREVIEW = statements(STORE / "preview.sql")

# Every merge the proof runs is first previewed; these count how the two reports compared.
previews = {"same": 0, "differ": [], "not reconciling seen": 0, "not reconciling missed": []}


class Store:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute("PRAGMA foreign_keys = ON")  # D1 enforces foreign keys
        self.db.executescript((STORE / "schema.sql").read_text())
        self.db.execute("INSERT INTO store_step VALUES ('link_triage', 3)")
        self.runs = 0

    def one(self, sql, *args):
        row = self.db.execute(sql, args).fetchone()
        return row[0] if row else None

    def all(self, sql, *args):
        return self.db.execute(sql, args).fetchall()

    def stage(self, run, records, writer="device", device="mini", stated=None, steps=None, at="2026-11-16T10:00:00Z"):
        """Register a run and hand over its records: [(kind, key, body), ...]."""
        lookup = writer == "lookup"
        self.db.execute(INGEST["register_run"], (run, writer, None if lookup else device,
                        "extension" if lookup else None, "abc1234", at[:10] if lookup else at, None, None))
        self.db.execute(INGEST["state_steps"], (run, json.dumps(steps or {"link_triage": 3})))
        counts = {}
        for kind, _, _ in records:
            counts[kind] = counts.get(kind, 0) + 1
        self.db.execute(INGEST["state_counts"], (run, json.dumps(stated or counts)))
        chunk = [{"kind": k, "key": key, "body": body} for k, key, body in records]
        for i in range(0, len(chunk), 2000):
            self.db.execute(INGEST["stage"], (run, json.dumps(chunk[i:i + 2000])))

    def preview(self, run):
        """store/preview.sql as a D1 batch: committed, and it writes nothing that stays.
        Returns the report it counts and whether the run's counts would reconcile."""
        report, reconciles, registered = {}, True, False
        self.db.execute("BEGIN")
        for sql in PREVIEW:
            cursor = self.db.execute(sql, (run,) if "?1" in sql else ())
            names = [c[0] for c in cursor.description or []]
            for row in cursor.fetchall():
                if names[:2] == ["status", "refusal"]:
                    registered = row[0] == "registered" and row[1] is None
                elif names[:2] == ["kind", "stated"]:
                    reconciles = reconciles and row[1] == row[2] == report.get(row[0], (0,))[0]
                else:
                    r = dict(zip(names, row))
                    report[r["kind"]] = (r["resolved"], r["added"], r["conflicts"], r["resolved"] - r["added"] - r["conflicts"])
        self.db.execute("COMMIT")
        return report, reconciles, registered

    def discard(self, run):
        self.db.execute("BEGIN")
        for name in ("discard_run", "discard_run_steps", "discard_run_counts", "discard_run_row"):
            self.db.execute(INGEST[name], (run,))
        self.db.execute("COMMIT")

    def merge(self, run, apply=True):
        """As a D1 batch: every statement or none. False when the batch was undone.
        Before it, the report without applying is taken, and afterwards held to the merge's."""
        counted, reconciles, registered = self.preview(run)
        ok = self._merge(run, apply)
        if registered and apply:
            if ok:
                same = counted == self.report(run)
                previews["same"] += same
                if not same:
                    previews["differ"].append((run, counted, self.report(run)))
            elif "reconciled" in self.last_error:
                previews["not reconciling seen" if not reconciles else "not reconciling missed"] += 1 if not reconciles else [run]
        return ok

    def _merge(self, run, apply=True):
        self.db.execute("BEGIN")
        try:
            for sql in MERGE:
                self.db.execute(sql, (run,) if "?1" in sql else ())
            self.db.execute("COMMIT" if apply else "ROLLBACK")
            return True
        except sqlite3.Error as error:
            self.db.execute("ROLLBACK")
            self.last_error = str(error)
            return False

    def run(self, records, **kw):
        self.runs += 1
        name = kw.pop("name", f"r{self.runs}")
        self.stage(name, records, **kw)
        return self.merge(name), name

    def report(self, run):
        return {kind: (resolved, added, conflicts, matched) for _, _, _, kind, resolved, added, conflicts, matched
                in self.all(INGEST["report"], run) if kind}

    def dump(self):
        return [self.all(sql) for sql in (
            "SELECT slug, review_state, reviewed_by, archived_at IS NOT NULL, awaiting_audit_at IS NOT NULL FROM claim ORDER BY 1",
            "SELECT c.slug, a.url_key FROM source_article a JOIN claim c ON c.id = a.claim_id ORDER BY 1, 2",
            "SELECT c.slug, e.dedupe_key, e.content_sha256, e.review_state FROM evidence_event e JOIN claim c ON c.id = e.claim_id ORDER BY 1, 2",
            "SELECT e.name, m.external_id, m.review_state, m.reviewed_by FROM entity_match m JOIN entity e ON e.id = m.entity_id ORDER BY 1, 2",
            "SELECT url_key, triage_score, triage_version, read_outcome FROM link_lead ORDER BY 1",
            "SELECT registry_name, external_id, overall_status, payload_sha256 FROM registry_trial ORDER BY 1, 2")]


# ---- records, in the natural-key form a writer hands over -------------------------------

SLUG = "semaglutide-obesity"
T = "2026-11-01T00:00:00Z"


def sha(n):
    return f"{n:064x}"


def payload(n, body=None):
    b = {"sha256": sha(n), "bytes": 700}
    b.update({"body": json.dumps(body)} if body else {"r2_key": f"payload/{sha(n)}"})
    return ("payload", sha(n), b)


def claim(slug=SLUG, state="approved", by="rule", held=T, origin="backfill", **more):
    body = {"slug": slug, "headline": f"Report on {slug}", "summary": "s", "vertical": "metabolic",
            "indication": slug.split("-")[-1], "origin": origin, "created_at": T, "awaiting_audit_at": held}
    if state != "pending":
        body.update(review_state=state, reviewed_by=by, reviewed_at=more.pop("reviewed_at", T))
    body.update(more)
    return ("claim", slug, body)


def article(key, slug=SLUG, date="2026-10-01"):
    return ("source_article", f"{slug}|{key}", {"slug": slug, "url_key": key, "url": f"https://{key}",
            "outlet": key.split("/")[0], "title": "t", "published_date": date})


def entity(name="semaglutide", slug=SLUG):
    return ("entity", f"{slug}|intervention|{name}", {"slug": slug, "type": "intervention", "name": name,
            "synonyms": ["Wegovy"]})


def match(trial, state, by, score=0.9, name="semaglutide", slug=SLUG, at=T):
    return ("entity_match", f"{slug}|{name}|{trial}", {"slug": slug, "entity_type": "intervention",
            "entity_name": name, "source_name": "clinicaltrials.gov", "external_id": trial, "score": score,
            "review_state": state, "reviewed_by": by, "reviewed_at": at, "created_at": T})


def event(trial="NCT1", content="c1", pay=1, fetched="2026-11-01T00:00:00Z", state="approved", by="rule", slug=SLUG):
    key = f"clinicaltrials.gov|{trial}|trial_registered|"
    body = {"slug": slug, "dedupe_key": key, "type": "trial_registered", "event_date": "2020-01-01",
            "source_name": "clinicaltrials.gov", "source_url": f"https://clinicaltrials.gov/study/{trial}",
            "external_id": trial, "summary": "registered", "confidence": 1, "content_sha256": content,
            "payload_sha256": sha(pay), "fetched_at": fetched, "created_at": T}
    if state != "pending":
        body.update(review_state=state, reviewed_by=by, reviewed_at=T)
    return ("evidence_event", f"{slug}|{key}", body)


def trial(number="NCT1", status="RECRUITING", pay=10, fetched="2026-11-01T00:00:00Z", title="Semaglutide in obesity"):
    return ("registry_trial", f"clinicaltrials.gov|{number}", {"registry_name": "clinicaltrials.gov",
            "external_id": number, "title": title, "conditions": ["Obesity"],
            "interventions": [{"type": "DRUG", "name": "Semaglutide"}], "intervention_names": "Semaglutide",
            "phases": ["PHASE3"], "overall_status": status, "payload_sha256": sha(pay), "fetched_at": fetched})


def lead(key="bbc.com/a", score=0.8, version=3, origin="file", shared="2026-10-01T09:00:00Z", **more):
    body = {"url_key": key, "url_key_version": 2, "url": f"https://{key}", "outlet": key.split("/")[0],
            "outlet_kind": "general_news", "title": "New obesity drug shows promise", "first_shared_at": shared,
            "origin": origin, "screen_outcome": "in_scope"}
    if score is not None:
        body.update(triage_score=score, triage_version=version)
    body.update(more)
    return ("link_lead", key, body)


def share(key="bbc.com/a", platform="hackernews", at="2026-10-01T09:00:00Z", score=12):
    community = "reader" if platform == "reader" else platform
    return ("link_share", f"{key}|{platform}|{at}", {"lead_url_key": key, "platform": platform,
            "community": community, "shared_at": at, "score": score})


def action(kind, slug=SLUG, by="human", **more):
    return ("action", f"{kind}|{slug}", {"action": kind, "slug": slug, "decided_by": by, "at": "2026-11-16T12:00:00Z", **more})


# ---- scenarios ---------------------------------------------------------------------------

results = []


def check(name, ok):
    results.append((name, bool(ok)))


def base():
    """A store holding one held claim with an article, an entity, an approved event."""
    s = Store()
    ok, run = s.run([payload(1), claim(), article("bbc.com/a"), entity(), event()])
    assert ok, s.last_error
    return s, run


def scenarios():
    # -- the spike's fourteen, on the designed schema --
    s, r1 = base()
    check("1 claim absent: added with its records", s.one("SELECT count(*) FROM claim") == 1
          and s.one("SELECT count(*) FROM source_article") == 1 and s.one("SELECT count(*) FROM evidence_event") == 1)
    check("2 audit mark carried on a new claim", s.one("SELECT awaiting_audit_at FROM claim") == T)
    check("3 report reconciles", s.report(r1) == {"payload": (1, 1, 0, 0), "claim": (1, 1, 0, 0),
          "source_article": (1, 1, 0, 0), "entity": (1, 1, 0, 0), "evidence_event": (1, 1, 0, 0)})
    before = s.dump()
    check("4 same run twice: nothing changes, first time reported", s.merge(r1) and s.dump() == before
          and s.one("SELECT status FROM run WHERE id = ?", r1) == "merged" and s.one("SELECT count(*) FROM stg") == 0)
    ok, r2 = s.run([article("reuters.com/b"), article("bbc.com/a")])
    check("5 claim present: new article added, known one matched", ok and s.report(r2)["source_article"] == (2, 1, 0, 1))

    s.run([action("audit_clear"), action("archive", reason="not one treatment")], writer="operator")
    s.db.execute("UPDATE claim SET review_state = 'rejected', reviewed_by = 'human'")
    ok, _ = s.run([claim(held=None), article("stat.com/c")])
    check("6 archived stays archived, a person's decision kept, article stored", ok and s.all(
          "SELECT archived_at IS NOT NULL, review_state, reviewed_by FROM claim") == [(1, "rejected", "human")]
          and s.one("SELECT count(*) FROM source_article") == 3)
    check("7 a merge never clears the audit mark", s.one("SELECT awaiting_audit_at FROM claim") is None)
    s.run([claim()])
    check("8 audit mark carried onto a claim already held", s.one("SELECT awaiting_audit_at FROM claim") == T)

    s, _ = base()
    s.run([match("NCT9", "rejected", "human", 0.4)])
    s.run([match("NCT9", "approved", "rule", 0.97, at="2026-12-01T00:00:00Z"), match("NCT8", "approved", "rule", 0.99)])
    check("9 a person's rejection of a match stands; a new match is added", s.all(
          "SELECT review_state, reviewed_by FROM entity_match WHERE external_id = 'NCT9'") == [("rejected", "human")]
          and s.one("SELECT count(*) FROM entity_match") == 2)
    s.run([match("NCT8", "rejected", "human")])
    check("10 a person's decision replaces a rule's", s.all(
          "SELECT review_state, reviewed_by FROM entity_match WHERE external_id = 'NCT8'") == [("rejected", "human")])

    s, _ = base()
    s.run([action("audit_clear")], writer="operator")
    ok, r = s.run([payload(2), event(content="c2", pay=2, fetched="2026-11-10T00:00:00Z")], writer="daily")
    check("11 differing evidence: stored kept, new kept apart with reason, claim held, one conflict", ok
          and s.one("SELECT content_sha256 FROM evidence_event") == "c1"
          and s.all("SELECT content_sha256, reason, state FROM evidence_conflict") == [("c2", "differs from the approved event stored", "open")]
          and s.one("SELECT awaiting_audit_at FROM claim") is not None and s.report(r)["evidence_event"] == (1, 0, 1, 0))
    before = s.dump()
    ok, old = s.run([claim("x-y")], steps={"link_triage": 2})
    check("12 older step version: refused, naming the step, nothing stored", ok and s.dump() == before
          and s.all("SELECT status, refusal FROM run WHERE id = ?", old) == [("refused", "step link_triage is at version 2, the store accepts 3")])
    ok, short = s.run([claim("x-y"), article("a.com/1", "x-y")], stated={"claim": 1, "source_article": 2})
    check("13 counts that do not reconcile: batch undone", not ok and s.dump() == before
          and s.one("SELECT status FROM run WHERE id = ?", short) == "registered")

    def two(order):
        d, _ = base()
        runs = {"a": [article("ft.com/z"), article("nyt.com/q")], "b": [article("ft.com/z"), article("sky.com/k")]}
        for name in order:
            d.run(runs[name])
        return d.dump()
    check("14 two runs on one claim: same store in either order", two("ab") == two("ba") and len(two("ab")[1]) == 4)

    # -- what the spec asks beyond the spike --
    s, _ = base()
    before = s.dump()
    ok, r = s.run([article("a.com/1", "no-such-claim")])
    check("15 a record whose claim the store lacks: batch undone", not ok and s.dump() == before)
    s.db.execute("DELETE FROM stg")
    ok, r = s.run([event("NCT5", pay=404)])
    check("16 an event whose payload was never handed over: batch undone", not ok and s.dump() == before)
    s.db.execute("DELETE FROM stg")
    rows = lambda: [s.one(f"SELECT count(*) FROM {t}") for t in ("run", "run_step", "run_stated", "stg", "merging", "merge_report", "source_article")]
    untouched = rows()
    s.stage("dry", [article("dry.com/1"), article("bbc.com/a")])
    counted, reconciles, _ = s.preview("dry")
    check("17 report without applying: counted, not tried; one would be added and one matched",
          counted == {"source_article": (2, 1, 0, 1)} and reconciles and s.dump() == before)
    s.discard("dry")
    check("17b after it the run is dropped and the store is as it was", rows() == untouched
          and s.one("SELECT count(*) FROM run WHERE id = 'dry'") == 0)
    try:
        s.stage("dry", [])
        s.db.execute(INGEST["stage"], ("dry", json.dumps([{"kind": "claim", "key": "", "body": {}}])))
        keyless = False
    except sqlite3.IntegrityError:
        keyless = True
    check("18 a record without its natural key is refused at the door", keyless)
    s.db.execute(INGEST["stage"], ("nobody", json.dumps([{"kind": "claim", "key": "k", "body": {}}])))
    check("19 records for a run never registered are not stored", s.one("SELECT count(*) FROM stg WHERE run_id = 'nobody'") == 0)

    # -- evidence: a refetch that says the same is not a conflict --
    s, _ = base()
    s.run([action("audit_clear")], writer="operator")
    ok, r = s.run([payload(3), event(content="c1", pay=3, fetched="2026-11-12T00:00:00Z")], writer="daily")
    check("20 a later fetch that says the same: no conflict, no hold, newest payload kept", ok
          and s.one("SELECT count(*) FROM evidence_conflict") == 0 and s.one("SELECT awaiting_audit_at FROM claim") is None
          and s.one("SELECT payload_sha256 FROM evidence_event") == sha(3) and s.report(r)["evidence_event"] == (1, 0, 0, 1))
    s.run([payload(4), event(content="c9", pay=4, fetched="2026-11-13T00:00:00Z")], writer="daily")
    s.run([payload(4), event(content="c9", pay=4, fetched="2026-11-13T00:00:00Z")], writer="device")
    check("21 the same difference from two runs is kept apart once", s.one("SELECT count(*) FROM evidence_conflict") == 1)
    ok, _ = s.run([action("audit_clear")], writer="operator")
    check("22 a claim is not cleared while its evidence is still kept apart", ok and s.one("SELECT awaiting_audit_at FROM claim") is not None)
    s.run([action("conflict_accept", dedupe_key="clinicaltrials.gov|NCT1|trial_registered|", content_sha256="c9")], writer="operator")
    s.run([("action", "clear2", action("audit_clear")[2])], writer="operator")
    check("23 accepted evidence replaces the stored event, and the claim can then be cleared", s.all(
          "SELECT content_sha256, review_state, reviewed_by FROM evidence_event") == [("c9", "approved", "human")]
          and s.one("SELECT state FROM evidence_conflict") == "accepted" and s.one("SELECT awaiting_audit_at FROM claim") is None)
    s2, _ = base()
    s2.run([payload(5), event("NCT7", "p1", 5, state="pending")])
    s2.run([payload(6), event("NCT7", "p2", 6, fetched="2026-11-20T00:00:00Z")])
    check("24 a pending event is replaced by a later fetch and takes its decision", s2.all(
          "SELECT content_sha256, review_state FROM evidence_event WHERE external_id = 'NCT7'") == [("p2", "approved")])

    # -- trials: the load and what a trial page reads --
    s = Store()
    ok, r = s.run([payload(10, {"nctId": "NCT1"}), trial()], writer="daily")
    check("25 a trial absent: added with its payload and first state", ok and s.report(r)["registry_trial"] == (1, 1, 0, 0)
          and s.all("SELECT overall_status FROM registry_trial_status") == [("RECRUITING",)])
    ok, r = s.run([trial(fetched="2026-11-05T00:00:00Z")], writer="daily")
    check("26 a trial fetched again unchanged: matched, checked time moves, payload time does not", ok
          and s.report(r)["registry_trial"] == (1, 0, 0, 1)
          and s.all("SELECT fetched_at, checked_at FROM registry_trial") == [("2026-11-01T00:00:00Z", "2026-11-05T00:00:00Z")])
    s.run([payload(11, {"nctId": "NCT1", "v": 2}), trial(status="COMPLETED", pay=11, fetched="2026-11-09T00:00:00Z")], writer="daily")
    check("27 a trial that changed: replaced whole, and its history has both states", s.one("SELECT overall_status FROM registry_trial") == "COMPLETED"
          and [x[0] for x in s.all("SELECT overall_status FROM registry_trial_status ORDER BY seen_at")] == ["RECRUITING", "COMPLETED"])
    s.run([payload(12, {"old": 1}), trial(status="RECRUITING", pay=12, fetched="2026-10-01T00:00:00Z")], writer="device")
    check("28 an older fetch never replaces a newer record", s.one("SELECT overall_status FROM registry_trial") == "COMPLETED")
    check("29 trial search finds it by condition and by intervention", s.one(
          "SELECT count(*) FROM registry_trial_fts WHERE registry_trial_fts MATCH 'obesity'") == 1
          and s.one("SELECT t.external_id FROM registry_trial_fts f JOIN registry_trial t ON t.id = f.rowid WHERE registry_trial_fts MATCH 'intervention_names:semaglutide'") == "NCT1")
    page = s.all("""SELECT t.title, t.overall_status, p.body IS NOT NULL FROM registry_trial t
                    JOIN payload p ON p.sha256 = t.payload_sha256 WHERE t.registry_name = ? AND t.external_id = ?""",
                 "clinicaltrials.gov", "NCT1")
    check("30 a plain trial page is one keyed read, payload included", page == [("Semaglutide in obesity", "COMPLETED", 1)])

    # -- leads, and what a reader's lookup leaves --
    s = Store()
    s.run([lead(), share()])
    s.run([lead(score=0.2, version=2)])
    s.run([lead(score=0.9, version=4, read_outcome="cannot_be_read")], steps={"link_triage": 4})
    check("32 a lead's score is taken only from a higher triage version; a read outcome once", s.all(
          "SELECT triage_score, triage_version, read_outcome FROM link_lead") == [(0.9, 4, "cannot_be_read")])
    ok, look = s.run([lead("stat.com/new", score=None, origin="reader", shared="2026-11-16"),
                      share("stat.com/new", "reader", "2026-11-16", 0), payload(20, {"nctId": "NCT20"}), trial("NCT20", pay=20),
                      ("lead_reading", "stat.com/new", {"lead_url_key": "stat.com/new", "intervention": "retatrutide",
                       "indication": "obesity", "confidence": 0.8, "read_version": 1, "read_on": "2026-11-16",
                       "trials": [{"registry": "clinicaltrials.gov", "trial_id": "NCT20", "score": 0.7}]})],
                     writer="lookup", at="2026-11-16T14:23:11Z")
    check("33 a lookup leaves a lead, a reader share, the trial and a reading; no claim, event or match", ok
          and s.one("SELECT count(*) FROM link_lead WHERE origin = 'reader'") == 1 and s.one("SELECT count(*) FROM lead_reading") == 1
          and s.one("SELECT count(*) FROM registry_trial") == 1
          and s.one("SELECT (SELECT count(*) FROM claim) + (SELECT count(*) FROM evidence_event) + (SELECT count(*) FROM entity_match)") == 0)
    s.run([lead("stat.com/new", score=None, origin="reader", shared="2026-11-16"), share("stat.com/new", "reader", "2026-11-16", 0)],
          writer="lookup", at="2026-11-16T19:00:00Z")
    check("34 the same article asked about twice in a day: one lead, one share", s.one(
          "SELECT count(*) FROM link_share WHERE platform = 'reader'") == 1)
    fine = s.all("""SELECT 1 FROM run WHERE writer = 'lookup' AND (length(registered_at) > 10 OR length(merged_at) > 10)
                    UNION ALL SELECT 1 FROM link_share WHERE platform = 'reader' AND length(shared_at) > 10
                    UNION ALL SELECT 1 FROM work_item WHERE record_key = 'stat.com/new' AND length(due_since) > 10""")
    check("35 nothing a lookup leaves holds a time finer than the day", fine == [])
    check("36 a reader's lead is due for processing once", s.all(
          "SELECT state, attempts FROM work_item WHERE step = 'lead_process'") == [("due", 0)])
    ok, _ = s.run([share("stat.com/new", "reader", "2026-11-17T08:01:02Z", 0)], writer="lookup", at="2026-11-17T08:01:02Z")
    check("37 a reader share with a time of day cannot be stored", not ok)
    s.db.execute("DELETE FROM stg")
    ok, _ = s.run([lead("blog.example/x", outlet_kind="unknown")])
    check("38 a lead on an unlisted outlet cannot be stored", not ok)
    s.db.execute("DELETE FROM stg")
    a = s.all(INGEST["lease_work"], "lead_process", 5, "2026-11-16T14:30:00Z", "2026-11-16T14:40:00Z")
    b = s.all(INGEST["lease_work"], "lead_process", 5, "2026-11-16T14:31:00Z", "2026-11-16T14:41:00Z")
    c = s.all(INGEST["lease_work"], "lead_process", 5, "2026-11-16T14:50:00Z", "2026-11-16T15:00:00Z")
    check("39 due work is leased to one consumer, and taken again when the lease lapses", len(a) == 1 and b == [] and len(c) == 1)
    for _ in range(2):
        s.db.execute(INGEST["fail_work"], ("link_lead", "stat.com/new", "lead_process", "reader_refused", 2))
    check("40 work that keeps failing is left with its error, not lost", s.all(
          "SELECT state, error FROM work_item WHERE step = 'lead_process'") == [("failed", "reader_refused")])

    # -- publication by rule: a reader's claim beside a backfill's --
    s = Store()
    s.run([claim("from-backfill"), claim("from-reader", held=None, origin="lookup")], writer="consumer")
    ok, _ = s.run([action("publish", "from-backfill", "rule"), action("publish", "from-reader", "rule")], writer="export")
    check("41 a reader's claim is published by rule; a backfill's waits for its audit", ok and s.all(
          "SELECT slug FROM claim_public") == [("from-reader",)])
    first = s.one("SELECT published_at FROM claim WHERE slug = 'from-reader'")
    s.run([("action", "again", {"action": "publish", "slug": "from-reader", "at": "2027-01-01T00:00:00Z"})], writer="export")
    check("42 a published time is never changed", s.one("SELECT published_at FROM claim WHERE slug = 'from-reader'") == first)
    listed = s.all("""SELECT c.slug FROM claim_action a JOIN claim c ON c.id = a.claim_id
                      WHERE a.action = 'publish' AND c.origin = 'lookup' AND substr(a.at, 1, 10) = '2026-11-16'""")
    check("43 claims published from readers' leads can be listed by day", listed == [("from-reader",)])

    # -- the operator: archive, unarchive, rename, merge --
    s, _ = base()
    s.run([action("audit_clear"), action("archive", reason="wrong trial")], writer="operator")
    ok, _ = s.run([action("unarchive", by="assistant")], writer="operator")
    check("44 only a person unarchives", not ok and s.one("SELECT archived_at FROM claim") is not None)
    s.db.execute("DELETE FROM stg")
    ok, _ = s.run([action("unarchive")], writer="operator")
    check("45 a person unarchives, and the action is on record", ok and s.one("SELECT archived_at FROM claim") is None
          and [x[0] for x in s.all("SELECT action FROM claim_action ORDER BY id")] == ["audit_clear", "archive", "unarchive"])

    ok, _ = s.run([action("rename", new_slug="semaglutide-weight")], writer="operator")
    ok2, _ = s.run([article("late.com/1")], writer="device")
    check("46 a renamed claim answers to both slugs: a device's late push still lands", ok and ok2
          and s.all("SELECT slug FROM claim") == [("semaglutide-weight",)] and s.one("SELECT count(*) FROM source_article") == 2)
    s.run([claim("other-claim", held=None)])
    ok, _ = s.run([action("rename", "other-claim", new_slug="semaglutide-weight")], writer="operator")
    check("47 a rename onto a slug another claim holds is undone", not ok and s.one("SELECT count(*) FROM claim WHERE slug = 'other-claim'") == 1)
    s.db.execute("DELETE FROM stg")

    s.run([article("dup.com/1", "other-claim", "2026-01-05"), article("late.com/1", "other-claim"), lead("dup.com/1", claim_slug="other-claim")])
    s.run([match("NCT1", "rejected", "human", name="semaglutide", slug="semaglutide-weight")])
    ok, _ = s.run([action("merge", "other-claim", into_slug="semaglutide-weight")], writer="operator")
    kept = s.one("SELECT id FROM claim WHERE slug = 'semaglutide-weight'")
    check("48 merged claim: archived, pointing at the one that stays", ok and s.all(
          "SELECT merged_into, archived_at IS NOT NULL, archive_reason FROM claim WHERE slug = 'other-claim'") == [(kept, 1, "merged into semaglutide-weight")])
    check("49 merged claim: its articles and leads move, a shared article is not doubled", s.one(
          "SELECT count(*) FROM source_article WHERE claim_id = ?", kept) == 3 and s.one("SELECT claim_id FROM link_lead WHERE url_key = 'dup.com/1'") == kept)
    check("50 merged claim: the kept claim's decisions stand, first report is the earlier, prepare is due", s.all(
          "SELECT review_state, reviewed_by FROM entity_match") == [("rejected", "human")]
          and s.one("SELECT first_reported_date FROM claim WHERE id = ?", kept) == "2026-01-05"
          and s.one("SELECT state FROM work_item WHERE record_key = 'semaglutide-weight' AND step = 'prepare'") == "due")
    ok, _ = s.run([article("after.com/1", "other-claim")], writer="device")
    check("51 records pushed for a merged claim go to the claim that stays", ok and s.one(
          "SELECT claim_id FROM source_article WHERE url_key = 'after.com/1'") == kept)
    check("52 claim search finds the claim by a synonym of its intervention", s.one(
          "SELECT c.slug FROM claim_fts f JOIN claim c ON c.id = f.rowid WHERE claim_fts MATCH 'wegovy'") == "semaglutide-weight")

    # -- spend by writer, slices, provenance --
    s = Store()
    use = lambda n, cost: ("usage", str(n), {"seq": n, "purpose": "triage", "model": "m", "input_tokens": 10, "output_tokens": 1, "cost_usd": cost, "created_at": "2026-11-16"})
    s.run([use(1, 1.5)], device="mini")
    s.run([use(1, 2.0)], device="macbook")
    s.run([use(1, 0.25)], writer="lookup")
    check("53 the month's spend is shown by device and by lookups", s.all(
          "SELECT who, cost_usd FROM spend_by_writer ORDER BY 1") == [("extension", 0.25), ("macbook", 2.0), ("mini", 1.5)])
    took = s.all(INGEST["take_slice"], "reddit", "science", "2026-03", "mini", "2026-11-16T10:00", "2026-11-17T10:00")
    lost = s.all(INGEST["take_slice"], "reddit", "science", "2026-03", "macbook", "2026-11-16T10:01", "2026-11-17T10:01")
    late = s.all(INGEST["take_slice"], "reddit", "science", "2026-03", "macbook", "2026-11-18T10:00", "2026-11-19T10:00")
    check("54 a slice is given to one device, and to another only when the taking lapsed", took == [("mini",)] and lost == [] and late == [("macbook",)])
    ok, _ = s.run([("work_slice", "reddit|science|2026-03", {"platform": "reddit", "community": "science", "month": "2026-03"})], device="mini")
    check("55 a slice never blocks a merge: done, and noted as not held", ok and s.all(
          "SELECT done_run IS NOT NULL, unheld FROM work_slice") == [(1, 1)])
    s, r1 = base()
    check("56 which records one run added is answered from the records alone", s.one(
          "SELECT count(*) FROM source_article a JOIN run r ON r.id = a.added_run WHERE r.device = 'mini' AND substr(r.registered_at, 1, 10) = '2026-11-16'") == 1)
    # -- what the pipeline's own merge and rename do (claims/corrections.py), mirrored --
    s, _ = base()
    ok, _ = s.run([action("rename", old_name="semaglutide", new_name="semaglutide injection")], writer="operator")
    check("59 a rename of the intervention: new name, old one kept as a synonym, same slug, registries due again", ok and s.all(
          "SELECT name, synonyms FROM entity") == [("semaglutide injection", '["Wegovy","semaglutide"]')]
          and s.all("SELECT slug FROM claim") == [(SLUG,)]
          and s.one("SELECT state FROM work_item WHERE record_key = ? AND step = 'prepare'", SLUG) == "due")
    ok, _ = s.run([entity("tirzepatide")])
    check("60 a claim has one intervention, never two", not ok and s.one("SELECT count(*) FROM entity") == 1)
    s.db.execute("DELETE FROM stg")
    company = lambda slug: ("entity", f"{slug}|company|Novo Nordisk", {"slug": slug, "type": "company", "name": "Novo Nordisk"})
    paper = ("entity", "dup|paper|STEP 1", {"slug": "dup", "type": "paper", "name": "STEP 1"})
    s.run([company(SLUG), claim("dup", held=None), entity("Ozempic", "dup"), company("dup"), paper, match("NCT4", "approved", "rule", name="Ozempic", slug="dup")])
    ok, _ = s.run([action("merge", "dup", into_slug=SLUG, gains=["Ozempic", "Wegovy"])], writer="operator")
    kept = s.one("SELECT id FROM claim WHERE slug = ?", SLUG)
    check("61 a merge moves what an article named and the names listed; a name both hold is not doubled", ok
          and s.one("SELECT synonyms FROM entity WHERE claim_id = ? AND type = 'intervention'", kept) == '["Wegovy","semaglutide","Ozempic"]'
          and s.one("SELECT claim_id FROM entity WHERE name = 'STEP 1'") == kept
          and s.one("SELECT count(*) FROM entity WHERE name = 'Novo Nordisk' AND claim_id = ?", kept) == 1)
    check("62 what a registry said does not move with a merge: the match stays with the claim that went", s.one(
          "SELECT c.slug FROM entity_match m JOIN entity e ON e.id = m.entity_id JOIN claim c ON c.id = e.claim_id WHERE m.external_id = 'NCT4'") == "dup")
    s.run([claim("dup2", held=None), entity("Zepbound", "dup2")])
    ok, _ = s.run([action("merge", "dup2", into_slug=SLUG, gains=["Zepbound", "Ozempic", "Alpha"])], writer="operator")
    check("63 a merge keeps the names in their order and adds the gained ones after them, unsorted", ok
          and s.one("SELECT synonyms FROM entity WHERE claim_id = ? AND type = 'intervention'", kept) == '["Wegovy","semaglutide","Ozempic","Zepbound","Alpha"]')

    check(f"57 the report without applying said what the merge then said, for every merge above ({previews['same']})",
          not previews["differ"] and not previews["not reconciling missed"] and previews["same"] >= 50)
    check(f"58 it also said so of every run whose counts did not reconcile ({previews['not reconciling seen']})",
          previews["not reconciling seen"] >= 2)
    return results


# ---- the sample, and sizes -----------------------------------------------------------------

ORDER = ["payload", "claim", "source_article", "promise", "reported_statement", "entity", "entity_match", "claim_term",
         "source_record", "entity_substance", "evidence_event", "trial_read", "registry_trial", "work_entry",
         "link_lead", "link_share", "usage", "decision", "action"]


def load_sample():
    OUT.mkdir(exist_ok=True)
    path = OUT / "store.db"
    path.unlink(missing_ok=True)
    s = Store(str(path))
    by_kind, full = {}, {}
    for line in SAMPLE.open(encoding="utf-8"):  # not splitlines: a title may hold a line separator
        if not line.startswith("{"):
            continue
        rec = json.loads(line)
        if rec["kind"] == "_full":
            full[rec["key"]] = rec["body"]["rows"]
        else:
            by_kind.setdefault(rec["kind"], []).append((rec["kind"], rec["key"], rec["body"]))
    records = [r for kind in ORDER for r in by_kind.get(kind, [])]
    print(f"\nSample: {len(records):,} records of {len(by_kind)} kinds")
    slowest, longest_body = 0.0, 0
    for i in range(0, len(records), 20000):       # a run a batch: parents come first, so each run is whole
        chunk = records[i:i + 20000]
        longest_body = max(longest_body, max(len(json.dumps(b)) for _, _, b in chunk))
        s.stage(f"migrate-{i // 20000}", chunk, writer="migration")
        started = time.time()
        merged = s.merge(f"migrate-{i // 20000}")
        if previews["differ"]:
            run, counted, said = previews["differ"][-1]
            print("  report without applying differed:", {k: (counted.get(k), said.get(k)) for k in set(counted) | set(said) if counted.get(k) != said.get(k)})
        if not merged:
            print("  merge undone:", s.last_error)
            for row in s.all("SELECT t.kind, t.records, (SELECT count(*) FROM stg WHERE run_id = t.run_id AND kind = t.kind) FROM run_stated t WHERE t.run_id = ?", f"migrate-{i // 20000}"):
                print("   stated", row)
            return None
        took = time.time() - started
        slowest = max(slowest, took)
        print(f"  run {i // 20000}: {len(chunk):,} records merged in {took:.2f} s")
    again = s.dump()
    s.db.execute("UPDATE run SET status = 'registered', merged_at = NULL WHERE id = 'migrate-0'")
    s.stage("migrate-again", records[:20000], writer="migration")
    s.merge("migrate-again")
    added = s.one("SELECT sum(added) FROM merge_report WHERE run_id = 'migrate-again'")
    print(f"  the first 20,000 pushed again as a new run: {added} added, store {'unchanged' if s.dump() == again else 'CHANGED'}")
    print(f"  the report without applying said what each of those merges then said: {'yes' if not previews['differ'] else 'NO'}")
    print("  held:", s.one("SELECT count(*) FROM claim WHERE awaiting_audit_at IS NOT NULL"), "archived:",
          s.one("SELECT count(*) FROM claim WHERE archived_at IS NOT NULL"), "public:", s.one("SELECT count(*) FROM claim_public"))
    s.db.execute("DELETE FROM merge_report")
    s.db.execute("VACUUM")
    sizes(s, full, path, slowest, longest_body)
    return s


GROUPS = {"registry_trial_fts": "registry_trial_fts", "link_lead_fts": "link_lead_fts", "claim_fts": "claim_fts"}


def sizes(s, full, path, slowest, longest_body):
    by_table = {}
    for name, pages in s.all("SELECT name, sum(pgsize) FROM dbstat GROUP BY name"):
        owner = s.one("SELECT tbl_name FROM sqlite_master WHERE name = ?", name) or name
        owner = next((g for prefix, g in GROUPS.items() if owner.startswith(prefix)), owner)
        by_table[owner] = by_table.get(owner, 0) + pages
    sample_rows = {t: s.one(f"SELECT count(*) FROM {t}") for t in by_table if not t.startswith("sqlite_")}
    inline = s.one("SELECT count(*) FROM payload WHERE body IS NOT NULL") or 1
    print(f"\nSizes: the sample is {path.stat().st_size / 1e6:.1f} MB as SQLite. Projected to the whole database:")
    print(f"  {'table':28}{'sample rows':>12}{'bytes a row':>13}{'full rows':>12}{'projected MB':>14}")
    total = 0
    for table, size in sorted(by_table.items(), key=lambda kv: -kv[1]):
        rows = sample_rows.get(table) or 0
        if not rows or table in ("stg", "run", "run_stated", "run_step", "merge_guard"):
            continue
        per = size / rows
        if table == "payload":
            whole = full.get("payload_inline", 0) + full.get("payload_r2", 0)
        else:
            whole = full.get(table)
        if whole is None:                         # no count asked for: scale with the claims
            whole = round(rows * full["claim"] / max(sample_rows["claim"], 1))
        projected = per * whole
        total += projected
        print(f"  {table:28}{rows:>12,}{per:>13,.0f}{whole:>12,}{projected / 1e6:>14,.1f}")
    largest = max(s.one(f"SELECT max(length(CAST({col} AS BLOB))) FROM {table}") or 0 for table, col in
                  [("payload", "body"), ("source_record", "body"), ("entity_match", "record_summary"),
                   ("registry_trial", "interventions"), ("decision_log", "output"), ("evidence_conflict", "event")])
    statement = max(len(sql.encode()) for sql in MERGE + list(INGEST.values()))
    params = max(sql.count("?") for sql in MERGE + list(INGEST.values()))
    print(f"\n  projected database: {total / 1e9:.2f} GB of D1's {D1_DATABASE_BYTES / 1e9:.0f} GB ({100 * total / D1_DATABASE_BYTES:.0f}%)")
    print(f"  payloads in R2: {full.get('payload_r2', 0):,} objects, {full.get('payload_r2_bytes', 0) / 1e6:,.0f} MB; kept in rows: {full.get('payload_inline', 0):,}")
    print(f"  largest value in a row: {largest:,} bytes of {D1_ROW_BYTES:,}; largest trial payload in Postgres: {full.get('largest_trial_payload', 0):,}")
    print(f"  longest statement: {statement:,} bytes of {D1_STATEMENT_BYTES:,}; most bound parameters: {params} of {D1_BOUND_PARAMETERS}")
    print(f"  largest staged record: {longest_body:,} bytes; a staging chunk is one string of at most {D1_ROW_BYTES:,}")
    print(f"  slowest merge of 20,000 records here: {slowest:.2f} s of D1's {D1_QUERY_SECONDS} s a batch (local disk, not D1)")
    print(f"  statements in the merge: {len(MERGE)}; Postgres today: {full.get('postgres_bytes', 0) / 1e6:,.0f} MB")


if __name__ == "__main__":
    done = scenarios()
    for name, ok in done:
        print("PASS" if ok else "FAIL", name)
    print(f"{sum(ok for _, ok in done)} of {len(done)} scenarios pass | statements in the merge: {len(MERGE)}")
    failed = [name for name, ok in done if not ok]
    if "--scenarios" not in sys.argv:
        if SAMPLE.exists():
            failed += [] if load_sample() else ["sample load"]
        else:
            print(f"\nNo sample at {SAMPLE}: run the export in store/README.md to load one and project sizes.")
    sys.exit(1 if failed else 0)
