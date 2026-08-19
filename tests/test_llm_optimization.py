from katala_match.domains.llm_optimization import (
    CandidateConfig,
    ConstraintGate,
    EvaluationRun,
    rank_llm_configs,
    summarize_failure_clusters,
)


def _run(
    config_id: str,
    *,
    success_rate: float,
    cost_per_task: float,
    latency_p95_ms: float,
    hallucination_rate: float = 0.01,
    schema_valid_rate: float = 1.0,
    safety_pass_rate: float = 1.0,
    groundedness: float = 0.9,
    completeness: float = 0.9,
) -> EvaluationRun:
    return EvaluationRun(
        config=CandidateConfig(
            id=config_id,
            name=config_id,
            model="gpt-test",
            prompt_version="v1",
            rag_profile="top5-rerank",
            temperature=0.1,
        ),
        task_count=80,
        success_rate=success_rate,
        groundedness=groundedness,
        completeness=completeness,
        schema_valid_rate=schema_valid_rate,
        safety_pass_rate=safety_pass_rate,
        hallucination_rate=hallucination_rate,
        cost_per_task=cost_per_task,
        latency_p95_ms=latency_p95_ms,
        retry_rate=0.02,
    )


def test_rank_llm_configs_prefers_measured_tradeoff_over_raw_accuracy():
    expensive = _run(
        "high-accuracy-expensive",
        success_rate=0.95,
        cost_per_task=0.045,
        latency_p95_ms=11_500,
    )
    balanced = _run(
        "balanced",
        success_rate=0.93,
        cost_per_task=0.012,
        latency_p95_ms=3_000,
    )

    ranked = rank_llm_configs([expensive, balanced], k=2)

    assert ranked[0]["config"]["id"] == "balanced"
    assert ranked[0]["score"]["total"] > ranked[1]["score"]["total"]


def test_constraint_gate_filters_invalid_json_and_hallucination_risk():
    invalid = _run(
        "invalid-json",
        success_rate=0.99,
        cost_per_task=0.01,
        latency_p95_ms=2_500,
        schema_valid_rate=0.94,
    )
    hallucinating = _run(
        "hallucinating",
        success_rate=0.98,
        cost_per_task=0.01,
        latency_p95_ms=2_500,
        hallucination_rate=0.12,
    )
    safe = _run("safe", success_rate=0.91, cost_per_task=0.02, latency_p95_ms=4_000)

    ranked = rank_llm_configs([invalid, hallucinating, safe], k=3, gate=ConstraintGate())

    assert [row["config"]["id"] for row in ranked] == ["safe"]


def test_summarize_failure_clusters_counts_taxonomy():
    first = _run("first", success_rate=0.9, cost_per_task=0.01, latency_p95_ms=2_500)
    first.failure_counts = {"retrieval_miss": 3, "schema_invalid": 1}
    second = _run("second", success_rate=0.9, cost_per_task=0.01, latency_p95_ms=2_500)
    second.failure_counts = {"retrieval_miss": 2, "context_overload": 4}

    clusters = summarize_failure_clusters([first, second])

    assert clusters == [
        {"failure": "retrieval_miss", "count": 5},
        {"failure": "context_overload", "count": 4},
        {"failure": "schema_invalid", "count": 1},
    ]
