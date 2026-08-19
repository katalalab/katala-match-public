"""Small reusable domain pieces for checking core interface sufficiency."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from katala_match.core import TrustSignal, TrustSignalBundle, trust_gate_penalty, trust_signal_summary
from katala_match.core.pipeline import Candidate, Gate, Hydrator, Scorer, Selector, Source


@dataclass
class InMemorySource(Source[dict[str, Any]]):
    items: list[dict[str, Any]]

    def fetch(self) -> Iterable[Candidate[dict[str, Any]]]:
        for item in self.items:
            yield Candidate(id=str(item["id"]), payload=item, metadata={})


class NoopHydrator(Hydrator[dict[str, Any]]):
    def hydrate(self, candidate: Candidate[dict[str, Any]]) -> Candidate[dict[str, Any]]:
        return candidate


@dataclass
class RequiredFieldsGate(Gate[dict[str, Any]]):
    fields: tuple[str, ...]

    def check(self, candidate: Candidate[dict[str, Any]]) -> tuple[bool, str | None]:
        missing = [field for field in self.fields if candidate.payload.get(field) in (None, "")]
        if missing:
            return False, f"missing:{','.join(missing)}"
        return True, None


@dataclass
class WeightedFieldScorer(Scorer[dict[str, Any]]):
    weights: dict[str, float]

    def score(self, candidate: Candidate[dict[str, Any]]) -> dict[str, float]:
        fit = 0.0
        possible = 0.0
        for field, weight in self.weights.items():
            possible += abs(weight)
            value = candidate.payload.get(field)
            if isinstance(value, bool):
                fit += weight if value else 0.0
            elif isinstance(value, (int, float)):
                fit += max(0.0, min(1.0, float(value))) * weight
            elif value:
                fit += weight
        normalized = fit / possible if possible else 0.0
        discovery = float(candidate.payload.get("discovery", 0.0) or 0.0)
        risk = float(candidate.payload.get("risk", 0.0) or 0.0)
        total = max(0.0, min(1.0, normalized + 0.2 * discovery - 0.2 * risk))
        return {
            "fit": round(normalized, 3),
            "discovery": round(discovery, 3),
            "risk": round(risk, 3),
            "total": round(total, 3),
        }


@dataclass
class TrustSignalScorer(Scorer[dict[str, Any]]):
    """Decorate a domain scorer with TrustSignal gate pressure.

    The base score remains visible as `base_total`; the adjusted `total` is
    lower only when the evidence gate says a public/domain claim needs caution.
    """

    base: Scorer[dict[str, Any]]
    trust_signals: dict[str, Any] = field(default_factory=dict)

    def score(self, candidate: Candidate[dict[str, Any]]) -> dict[str, float]:
        scores = dict(self.base.score(candidate))
        signal = _resolve_trust_signal(candidate.id, self.trust_signals)
        if signal is None:
            return scores
        penalty = trust_gate_penalty(signal)
        base_total = float(scores.get("total", 0.0) or 0.0)
        adjusted_total = max(0.0, min(1.0, base_total - penalty))
        candidate.metadata["trust_signal"] = trust_signal_summary(signal)
        scores["base_total"] = round(base_total, 3)
        scores["trust"] = round(signal.aggregate_trust_score, 3)
        scores["trust_adjustment"] = round(-penalty, 3)
        scores["total"] = round(adjusted_total, 3)
        return scores


class TopKSelector(Selector[dict[str, Any]]):
    def select(self, scored: list[Candidate[dict[str, Any]]], k: int) -> list[Candidate[dict[str, Any]]]:
        return sorted(scored, key=lambda c: -c.metadata["score"]["total"])[:k]


def _resolve_trust_signal(candidate_id: str, trust_signals: dict[str, Any]) -> TrustSignal | None:
    value = trust_signals.get(candidate_id, trust_signals.get("*"))
    if value is None:
        return None
    if isinstance(value, TrustSignal):
        return value
    if isinstance(value, TrustSignalBundle):
        return value.signals[0] if value.signals else None
    if isinstance(value, dict):
        if "signals" in value:
            bundle = TrustSignalBundle.model_validate(value)
            return bundle.signals[0] if bundle.signals else None
        return TrustSignal.model_validate(value)
    return None
