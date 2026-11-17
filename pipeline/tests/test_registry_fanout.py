import sqlite3
from contextlib import closing

from thenwhat.resolve.registry_fanout import TrialHit, trial_fanout
from thenwhat.resolve.registry_study_names import NamedTrial, cited_study_names


def test_ranked_fanout_recovers_registered_aliases_and_protocol_titles():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript("""
            CREATE TABLE registry_trial (
                id INTEGER PRIMARY KEY, external_id TEXT, title TEXT, conditions TEXT,
                intervention_names TEXT, acronym TEXT, phases TEXT, overall_status TEXT,
                lead_sponsor_name TEXT, search_name TEXT
            );
            CREATE VIRTUAL TABLE registry_trial_fts USING fts5 (
                title, conditions, intervention_names,
                content = 'registry_trial', content_rowid = 'id'
            );
            INSERT INTO registry_trial VALUES
                (1, 'NCT00000001', 'AB 2101 for chronic lung disease',
                 '["Interstitial lung disease"]', 'AB 2101', NULL, '["PHASE3"]',
                 'COMPLETED', 'Example Research Labs, Inc.', 'examplemab'),
                (2, 'NCT00000002', 'Chronic lung function response in clinical care',
                 '["Interstitial lung disease"]', 'Placebo', NULL, '["NA"]',
                 'COMPLETED', 'Example Research Labs, Inc.', NULL),
                (3, 'NCT00000003', 'Adaptive Lung Response Protocol',
                 '["Interstitial lung disease"]', 'CD 9120', NULL, '["PHASE3"]',
                 'COMPLETED', 'Old Sponsor, Inc.', NULL);
            INSERT INTO registry_trial_fts(registry_trial_fts) VALUES ('rebuild');
            """)
        by_alias = trial_fanout(
            db,
            "Phase 3 Examplemab",
            indication="interstitial lung disease",
            interventions=["Examplemab (new brand)"],
        )
        by_title = trial_fanout(
            db,
            "Adaptive Lung Response Protocol CD 9120",
            indication="interstitial lung disease",
            sponsor="New Sponsor",
        )
        by_sponsor = trial_fanout(
            db,
            "Phase 3 treatment outcome",
            indication="interstitial lung disease",
            sponsor="Example Research Ltd.",
        )

    assert TrialHit("NCT00000001", "registered_product") in by_alias
    assert by_title[0] == TrialHit("NCT00000003", "title_phrase")
    assert by_sponsor[0] == TrialHit("NCT00000001", "sponsor_context")


def test_study_name_lookup_preserves_a_multiword_label_with_normalized_separators():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript("""
            CREATE TABLE registry_trial (
                external_id TEXT, acronym TEXT, conditions TEXT, intervention_names TEXT
            );
            INSERT INTO registry_trial VALUES
                ('NCT00000001', ' BRIGHT ‐ STAR ', '["Interstitial lung disease"]', 'EXQ; PBO'),
                ('NCT00000002', 'BRIGHT STAR EXTENSION',
                 '["Interstitial lung disease"]', 'Examplemab');
            """)
        for context in ("on EXQ", "for people with ILD"):
            found = cited_study_names(db, f"The Bright Star trial reported outcomes {context}.")
            assert found == [NamedTrial("NCT00000001", " BRIGHT ‐ STAR ")]
        assert cited_study_names(db, "The Bright Star trial enrolled people on PBO.") == []


def test_small_sponsor_phase_fanout_keeps_an_older_product_code_and_umbrella_condition():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript("""
            CREATE TABLE registry_trial (
                id INTEGER PRIMARY KEY, external_id TEXT, title TEXT, conditions TEXT,
                intervention_names TEXT, acronym TEXT, phases TEXT, overall_status TEXT,
                lead_sponsor_name TEXT, search_name TEXT
            );
            CREATE VIRTUAL TABLE registry_trial_fts USING fts5 (
                title, conditions, intervention_names,
                content = 'registry_trial', content_rowid = 'id'
            );
            INSERT INTO registry_trial VALUES
                (1, 'NCT00000011', 'A Study of EX-204 in Solid Tumors',
                 '["Solid Tumor"]', 'EX-204', NULL, '["PHASE1"]',
                 'RECRUITING', 'Example Oncology Inc.', 'ex-204'),
                (2, 'NCT00000022', 'A Study of EX-505 in Solid Tumors',
                 '["Solid Tumor"]', 'EX-505', NULL, '["PHASE3"]',
                 'RECRUITING', 'Example Oncology Inc.', 'ex-505');
            INSERT INTO registry_trial_fts(registry_trial_fts) VALUES ('rebuild');
            """)
        found = trial_fanout(
            db,
            "Phase 1 Neoplasmab recurrent squamous carcinoma",
            indication="recurrent squamous carcinoma",
            sponsor="Example Oncology",
            interventions=["Neoplasmab"],
        )
    assert found == [TrialHit("NCT00000011", "sponsor_phase")]
