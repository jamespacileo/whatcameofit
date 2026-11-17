from thenwhat.resolve.study_enrollment import agrees_with_total, reported_total


def test_explicit_enrollment_can_distinguish_sibling_protocols():
    assert (
        reported_total(["The researchers obtained measurements for each of the 1,100 patients."])
        == 1100
    )
    assert agrees_with_total(1100, 1089)
    assert not agrees_with_total(1100, 267)


def test_rejects_subset_and_inconsistent_totals():
    assert (
        reported_total(["The team analyzed each of the 250 participants in this cohort."]) is None
    )
    assert reported_total(["There were adverse events in 10 of 100 patients."]) is None
    assert (
        reported_total(["The trial enrolled 150 patients.", "A total of 125 participants."]) is None
    )
