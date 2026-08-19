from katala_match.core import (
    ConnectorAxis,
    ConnectorNode,
    ConnectorNodeKind,
    EvidenceKind,
    KatalaConnector,
    PersonModel,
    Variable,
    node_from_person,
)


def test_connector_generates_multi_axis_question_to_knowledge_candidate():
    source = ConnectorNode(
        id="q-connect",
        kind=ConnectorNodeKind.QUESTION,
        label="繋ぐをアルゴリズム化したい",
        themes=["creativity", "connection", "synergy"],
        variables=["translation_loss", "meaningful_distance", "synergy"],
        needs=["algorithmize_connection", "scholarly_axes", "small_mvp"],
        contexts=["katala_match", "now"],
    )
    target = ConnectorNode(
        id="network-science",
        kind=ConnectorNodeKind.KNOWLEDGE,
        label="weak ties and structural holes",
        themes=["social_network", "connection", "brokerage"],
        variables=["bridge_value", "weak_tie", "structural_hole", "algorithmize_connection"],
        offers=["algorithmize_connection", "scholarly_axes", "bridge_value"],
        contexts=["katala_match"],
        evidence={"doi": "10.1086/225469"},
    )

    candidate = KatalaConnector().evaluate(
        source,
        target,
        context={"contexts": ["katala_match", "now"], "preferred_actions": ["quick_test"]},
    )

    assert candidate.connection_type == "question_to_knowledge"
    assert "algorithmize_connection" in candidate.complementary_variables
    assert candidate.total_score > 0.35
    assert candidate.next_action
    axes = candidate.axis_map()
    assert ConnectorAxis.SOCIAL_NETWORK in axes
    assert ConnectorAxis.CREATIVITY in axes
    assert ConnectorAxis.INFORMATION in axes
    assert axes[ConnectorAxis.SOCIAL_NETWORK].source_theory


def test_connector_keeps_person_to_person_safety_notes_visible():
    source = ConnectorNode(
        id="person-a",
        kind=ConnectorNodeKind.PERSON,
        label="idea seeker",
        needs=["creative_feedback"],
        constraints=["privacy"],
        contexts=["early_stage"],
    )
    target = ConnectorNode(
        id="person-b",
        kind=ConnectorNodeKind.PERSON,
        label="expert",
        offers=["creative_feedback"],
        contexts=["early_stage"],
    )

    candidate = KatalaConnector().evaluate(source, target)

    assert candidate.score.risk >= 0.6
    assert any("consent" in note for note in candidate.safety_notes)
    assert "person_to_person" in candidate.connection_type


def test_node_from_person_preserves_person_model_variables():
    person = PersonModel(person_id="p1", label="connector builder", domain="connector")
    person.declared.goals.append("algorithmize_connection")
    person.declared.preferences["scholarly_axes"] = True
    person.latent.unique_strengths.append(
        Variable(
            name="structural_bridge_design",
            value=True,
            weight=0.9,
            confidence=0.8,
            evidence=EvidenceKind.INFERENCE,
        )
    )
    person.context.roles.append("builder")

    node = node_from_person(person)

    assert node.kind == ConnectorNodeKind.PERSON
    assert "scholarly_axes" in node.variables
    assert "algorithmize_connection" in node.needs
    assert "structural_bridge_design" in node.offers


def test_connector_ranks_creative_bridge_above_redundant_match():
    source = ConnectorNode(
        id="q",
        kind=ConnectorNodeKind.QUESTION,
        label="creative connector question",
        themes=["creativity", "connection"],
        variables=["meaningful_distance", "translation_loss"],
        needs=["small_mvp", "scholarly_axes"],
        contexts=["katala_match"],
    )
    creative_bridge = ConnectorNode(
        id="info-theory",
        kind=ConnectorNodeKind.KNOWLEDGE,
        label="information theory",
        themes=["information", "signal", "noise"],
        variables=["translation_loss", "compression"],
        offers=["scholarly_axes", "small_mvp"],
    )
    redundant = ConnectorNode(
        id="same-words",
        kind=ConnectorNodeKind.KNOWLEDGE,
        label="same words",
        themes=["creativity", "connection"],
        variables=["meaningful_distance"],
        offers=[],
    )

    ranked = KatalaConnector().rank(source, [redundant, creative_bridge], context={"preferred_actions": ["quick_test"]})

    assert ranked[0].target_id == "info-theory"

