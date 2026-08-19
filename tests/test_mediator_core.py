from katala_match.core import (
    CandidateStatement,
    KatalaMediator,
    MatchContext,
    PersonMessage,
    PersonModel,
    Variable,
    estimate_translation_loss,
)
from katala_match.core.llm_mediator import build_llm_mediator_prompt


def test_person_model_keeps_four_layers_and_selects_strongest_variable():
    person = PersonModel(person_id="p1", label="candidate", domain="jobs")
    person.declared.preferences["remote"] = True
    person.declared.hard_constraints["salary_min"] = 700
    person.behavioral.accepted.append("ai-product-role")
    person.latent.unique_strengths.append(Variable(name="systems_thinking", value=True, weight=0.9, confidence=0.8))
    person.context.roles.append("parent")

    variables = person.variable_map()

    assert set(["remote", "salary_min", "systems_thinking"]).issubset(variables)
    assert person.hard_constraint_failures({"salary_min": 650}) == ["salary_min: 650 != 700"]
    assert person.hard_constraint_failures({"salary_min": 700}) == []


def test_translation_loss_prioritizes_rsa_and_nvc_gaps():
    speaker = PersonModel(person_id="p1")
    speaker.declared.hard_dislikes.append("押し切られる")
    report = estimate_translation_loss(
        "ちょっと不安です。押し切られる感じは無理かも。",
        speaker=speaker,
        context={"domain": "estate"},
    )

    by_level = report.by_level()
    assert by_level["L2_pragmatic_rsa_mismatch"].score > 0
    assert by_level["L3_nvc_need_translation"].score >= 0.4
    assert report.overall > 0


def test_mediator_ranks_candidate_by_variable_coverage_and_loss():
    p1 = PersonModel(person_id="p1", label="borrower")
    p1.declared.preferences["safety"] = "high"
    p1.declared.hard_constraints["rent_max"] = 13
    p2 = PersonModel(person_id="p2", label="owner")
    p2.declared.preferences["stable_payment"] = True

    mediator = KatalaMediator()
    result = mediator.mediate(
        "この物件を進めるか",
        [p1, p2],
        [
            PersonMessage(person_id="p1", text="安全性と家賃上限が大事です"),
            PersonMessage(person_id="p2", text="安定支払いなら進めたいです"),
        ],
        [
            CandidateStatement(text="安全性、rent_max、stable_paymentを確認して進める", covered_variables=["safety", "rent_max", "stable_payment"]),
            CandidateStatement(text="なんとなく良さそうなので進める", covered_variables=[]),
        ],
        context={"domain": "estate"},
    )

    assert result.winner.covered_variables == ["safety", "rent_max", "stable_payment"]
    assert len(result.rankings) == 4


def test_llm_mediator_prompt_preserves_context_and_schema():
    person = PersonModel(person_id="p1", label="seeker", domain="estate")
    person.declared.preferences["safety"] = True
    mediator = KatalaMediator()
    result = mediator.mediate(
        "この候補を進めるか",
        [person],
        [PersonMessage(person_id="p1", text="安全性を確認したい")],
        [CandidateStatement(text="安全性を確認済み", covered_variables=["safety"])],
        context={"domain": "estate"},
    )
    context = MatchContext(
        domain="estate",
        candidate_id="property-1",
        candidate_label="候補1",
        candidate_payload={"id": "property-1", "name": "候補1", "layout": "1LDK"},
        people=[person],
        messages=[PersonMessage(person_id="p1", text="安全性を確認したい")],
    )

    prompt = build_llm_mediator_prompt(context, result)

    assert "Domain: estate" in prompt
    assert "property-1" in prompt
    assert "JSON schema" in prompt
    assert "next_questions" in prompt
