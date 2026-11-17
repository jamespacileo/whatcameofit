"""Yearly MeSH refresh and paper headings through the writer and bulk-store export."""

import pytest
from sqlalchemy.orm import Session

from store_support import assert_same_export
from test_clinical_service import NOW, TREE, FakeMesh, new_claim, with_trial
from test_export import add_origin_paper, index_record, store_paper
from thenwhat.clinical.service import read_tree
from thenwhat.sources.base import SourceError
from thenwhat.sources.mesh import Mesh, UnexpectedAnswer


class YearlyMesh(FakeMesh):
    vocabulary_year = str(NOW.year)
    unavailable = False

    def descriptor_labelled(self, label):
        if self.unavailable:
            raise SourceError("The source is temporarily unavailable.")
        return super().descriptor_labelled(label)

    def term(self, identifier, *, force=False):
        record = super().term(identifier, force=force)
        if record is None or self.vocabulary_year == str(NOW.year):
            return record
        if identifier == "D012878":
            return None
        term = record.payload["term"]
        for key in ("@id", "treeNumber", "broaderDescriptor"):
            if key in term:
                term[key] = term[key].replace(str(NOW.year), self.vocabulary_year)
        if identifier == "D011565":
            term["treeNumber"] = term["treeNumber"].replace("859.675", "859.999")
        return record


def test_missing_heading_survives_a_restart_and_expires_in_a_new_year(
    session, tmp_path, fixture_json
):
    claim = new_claim(session, "negative-heading")
    with_trial(session, claim, "NCT00000001", "D011565")
    paper = index_record(fixture_json)
    paper["meshHeadingList"] = {
        "meshHeading": [{"descriptorName": "Unknown", "majorTopic_YN": "Y"}]
    }
    store_paper(session, paper)
    add_origin_paper(session, paper["doi"], claim.slug)
    source = YearlyMesh()

    def export_at(name, now):
        folder = tmp_path / name
        folder.mkdir()
        with Session(session.get_bind(), join_transaction_mode="create_savepoint") as reopened:
            return assert_same_export(reopened, folder, now)["claims"][0]["clinical_categories"]

    source.unavailable = True
    with pytest.raises(SourceError):
        read_tree(session, source, [claim], mapping={})
    assert export_at("unavailable", NOW) is None

    source.unavailable = False
    first = read_tree(session, source, [claim], mapping={})
    assert first.unknown_headings == ["Unknown"]
    assert [c["identifier"] for c in export_at("resolved", NOW)] == ["D011565"]
    source.asked.clear()
    read_tree(session, source, [claim], mapping={})
    assert source.asked == []

    later = NOW.replace(year=NOW.year + 1)
    source.vocabulary_year = str(later.year)
    source.unavailable = True
    with pytest.raises(SourceError):
        read_tree(session, source, [claim], mapping={})
    assert export_at("new-year-pending", later) is None
    source.unavailable = False
    read_tree(session, source, [claim], mapping={})
    assert [c["identifier"] for c in export_at("new-year-rechecked", later)] == ["D011565"]


def test_yearly_refresh_replaces_placements_and_identifies_retired_records(session, tmp_path):
    claim = new_claim(session, "new-mesh-year")
    with_trial(session, claim, "NCT00000001", "D011565", "D012878")
    source = YearlyMesh()
    read_tree(session, source, [claim], mapping={})
    assert set(source.asked) == set(TREE)
    source.asked.clear()
    later = NOW.replace(year=NOW.year + 1)
    source.vocabulary_year = str(later.year)
    report = read_tree(session, source, [claim], mapping={})
    assert report.retired_years == {"D012878": str(NOW.year)}
    assert set(source.asked) == set(TREE)
    assert len(source.asked) == len(TREE)
    source.asked.clear()
    again = read_tree(session, source, [claim], mapping={})
    assert again.retired_years == report.retired_years
    assert not source.asked

    exported = assert_same_export(session, tmp_path, later)
    nodes = {node["identifier"]: node for node in exported["clinical"]["nodes"]}
    assert nodes["D011565"]["tree_numbers"] == ["C17.800.859.999"]
    assert nodes["D012878"]["tree_numbers"] == [TREE["D012878"][1]]
    assert exported["clinical"]["mesh_years"] == [str(NOW.year), str(later.year)]


@pytest.mark.parametrize("response", [None, {}, "unavailable", [{}], ["bad row"]])
def test_a_malformed_lookup_response_cannot_become_a_negative(
    session, fake_time, monkeypatch, response
):
    from thenwhat.sources.base import Fetched

    mesh = Mesh(session, time=fake_time, contact_email="test@example.test")
    answer = None if response is None else Fetched(response, fake_time.now())
    monkeypatch.setattr(mesh, "_get", lambda *args, **kwargs: answer)
    with pytest.raises(UnexpectedAnswer):
        mesh.descriptor_labelled("Unknown")
