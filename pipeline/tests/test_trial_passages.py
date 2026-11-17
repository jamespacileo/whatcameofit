from thenwhat.resolve.trial_passages import reported_passage


def test_a_complete_multiword_name_prefers_reported_results():
    ongoing = "The ACTIVE TRACK extension study is still enrolling and will present its findings."
    results = "The ACTIVE TRACK trial demonstrated a decrease in the primary outcome."
    passage = reported_passage(
        f"{ongoing}\n{results}",
        "NCT00001111",
        labels=("ACTIVE TRACK",),
        products=(),
    )

    assert passage is not None
    assert results in passage.text
    assert passage.possible_code is None


def test_a_short_sponsor_code_is_a_hint_for_the_same_result():
    passage = reported_passage(
        "Example's AX ‘408 trial demonstrated a change in the prespecified endpoint.",
        "NCT00001111",
        labels=(),
        products=("AX-53408",),
    )

    assert passage is not None
    assert passage.possible_code == "AX ‘408 is consistent with a shortened AX-53408"


def test_a_lay_description_of_a_trial_goal_can_ground_a_candidate():
    passage = reported_passage(
        "Researchers reported on examplemab in a mid-stage trial. The treatment met its main goal.",
        "NCT00001111",
        labels=(),
        products=("examplemab",),
    )

    assert passage is not None
    assert "met its main goal" in passage.text


def test_an_identifiable_product_in_a_reported_result_can_supply_evidence():
    passage = reported_passage(
        "Examplemab met all primary and secondary efficacy endpoints.",
        "NCT00001111",
        labels=(),
        products=("examplemab",),
    )

    assert passage is not None
    assert passage.names_protocol is False


def test_another_trials_findings_do_not_belong_to_the_background_trial():
    article = (
        "The STAR TRACK trial of examplemab is enrolling. "
        "The ACTIVE TRACK trial showed improved outcomes with examplemab."
    )

    assert (
        reported_passage(
            article,
            "NCT00001111",
            labels=("STAR TRACK",),
            products=("examplemab",),
            other_labels=("ACTIVE TRACK",),
        )
        is None
    )


def test_an_observed_result_survives_a_future_clause_and_wins_over_a_phase_mention():
    result = "ACTIVE TRACK met its primary endpoint, and the next phase will present results later."
    article = (
        "The ACTIVE TRACK trial (NCT00001111) is ongoing. "
        "Participants showed sustained improvement. "
        f"{result}"
    )

    passage = reported_passage(article, "NCT00001111", labels=("ACTIVE TRACK",), products=())

    assert passage is not None
    assert passage.text == result
    assert passage.names_protocol


def test_reported_findings_can_be_expressed_in_a_subheading():
    passage = reported_passage(
        "ACTIVE TRACK trial: Six patients, four remissions.\n"
        "The ACTIVE TRACK extension will present its results next year.",
        "NCT00001111",
        labels=("ACTIVE TRACK",),
        products=(),
    )

    assert passage is not None
    assert passage.text == "ACTIVE TRACK trial: Six patients, four remissions."


def test_a_named_result_after_flattened_navigation_beats_a_condition_acronym():
    result = (
        "Researchers reported initial findings from the ACTIVE TRACK study in patients with ASTHMA."
    )
    article = "ACTIVE TRACK in the news " + ("navigation menu " * 90) + result
    passage = reported_passage(
        article,
        "NCT00001111",
        labels=("ACTIVE TRACK",),
        products=(),
        other_labels=("ASTHMA",),
    )

    assert passage is not None
    assert result in passage.text
    assert passage.names_protocol
