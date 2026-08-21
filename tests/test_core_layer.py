"""Tests for core_layer: BifurcationMap, CoreLayer, DialetheiaEntry, ObservabilityReport."""

from katala_match.core import (
    AttractorNode,
    BifurcationMap,
    BifurcationPoint,
    CoreLayer,
    CorePole,
    CreativityMode,
    DialetheiaEntry,
    ObservabilityReport,
    PhiEdge,
    PersonModel,
    build_core_layer,
    promotion_decision,
    rebuild_core,
    score_candidate_with_core,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_person(
    pid: str = "p1",
    *,
    preferences: dict | None = None,
    hard_constraints: dict | None = None,
) -> PersonModel:
    p = PersonModel(person_id=pid, label=pid, domain="generic")
    if preferences:
        p.declared.preferences.update(preferences)
    if hard_constraints:
        p.declared.hard_constraints.update(hard_constraints)
    return p


# ---------------------------------------------------------------------------
# BifurcationMap
# ---------------------------------------------------------------------------


def test_bifurcation_map_dominant_pole_known():
    bmap = BifurcationMap(person_id="p1")
    bmap.add_attractor(
        AttractorNode(
            node_id="a1", label="stability", pole=CorePole.KNOWN, strength=0.8
        )
    )
    bmap.add_attractor(
        AttractorNode(node_id="a2", label="growth", pole=CorePole.UNKNOWN, strength=0.3)
    )
    assert bmap.dominant_pole() == CorePole.KNOWN


def test_bifurcation_map_dominant_pole_unknown():
    bmap = BifurcationMap(person_id="p1")
    bmap.add_attractor(
        AttractorNode(node_id="a1", label="risk", pole=CorePole.UNKNOWN, strength=0.9)
    )
    bmap.add_attractor(
        AttractorNode(node_id="a2", label="safety", pole=CorePole.KNOWN, strength=0.2)
    )
    assert bmap.dominant_pole() == CorePole.UNKNOWN


def test_bifurcation_map_dominant_pole_empty_defaults_to_known():
    bmap = BifurcationMap(person_id="p1")
    assert bmap.dominant_pole() == CorePole.KNOWN


def test_bifurcation_map_stores_bifurcation_points():
    bmap = BifurcationMap(person_id="p1")
    bp = BifurcationPoint(node_id="bp1", label="location", question="option A or option B")
    bmap.add_bifurcation(bp)
    assert len(bmap.bifurcation_points) == 1
    assert bmap.bifurcation_points[0].label == "location"


def test_bifurcation_map_stores_phi_edges():
    bmap = BifurcationMap(person_id="p1")
    edge = PhiEdge(source_id="a1", target_id="a2", phi=0.7, label="integrated")
    bmap.add_edge(edge)
    assert len(bmap.edges) == 1
    assert bmap.edges[0].phi == 0.7


# ---------------------------------------------------------------------------
# DialetheiaEntry
# ---------------------------------------------------------------------------


def test_dialetheia_unresolved_by_default():
    d = DialetheiaEntry(entry_id="d1", thesis="安定を求める", antithesis="変化を求める")
    assert not d.is_resolved


def test_dialetheia_resolved_when_resolution_set():
    d = DialetheiaEntry(
        entry_id="d1",
        thesis="安定を求める",
        antithesis="変化を求める",
        resolution="段階的変化で両立",
    )
    assert d.is_resolved


# ---------------------------------------------------------------------------
# CoreLayer
# ---------------------------------------------------------------------------


def test_core_layer_builds_via_helper():
    person = _make_person("p1", preferences={"remote": True})
    core = build_core_layer(person, mode=CreativityMode.CONSERVATIVE, window_id="w0")
    assert core.person.person_id == "p1"
    assert core.window_id == "w0"
    assert core.mode == CreativityMode.CONSERVATIVE


def test_core_layer_observability_counts():
    person = _make_person("p1", preferences={"remote": True, "safety": "high"})
    bp = BifurcationPoint(node_id="bp1", label="remote", question="リモートか出社か")
    att = AttractorNode(node_id="a1", label="safety", pole=CorePole.KNOWN, strength=0.7)
    dia = DialetheiaEntry(entry_id="d1", thesis="自由を優先", antithesis="安定を優先")
    core = build_core_layer(
        person,
        bifurcations=[bp],
        attractors=[att],
        dialetheias=[dia],
        window_id="w1",
    )
    report = core.observability()
    assert isinstance(report, ObservabilityReport)
    assert report.person_id == "p1"
    assert report.window_id == "w1"
    assert report.n_variables == 2
    assert report.n_bifurcations == 1
    assert report.n_attractors == 1
    assert report.n_dialetheias == 1
    assert report.n_unresolved_dialetheias == 1


def test_core_layer_coverage_score_when_attractor_matches_variable():
    person = _make_person("p1", preferences={"remote": True})
    att = AttractorNode(node_id="a1", label="remote", pole=CorePole.KNOWN, strength=0.8)
    core = build_core_layer(person, attractors=[att])
    report = core.observability()
    assert report.coverage_score == 1.0


def test_core_layer_coverage_score_zero_when_no_overlap():
    person = _make_person("p1", preferences={"remote": True})
    att = AttractorNode(
        node_id="a1", label="stability", pole=CorePole.KNOWN, strength=0.8
    )
    core = build_core_layer(person, attractors=[att])
    report = core.observability()
    assert report.coverage_score == 0.0


# ---------------------------------------------------------------------------
# score_candidate_with_core
# ---------------------------------------------------------------------------


def test_score_candidate_hard_constraint_failure_returns_zero():
    person = _make_person("p1", hard_constraints={"salary_min": 12})
    core = build_core_layer(person)
    # Candidate violates hard constraint.
    score = score_candidate_with_core(core, {"salary_min": 15})
    assert score == 0.0


def test_score_candidate_matches_preference():
    person = _make_person("p1", preferences={"remote": True})
    core = build_core_layer(person)
    score_match = score_candidate_with_core(core, {"remote": True})
    score_mismatch = score_candidate_with_core(core, {"remote": False})
    assert score_match > score_mismatch


def test_score_candidate_unknown_pole_exploratory_boosts():
    person = _make_person("p1", preferences={"remote": True})
    att_unknown = AttractorNode(
        node_id="a1", label="growth", pole=CorePole.UNKNOWN, strength=0.9
    )
    core_exp = build_core_layer(
        person, attractors=[att_unknown], mode=CreativityMode.EXPLORATORY
    )
    core_con = build_core_layer(
        person, attractors=[att_unknown], mode=CreativityMode.CONSERVATIVE
    )
    score_exp = score_candidate_with_core(core_exp, {"remote": True})
    score_con = score_candidate_with_core(core_con, {"remote": True})
    assert score_exp > score_con


def test_score_candidate_no_variables_returns_half():
    person = _make_person("p1")
    core = build_core_layer(person)
    score = score_candidate_with_core(core, {"anything": "value"})
    assert score == 0.5


# ---------------------------------------------------------------------------
# promotion_decision
# ---------------------------------------------------------------------------


def test_promotion_decision_promotes_above_threshold():
    person = _make_person("p1", preferences={"remote": True})
    core = build_core_layer(person)
    result = promotion_decision(core, {"remote": True}, threshold=0.5)
    assert result["promote"] is True
    assert result["score"] > 0.5


def test_promotion_decision_rejects_below_threshold():
    person = _make_person("p1", preferences={"remote": True})
    core = build_core_layer(person)
    result = promotion_decision(core, {"remote": False}, threshold=0.9)
    assert result["promote"] is False


# ---------------------------------------------------------------------------
# rebuild_core (cross-window mutation)
# ---------------------------------------------------------------------------


def test_rebuild_core_carries_forward_state():
    person = _make_person("p1", preferences={"remote": True})
    att = AttractorNode(node_id="a1", label="remote", pole=CorePole.KNOWN, strength=0.7)
    core_w0 = build_core_layer(person, attractors=[att], window_id="w0")
    dia = DialetheiaEntry(entry_id="d1", thesis="A", antithesis="B")
    core_w0.add_dialetheia(dia)

    new_att = AttractorNode(
        node_id="a2", label="safety", pole=CorePole.KNOWN, strength=0.6
    )
    core_w1 = rebuild_core(
        core_w0,
        new_window_id="w1",
        additional_attractors=[new_att],
    )

    assert core_w1.window_id == "w1"
    assert len(core_w1.bmap.attractors) == 2
    assert len(core_w1.dialetheias) == 1
    # Original window unchanged.
    assert core_w0.window_id == "w0"
    assert len(core_w0.bmap.attractors) == 1


def test_rebuild_core_mode_override():
    person = _make_person("p1")
    core_w0 = build_core_layer(person, mode=CreativityMode.CONSERVATIVE, window_id="w0")
    core_w1 = rebuild_core(core_w0, new_window_id="w1", mode=CreativityMode.DIALECTIC)
    assert core_w1.mode == CreativityMode.DIALECTIC
    assert core_w0.mode == CreativityMode.CONSERVATIVE


# ---------------------------------------------------------------------------
# Window-invariant regression tests (CONSENSUS_REVIEW_2026-06-08 issues 1–4)
# ---------------------------------------------------------------------------


def test_rebuild_core_person_is_independent_copy():
    """PersonModel must not be shared by reference across windows."""
    person = _make_person("p1", preferences={"remote": True})
    core_w0 = build_core_layer(person, window_id="w0")
    core_w1 = rebuild_core(core_w0, new_window_id="w1")

    assert core_w1.person is not core_w0.person
    core_w1.person.declared.preferences["remote"] = False
    assert core_w0.person.declared.preferences["remote"] is True


def test_rebuild_core_attractor_nodes_are_independent_copies():
    """Attractor nodes must not be shared between old and new window."""
    att = AttractorNode(
        node_id="a1", label="stability", pole=CorePole.KNOWN, strength=0.7
    )
    person = _make_person("p1")
    core_w0 = build_core_layer(person, attractors=[att], window_id="w0")
    core_w1 = rebuild_core(core_w0, new_window_id="w1")

    assert core_w1.bmap.attractors[0] is not core_w0.bmap.attractors[0]


def test_rebuild_core_bifurcation_points_are_independent_copies():
    """BifurcationPoint nodes must not be shared between windows."""
    bp = BifurcationPoint(node_id="bp1", label="city", question="option A or option B")
    person = _make_person("p1")
    core_w0 = build_core_layer(person, bifurcations=[bp], window_id="w0")
    core_w1 = rebuild_core(core_w0, new_window_id="w1")

    assert core_w1.bmap.bifurcation_points[0] is not core_w0.bmap.bifurcation_points[0]


def test_rebuild_core_edges_are_independent_copies():
    """PhiEdge objects must not be shared between windows."""
    edge = PhiEdge(source_id="a1", target_id="a2", phi=0.5)
    person = _make_person("p1")
    bmap = BifurcationMap(person_id="p1")
    bmap.add_edge(edge)
    core_w0 = CoreLayer(person=person, bmap=bmap, window_id="w0")
    core_w1 = rebuild_core(core_w0, new_window_id="w1")

    assert core_w1.bmap.edges[0] is not core_w0.bmap.edges[0]


def test_node_models_are_frozen():
    """BifurcationPoint, AttractorNode, PhiEdge must be immutable after construction."""
    import pytest

    bp = BifurcationPoint(node_id="bp1", label="x", question="q")
    with pytest.raises(Exception):
        bp.label = "y"  # type: ignore[misc]

    att = AttractorNode(node_id="a1", label="x")
    with pytest.raises(Exception):
        att.strength = 0.99  # type: ignore[misc]

    edge = PhiEdge(source_id="s", target_id="t")
    with pytest.raises(Exception):
        edge.phi = 1.0  # type: ignore[misc]


def test_rebuild_core_additional_bifurcations_injected():
    """additional_bifurcations param is carried into the new window."""
    person = _make_person("p1")
    core_w0 = build_core_layer(person, window_id="w0")
    extra_bp = BifurcationPoint(
        node_id="bp99", label="finance", question="commit now or defer"
    )
    core_w1 = rebuild_core(
        core_w0, new_window_id="w1", additional_bifurcations=[extra_bp]
    )

    assert len(core_w1.bmap.bifurcation_points) == 1
    assert core_w1.bmap.bifurcation_points[0].node_id == "bp99"
    assert len(core_w0.bmap.bifurcation_points) == 0


def test_rebuild_core_additional_dialetheias_injected():
    """additional_dialetheias param is carried into the new window."""
    person = _make_person("p1")
    core_w0 = build_core_layer(person, window_id="w0")
    dia = DialetheiaEntry(entry_id="d99", thesis="A", antithesis="B")
    core_w1 = rebuild_core(core_w0, new_window_id="w1", additional_dialetheias=[dia])

    assert len(core_w1.dialetheias) == 1
    assert core_w1.dialetheias[0].entry_id == "d99"
    assert len(core_w0.dialetheias) == 0
