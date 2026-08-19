"""Domain decision artifacts for downstream ledger handoff.

DomainDecision is a commit artifact, not proof. It records how a domain adapter
used candidate fit, translation loss, and TrustSignal gate pressure to choose a
bounded public/domain decision.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from .trust_signal import CLAIM_STATE, TrustGate, TrustSignal, trust_signal_summary


SCHEMA_VERSION = "katala.domain_decision.v0.1"
PUBLIC_COMMIT_GATE = "domain_decision_not_proof"


class DomainDecision(BaseModel):
    schema_version: str = SCHEMA_VERSION
    id: str
    domain: str
    candidate_id: str
    candidate_label: str = ""
    base_decision: str
    decision: str
    public_commit_gate: str = PUBLIC_COMMIT_GATE
    public_commit_class: str = "hypothesis"
    claim_state: str = CLAIM_STATE
    trust_signal_ids: list[str] = Field(default_factory=list)
    trust_recommended_gate: str = ""
    evidence_record_ids: list[str] = Field(default_factory=list)
    translation_loss: float = Field(ge=0.0, le=1.0)
    domain_score: float = 0.0
    mediator_score: float = 0.0
    unresolved_variables: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)


def domain_decision_summary(
    *,
    domain: str,
    candidate_id: str,
    candidate_label: str,
    base_decision: str,
    decision: str,
    translation_loss: float,
    domain_score: float,
    mediator_score: float,
    trust_signal: TrustSignal | None = None,
    unresolved_variables: list[str] | None = None,
    next_questions: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a serializable DomainDecision artifact for sidecar transport."""
    trust = trust_signal_summary(trust_signal) if trust_signal else {}
    artifact = DomainDecision(
        id=f"domain-decision:{domain}:{candidate_id}",
        domain=domain,
        candidate_id=candidate_id,
        candidate_label=candidate_label,
        base_decision=base_decision,
        decision=decision,
        public_commit_class=_public_commit_class(trust_signal.recommended_gate if trust_signal else None),
        trust_signal_ids=[trust["id"]] if trust else [],
        trust_recommended_gate=str(trust.get("recommended_gate", "")),
        evidence_record_ids=list(trust.get("source_record_ids", [])),
        translation_loss=round(max(0.0, min(1.0, float(translation_loss))), 3),
        domain_score=round(float(domain_score), 3),
        mediator_score=round(float(mediator_score), 3),
        unresolved_variables=sorted(set(unresolved_variables or [])),
        next_questions=_dedupe(next_questions or []),
        metadata=metadata or {},
    )
    return artifact.model_dump()


def _public_commit_class(gate: TrustGate | None) -> str:
    if gate is None or gate == TrustGate.ALLOW_HYPOTHESIS:
        return "hypothesis"
    return gate.value


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
