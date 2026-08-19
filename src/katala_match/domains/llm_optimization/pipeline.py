"""Pipeline integration for LLM configuration optimization."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from katala_match.core.pipeline import Candidate, Gate, Pipeline, Scorer, Selector, Source

from .schema import EvaluationRun, ObjectiveWeights


@dataclass
class EvaluationRunSource(Source[EvaluationRun]):
    runs: list[EvaluationRun]

    def fetch(self) -> Iterable[Candidate[EvaluationRun]]:
        for run in self.runs:
            yield Candidate(id=run.config.id, payload=run, metadata={})


@dataclass
class ConstraintGate(Gate[EvaluationRun]):
    """Fail-closed operational constraints for production candidates."""

    min_task_count: int = 20
    min_schema_valid_rate: float = 0.98
    min_safety_pass_rate: float = 0.99
    max_latency_p95_ms: float = 12_000.0
    max_cost_per_task: float = 0.05
    max_hallucination_rate: float = 0.05

    def check(self, candidate: Candidate[EvaluationRun]) -> tuple[bool, str | None]:
        run = candidate.payload
        failures: list[str] = []
        if run.task_count < self.min_task_count:
            failures.append("task_count")
        if run.schema_valid_rate < self.min_schema_valid_rate:
            failures.append("schema_valid_rate")
        if run.safety_pass_rate < self.min_safety_pass_rate:
            failures.append("safety_pass_rate")
        if run.latency_p95_ms > self.max_latency_p95_ms:
            failures.append("latency_p95_ms")
        if run.cost_per_task > self.max_cost_per_task:
            failures.append("cost_per_task")
        if run.hallucination_rate > self.max_hallucination_rate:
            failures.append("hallucination_rate")
        if failures:
            return False, "constraint:" + ",".join(failures)
        return True, None


@dataclass
class WeightedObjectiveScorer(Scorer[EvaluationRun]):
    """Score quality while penalizing cost, latency, retry, and hallucination."""

    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)
    cost_reference: float = 0.05
    latency_reference_ms: float = 12_000.0

    def score(self, candidate: Candidate[EvaluationRun]) -> dict[str, float]:
        run = candidate.payload
        w = self.weights
        quality = (
            w.success * run.success_rate
            + w.groundedness * run.groundedness
            + w.completeness * run.completeness
            + w.schema_valid * run.schema_valid_rate
            + w.safety * run.safety_pass_rate
        )
        cost_norm = min(1.0, run.cost_per_task / self.cost_reference) if self.cost_reference else 0.0
        latency_norm = (
            min(1.0, run.latency_p95_ms / self.latency_reference_ms)
            if self.latency_reference_ms
            else 0.0
        )
        risk = (
            w.hallucination_penalty * run.hallucination_rate
            + w.cost_penalty * cost_norm
            + w.latency_penalty * latency_norm
            + w.retry_penalty * run.retry_rate
        )
        uncertainty = 0.0
        if run.confidence_low is not None and run.confidence_high is not None:
            uncertainty = max(0.0, run.confidence_high - run.confidence_low)
            risk += 0.04 * uncertainty
        total = max(0.0, min(1.0, quality - risk))
        return {
            "quality": round(quality, 3),
            "risk": round(risk, 3),
            "uncertainty": round(uncertainty, 3),
            "total": round(total, 3),
        }


@dataclass
class ParetoSelector(Selector[EvaluationRun]):
    """Prefer non-dominated candidates, then score order.

    A candidate is dominated when another candidate is at least as good on
    success, cost, latency, and hallucination, and strictly better on one.
    """

    include_dominated_fallback: bool = True

    def select(self, scored: list[Candidate[EvaluationRun]], k: int) -> list[Candidate[EvaluationRun]]:
        front = [candidate for candidate in scored if not self._is_dominated(candidate, scored)]
        ranked_front = sorted(front, key=lambda c: -c.metadata["score"]["total"])
        if len(ranked_front) >= k or not self.include_dominated_fallback:
            return ranked_front[:k]
        ranked_all = sorted(scored, key=lambda c: -c.metadata["score"]["total"])
        selected_ids = {candidate.id for candidate in ranked_front}
        for candidate in ranked_all:
            if candidate.id in selected_ids:
                continue
            ranked_front.append(candidate)
            if len(ranked_front) >= k:
                break
        return ranked_front

    def _is_dominated(
        self,
        candidate: Candidate[EvaluationRun],
        candidates: list[Candidate[EvaluationRun]],
    ) -> bool:
        run = candidate.payload
        for other in candidates:
            if other.id == candidate.id:
                continue
            other_run = other.payload
            no_worse = (
                other_run.success_rate >= run.success_rate
                and other_run.cost_per_task <= run.cost_per_task
                and other_run.latency_p95_ms <= run.latency_p95_ms
                and other_run.hallucination_rate <= run.hallucination_rate
            )
            strictly_better = (
                other_run.success_rate > run.success_rate
                or other_run.cost_per_task < run.cost_per_task
                or other_run.latency_p95_ms < run.latency_p95_ms
                or other_run.hallucination_rate < run.hallucination_rate
            )
            if no_worse and strictly_better:
                return True
        return False


def build_llm_optimization_pipeline(
    runs: list[EvaluationRun],
    gate: ConstraintGate | None = None,
    scorer: WeightedObjectiveScorer | None = None,
    selector: ParetoSelector | None = None,
) -> Pipeline[EvaluationRun]:
    return Pipeline(
        sources=[EvaluationRunSource(runs)],
        hydrators=[],
        gates=[gate or ConstraintGate()],
        scorer=scorer or WeightedObjectiveScorer(),
        selector=selector or ParetoSelector(),
        side_effects=[],
    )


def rank_llm_configs(
    runs: list[EvaluationRun],
    k: int = 5,
    gate: ConstraintGate | None = None,
    scorer: WeightedObjectiveScorer | None = None,
) -> list[dict]:
    """Return selected config rows with observed metrics and objective scores."""

    selected = build_llm_optimization_pipeline(runs, gate=gate, scorer=scorer).run(k=k)
    rows = []
    for candidate in selected:
        run = candidate.payload.to_dict()
        run["score"] = candidate.metadata["score"]
        rows.append(run)
    return rows


def summarize_failure_clusters(runs: list[EvaluationRun]) -> list[dict[str, int | str]]:
    """Aggregate failure taxonomy counts across eval runs."""

    totals: dict[str, int] = {}
    for run in runs:
        for label, count in run.failure_counts.items():
            totals[label] = totals.get(label, 0) + int(count)
    return [
        {"failure": label, "count": count}
        for label, count in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]
