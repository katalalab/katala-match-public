# Katala Match

Needs-matching primitives for systems that pair people with options — and for
choosing the LLM configuration that runs them.

Most matching code compresses a person into a row of shared columns, scores the
row, and returns the top N. That works for commodities and fails for anyone
whose value lives in a column nobody thought to add. This package takes the
opposite position: **keep the person as an evidence-backed variable space, make
the loss visible when you compress it, and never let one source fill the whole
result slate.**

Everything here is deterministic and testable. LLM calls are an optional
overlay, never the load-bearing path.

## What is in here

| Module | What it does |
|---|---|
| `core/pipeline.py` | `Source -> Hydrator -> Gate -> Scorer -> Selector -> SideEffect` generic pipeline |
| `core/person_model.py` | Four-layer person model (declared / behavioral / latent / context) with provenance and confidence separated from weight |
| `core/mediator.py` | Ranks candidate statements by variable coverage minus translation loss, instead of by generic agreement |
| `core/translation_loss.py` | L1-L7 loss estimator: lexical ambiguity, pragmatic mismatch, NVC need translation, preference compression, context omission, power distortion, temporal drift |
| `core/connector.py` | Deterministic connection-hypothesis generator over 8 evaluation axes with consent and risk gates |
| `core/trust_signal.py` | Claim-state / evidence gating so unverified claims cannot silently score as facts |
| `core/anti_bubble.py` | Selection with per-source diversity caps and a discovery floor |
| `core/choice_arch.py` | Layered tapering (1000 -> 10 -> 3 -> 2 -> 1) to cut decision fatigue |
| `core/core_layer.py` | Attractor/bifurcation view over a person's stable and unstable poles |
| `core/llm_mediator.py` | Provider-neutral structured-output protocol; Gemini and Claude adapters behind optional extras |
| `domains/llm_optimization/` | Turn prompt/RAG/model/retry choices into comparable candidates: fail-closed constraint gate, weighted objective, Pareto selector |
| `domains/jobs/` | False-negative rescue: a candidate weak on average signals but strong on rare role-relevant variables |
| `domains/{coaching,dating}/` | Minimal demo pipelines proving the core contract holds across domains |

## Install

```bash
pip install -e ".[dev]"     # core + pytest
pip install -e ".[gemini]"  # optional LLM mediator adapters
pytest -q
```

Python 3.11+. The only runtime dependency is `pydantic`.

## Measured LLM optimization

Pick a production LLM config from offline eval logs rather than vibes. The gate
is fail-closed: a candidate that misses schema validity, safety, latency, cost,
or hallucination thresholds is dropped before scoring, and the selector prefers
the Pareto front over raw score order.

```python
from katala_match.domains.llm_optimization import (
    CandidateConfig, EvaluationRun, rank_llm_configs, summarize_failure_clusters,
)

runs = [
    EvaluationRun(
        config=CandidateConfig(id="rag-v3", name="RAG v3", model="some-model",
                               prompt_version="mediator-v3", rag_profile="top5-rerank"),
        task_count=80, success_rate=0.93, groundedness=0.94, completeness=0.90,
        schema_valid_rate=1.0, safety_pass_rate=1.0, hallucination_rate=0.01,
        cost_per_task=0.012, latency_p95_ms=3000, retry_rate=0.02,
        failure_counts={"retrieval_miss": 3},
    ),
]

best = rank_llm_configs(runs, k=1)
clusters = summarize_failure_clusters(runs)
```

A shared failure taxonomy (`retrieval_miss`, `ranking_miss`, `context_overload`,
`generation_miss`, `citation_miss`, `schema_invalid`, `tool_loop`,
`safety_block`) makes failures comparable across domains. See
[docs/LLM_OPTIMIZATION.md](docs/LLM_OPTIMIZATION.md).

## Mediation with visible translation loss

```python
from katala_match.core import KatalaMediator, PersonModel, PersonMessage

seeker = PersonModel(person_id="p1", label="seeker", domain="jobs")
seeker.declared.goals.append("work on ambiguous problems with real autonomy")
seeker.declared.hard_constraints["remote_only"] = True

result = KatalaMediator().mediate(
    "should we move forward with this option",
    people=[seeker],
    messages=[PersonMessage(person_id="p1", text="it feels fine I guess", intent="preference")],
)

result.winner.text          # least-erasing candidate statement
result.rankings[0].loss     # per-level L1-L7 translation loss
result.next_questions       # asked instead of recommending when loss is high
```

`score = variable_coverage * 0.7 + (1 - translation_loss) * 0.3`. Deliberately
simple so it can be tested; a learned ranker can replace it later.

## Anti-bubble selection

A ranked list dominated by one source is a bubble, not a recommendation.
`select_with_diversity` enforces a per-source cap and a discovery floor, so
low-score/high-novelty candidates survive into the slate.

```python
from katala_match.core.anti_bubble import select_with_diversity
selected = select_with_diversity(scored_candidates, k=10)
```

## Design notes

- [docs/PERSON_MODEL.md](docs/PERSON_MODEL.md) — the four layers and why missing variables are not absent value
- [docs/MEDIATOR.md](docs/MEDIATOR.md) — mediation loop, L1-L7 losses, prompt shape
- [docs/CONNECTOR.md](docs/CONNECTOR.md) — connecting people, knowledge, ideas, and experiences
- [docs/CONNECTOR_AXES.md](docs/CONNECTOR_AXES.md) — the 8 evaluation axes and their gates
- [docs/LLM_OPTIMIZATION.md](docs/LLM_OPTIMIZATION.md) — metrics, constraints, failure taxonomy

## Attribution

The mediation loop shape (generate candidate statements → predict per-person
rankings → aggregate → revise after critique) is inspired by the published
Habermas Machine design from `google-deepmind/habermas_machine`. No code or
prompt text from that project is included; the objective here is variable
coverage and translation loss rather than consensus agreement.

## Status

v0. The primitives and their tests are real; the domain adapters under
`domains/` are intentionally minimal demonstrations of the core contract, not
production integrations.

## License

MIT — see [LICENSE](LICENSE).

- [Repository hygiene](.gitignore)
