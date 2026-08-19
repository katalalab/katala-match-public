from katala_match.domains.jobs import (
    evaluate_false_negative_rescue,
    match_context_for_role,
    mediate_false_negative_role,
    screening_false_negative_person,
)


def test_jobs_rescues_screening_false_negative_candidate():
    person = screening_false_negative_person()
    role = {
        "id": "ai-ops-product-role",
        "title": "AI workflow product operator",
        "degree": "",
        "years_experience": 0,
        "company_tier": "",
        "keyword_score": 0.2,
        "role_needs": [
            "ambiguous_problem_structuring",
            "operator_empathy",
            "agentic_tooling_literacy",
        ],
    }

    result = evaluate_false_negative_rescue(role, person)

    assert result.baseline_rejected is True
    assert result.rescued is True
    assert "degree" in result.missing_average_signals
    assert result.matched_unique_variables == [
        "agentic_tooling_literacy",
        "ambiguous_problem_structuring",
        "operator_empathy",
    ]


def test_jobs_false_negative_uses_match_context_and_mediator_shape():
    person = screening_false_negative_person()
    role = {
        "id": "ai-ops-product-role",
        "title": "AI workflow product operator",
        "degree": "",
        "years_experience": 0,
        "company_tier": "",
        "keyword_score": 0.2,
        "role_needs": [
            "ambiguous_problem_structuring",
            "operator_empathy",
            "agentic_tooling_literacy",
        ],
    }

    context = match_context_for_role(role, person)
    mediated = mediate_false_negative_role(role, person)

    assert context.domain == "jobs"
    assert context.candidate_id == "ai-ops-product-role"
    assert mediated["rescued"] is True
    assert mediated["context_domain"] == "jobs"
    assert "平均シグナル" in mediated["mediator_winner"]
    assert mediated["mediator_score"] > 0
