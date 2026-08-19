"""Trust signals derived from bounded research evidence bundles.

The trust signal layer is a gate input, not a truth engine. It keeps external
and local evidence visible for downstream matching while preserving Katala's
hypothesis-only public contract.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


SCHEMA_VERSION = "katala.trust_signal.v0.1"
CLAIM_STATE = "hypothesis_only_no_truth_promotion"
PUBLIC_COMMIT_GATE = "trust_signal_not_proof"
TRUST_GATE_PENALTIES = {
    "allow_hypothesis": 0.0,
    "partial_commit_with_visible_uncertainty": 0.12,
    "hold_final_claim_until_evidence": 0.3,
    "clarify_or_abstain": 0.4,
}


class TrustGate(str, Enum):
    ALLOW_HYPOTHESIS = "allow_hypothesis"
    PARTIAL_COMMIT_WITH_VISIBLE_UNCERTAINTY = "partial_commit_with_visible_uncertainty"
    HOLD_FINAL_CLAIM_UNTIL_EVIDENCE = "hold_final_claim_until_evidence"
    CLARIFY_OR_ABSTAIN = "clarify_or_abstain"


class TrustSignal(BaseModel):
    id: str
    subject: str = ""
    claim: str = ""
    source_record_ids: list[str] = Field(default_factory=list)
    evidence_kinds: list[str] = Field(default_factory=list)
    provenance_score: float = Field(ge=0.0, le=1.0)
    retrievability_score: float = Field(ge=0.0, le=1.0)
    freshness_score: float = Field(ge=0.0, le=1.0)
    cross_check_score: float = Field(ge=0.0, le=1.0)
    aggregate_trust_score: float = Field(ge=0.0, le=1.0)
    verification_state: str
    recommended_gate: TrustGate
    claim_state: str = CLAIM_STATE
    risk_flags: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    rationale: str = ""


class TrustSignalBundle(BaseModel):
    schema_version: str = SCHEMA_VERSION
    source_system: str = "katala-match"
    source_bundle_schema: str = ""
    generated_at: str = Field(default_factory=lambda: _utc_now_iso())
    claim_state: str = CLAIM_STATE
    public_commit_gate: str = PUBLIC_COMMIT_GATE
    subject: str = ""
    claim: str = ""
    signals: list[TrustSignal] = Field(default_factory=list)
    record_counts: dict[str, int] = Field(default_factory=dict)
    open_questions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def research_bundle_to_trust_signals(
    bundle: Any,
    *,
    subject: str = "",
    claim: str = "",
    now: datetime | None = None,
) -> TrustSignalBundle:
    """Convert a Katala ResearchBundle-like object into aggregate trust signals."""
    data = _to_dict(bundle)
    records = _as_dicts(data.get("records"))
    record_counts = _record_counts(data, records)
    source_bundle_schema = _text(data.get("schema_version"))
    bundle_questions = [_text(item) for item in _as_list(data.get("open_questions")) if _text(item)]

    signal = _aggregate_signal(records, subject=subject, claim=claim, bundle_questions=bundle_questions, now=now)
    questions = _dedupe(bundle_questions + signal.open_questions)
    return TrustSignalBundle(
        source_bundle_schema=source_bundle_schema,
        subject=subject,
        claim=claim,
        signals=[signal],
        record_counts=record_counts,
        open_questions=questions,
        metadata={
            "source_system": _text(data.get("source_system")),
            "source_command": _text(data.get("source_command")),
            "query": _text(data.get("query")),
            "archive": _text(data.get("archive")),
            "source_claim_state": _text(data.get("claim_state")),
            "source_public_commit_gate": _text(data.get("public_commit_gate")),
        },
    )


def research_bundle_to_trust_signal(
    bundle: Any,
    *,
    subject: str = "",
    claim: str = "",
    now: datetime | None = None,
) -> TrustSignal:
    """Return the aggregate signal for callers that do not need bundle metadata."""
    return research_bundle_to_trust_signals(bundle, subject=subject, claim=claim, now=now).signals[0]


def trust_gate_penalty(signal: TrustSignal) -> float:
    """Return a bounded score penalty for using a trust signal in domain ranking."""
    penalty = TRUST_GATE_PENALTIES.get(signal.recommended_gate.value, 0.25)
    if signal.aggregate_trust_score < 0.5:
        penalty += 0.05
    return round(_clamp(penalty), 3)


def trust_signal_summary(signal: TrustSignal) -> dict[str, Any]:
    """Return serializable metadata for candidate/domain decision artifacts."""
    return {
        "id": signal.id,
        "claim_state": signal.claim_state,
        "recommended_gate": signal.recommended_gate.value,
        "verification_state": signal.verification_state,
        "aggregate_trust_score": signal.aggregate_trust_score,
        "penalty": trust_gate_penalty(signal),
        "risk_flags": list(signal.risk_flags),
        "source_record_ids": list(signal.source_record_ids),
        "public_commit_gate": PUBLIC_COMMIT_GATE,
    }


def _aggregate_signal(
    records: list[dict[str, Any]],
    *,
    subject: str,
    claim: str,
    bundle_questions: list[str],
    now: datetime | None,
) -> TrustSignal:
    evidence_ids = [_record_id(record, idx) for idx, record in enumerate(records, start=1)]
    evidence_kinds = sorted({_text(record.get("kind")) or "unknown" for record in records})
    provenance_score = _mean([_provenance_score(record) for record in records])
    retrievability_score = _mean([_retrievability_score(record) for record in records])
    freshness_score = _mean([_freshness_score(record, now=now) for record in records])
    cross_check_score = _cross_check_score(records)
    aggregate = _clamp(
        provenance_score * 0.35
        + retrievability_score * 0.25
        + freshness_score * 0.15
        + cross_check_score * 0.25
    )
    risk_flags = _risk_flags(records)
    verification_state = _verification_state(records, risk_flags)
    gate = _recommended_gate(verification_state, risk_flags)
    open_questions = _signal_questions(risk_flags)
    if bundle_questions and gate == TrustGate.ALLOW_HYPOTHESIS:
        gate = TrustGate.PARTIAL_COMMIT_WITH_VISIBLE_UNCERTAINTY

    return TrustSignal(
        id="trust-signal-aggregate-001",
        subject=subject,
        claim=claim,
        source_record_ids=evidence_ids,
        evidence_kinds=evidence_kinds,
        provenance_score=round(provenance_score, 3),
        retrievability_score=round(retrievability_score, 3),
        freshness_score=round(freshness_score, 3),
        cross_check_score=round(cross_check_score, 3),
        aggregate_trust_score=round(aggregate, 3),
        verification_state=verification_state,
        recommended_gate=gate,
        risk_flags=risk_flags,
        open_questions=open_questions,
        rationale=_rationale(verification_state, gate, risk_flags),
    )


def _provenance_score(record: dict[str, Any]) -> float:
    tier_weights = {
        "captured_page": 0.95,
        "official": 0.9,
        "primary": 0.88,
        "local_repo": 0.72,
        "archived_feed": 0.7,
        "external_candidate": 0.5,
        "candidate": 0.4,
    }
    source_type_weights = {
        "official": 0.9,
        "primary": 0.88,
        "standards": 0.86,
        "local_repository": 0.72,
        "archived_feed": 0.7,
        "web": 0.5,
    }
    score = tier_weights.get(_text(record.get("provenance_tier")), 0.35)
    score = max(score, source_type_weights.get(_text(record.get("source_type")), 0.0))
    quality = _float(record.get("quality_score"))
    if quality is not None:
        normalized = _clamp(quality / 100 if quality > 1 else quality)
        score = _clamp(score + (normalized - 0.5) * 0.1)
    return score


def _retrievability_score(record: dict[str, Any]) -> float:
    url = _text(record.get("url"))
    metadata = _to_dict(record.get("metadata"))
    if url.startswith(("https://", "http://")):
        return 1.0
    if url.startswith("repo://"):
        return 0.85
    if url:
        return 0.65
    if _text(metadata.get("repo_path")) and _text(metadata.get("rel_path")):
        return 0.75
    return 0.25


def _freshness_score(record: dict[str, Any], *, now: datetime | None) -> float:
    date_text = _text(record.get("captured_at")) or _text(record.get("published_at"))
    if not date_text:
        return 0.45
    parsed = _parse_datetime(date_text)
    if parsed is None:
        return 0.6
    anchor = now or datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    days = (anchor - parsed).days
    if days < 0:
        return 0.65
    if days <= 30:
        return 0.9
    if days <= 365:
        return 0.75
    return 0.55


def _cross_check_score(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    kinds = {_text(record.get("kind")) or "unknown" for record in records}
    sources = {_text(record.get("source")) or _text(record.get("url")) for record in records}
    source_count = len([source for source in sources if source])
    if {"page_snapshot", "repo_document"}.issubset(kinds) or {"page_snapshot", "feed_item"}.issubset(kinds):
        return 0.9
    if len(kinds) >= 3:
        return 0.85
    if len(kinds) >= 2:
        return 0.65
    if source_count >= 2:
        return 0.5
    return 0.35


def _risk_flags(records: list[dict[str, Any]]) -> list[str]:
    if not records:
        return ["no_evidence"]
    kinds = {_text(record.get("kind")) for record in records}
    flags: list[str] = []
    if kinds <= {"repo_document"}:
        flags.append("local_only_evidence")
    if "web_result" in kinds and "page_snapshot" not in kinds:
        flags.append("web_candidates_without_page_snapshots")
    if "repo_document" in kinds and kinds.isdisjoint({"web_result", "feed_item", "page_snapshot"}):
        flags.append("missing_external_corroboration")
    if any(not _text(record.get("url")) for record in records):
        flags.append("non_retrievable_record")
    return _dedupe(flags)


def _verification_state(records: list[dict[str, Any]], risk_flags: list[str]) -> str:
    if not records:
        return "insufficient_evidence"
    if "local_only_evidence" in risk_flags:
        return "local_only"
    kinds = {_text(record.get("kind")) for record in records}
    if kinds <= {"web_result"}:
        return "candidate_evidence"
    if "page_snapshot" in kinds:
        return "captured_evidence"
    if len(kinds) >= 2:
        return "cross_checked_candidate"
    return "single_surface_candidate"


def _recommended_gate(verification_state: str, risk_flags: list[str]) -> TrustGate:
    if verification_state == "insufficient_evidence":
        return TrustGate.CLARIFY_OR_ABSTAIN
    if "non_retrievable_record" in risk_flags:
        return TrustGate.HOLD_FINAL_CLAIM_UNTIL_EVIDENCE
    if verification_state in {"local_only", "candidate_evidence", "single_surface_candidate"}:
        return TrustGate.PARTIAL_COMMIT_WITH_VISIBLE_UNCERTAINTY
    return TrustGate.ALLOW_HYPOTHESIS


def _signal_questions(risk_flags: list[str]) -> list[str]:
    questions: list[str] = []
    if "no_evidence" in risk_flags:
        questions.append("Populate evidence records before ranking claims.")
    if "local_only_evidence" in risk_flags:
        questions.append("Add at least one external or captured source before public synthesis.")
    if "web_candidates_without_page_snapshots" in risk_flags:
        questions.append("Capture or read the top web candidates before treating them as evidence.")
    if "non_retrievable_record" in risk_flags:
        questions.append("Attach retrievable URLs or repo paths to every evidence record.")
    return questions


def _rationale(verification_state: str, gate: TrustGate, risk_flags: list[str]) -> str:
    if verification_state == "insufficient_evidence":
        return "No evidence records were available, so the claim must remain clarify/hold."
    if risk_flags:
        return f"Evidence is usable for matching, but gate {gate.value} remains due to {', '.join(risk_flags)}."
    return f"Evidence spans enough surfaces for {gate.value}; it remains hypothesis-only, not proof."


def _record_counts(data: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {key: int(value) for key, value in _to_dict(data.get("record_counts")).items() if isinstance(value, int)}
    if "total_records" not in counts:
        counts["total_records"] = len(records)
    return counts


def _record_id(record: dict[str, Any], index: int) -> str:
    return _text(record.get("id")) or f"record-{index:03d}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(normalized[:10])
    except ValueError:
        return None


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in (_to_dict(item) for item in value) if item]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    return value if isinstance(value, str) else "" if value is None else str(value)


def _float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(values: list[float]) -> float:
    return _clamp(sum(values) / len(values)) if values else 0.0


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item and item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped
