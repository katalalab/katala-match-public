# LLM Optimization Domain

Katala treats LLM behavior as a measured system: observe runs, define objective
functions, compare candidates, and keep production choices inside explicit
constraints.

## Shape

```text
eval inputs
  -> candidate config(prompt / RAG / model / retry / tool policy)
  -> observed output metrics
  -> constraint gate
  -> weighted objective score
  -> Pareto selector
  -> rollout candidate
```

The implementation lives in `src/katala_match/domains/llm_optimization/`.

## Metrics

Required run-level metrics:

- `success_rate`
- `groundedness`
- `completeness`
- `schema_valid_rate`
- `safety_pass_rate`
- `hallucination_rate`
- `cost_per_task`
- `latency_p95_ms`
- `retry_rate`

The default gate is fail-closed:

- enough eval cases
- JSON/schema validity above threshold
- safety pass rate above threshold
- hallucination, cost, and p95 latency below threshold

## Failure Taxonomy

Use the same labels across domains so failures can be clustered:

- `retrieval_miss`: needed document was not retrieved
- `ranking_miss`: document was retrieved but not ranked high enough
- `context_overload`: relevant context was drowned by noise
- `generation_miss`: answer ignored available evidence
- `citation_miss`: answer failed to ground claims
- `schema_invalid`: output could not pass machine validation
- `tool_loop`: agent repeated tool calls without progress
- `safety_block`: policy or business safety guard failed

## Minimal Usage

```python
from katala_match.domains.llm_optimization import (
    CandidateConfig,
    EvaluationRun,
    rank_llm_configs,
)

runs = [
    EvaluationRun(
        config=CandidateConfig(
            id="rag-v3-gpt",
            name="RAG v3 GPT",
            model="gpt-5.4",
            prompt_version="mediator-v3",
            rag_profile="top5-rerank",
            temperature=0.1,
        ),
        task_count=80,
        success_rate=0.93,
        groundedness=0.94,
        completeness=0.90,
        schema_valid_rate=1.0,
        safety_pass_rate=1.0,
        hallucination_rate=0.01,
        cost_per_task=0.012,
        latency_p95_ms=3000,
        retry_rate=0.02,
    )
]

ranked = rank_llm_configs(runs, k=1)
```

This is deliberately offline-first. Production logs can later be normalized into
the same `EvaluationRun` schema.
