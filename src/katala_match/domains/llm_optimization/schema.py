"""Schemas for measured LLM optimization.

The domain turns prompt/RAG/model choices into comparable candidates. It is
intentionally provider-neutral so offline eval logs can drive selection before
any production rollout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateConfig:
    """A prompt, RAG, model, routing, or retry configuration under test."""

    id: str
    name: str
    model: str
    prompt_version: str
    rag_profile: str = ""
    tool_policy: str = ""
    temperature: float = 0.0
    top_p: float = 1.0
    retry_policy: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CandidateConfig":
        return cls(
            id=str(data["id"]),
            name=str(data.get("name", data["id"])),
            model=str(data.get("model", "")),
            prompt_version=str(data.get("prompt_version", "")),
            rag_profile=str(data.get("rag_profile", "")),
            tool_policy=str(data.get("tool_policy", "")),
            temperature=float(data.get("temperature", 0.0)),
            top_p=float(data.get("top_p", 1.0)),
            retry_policy=str(data.get("retry_policy", "")),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "rag_profile": self.rag_profile,
            "tool_policy": self.tool_policy,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "retry_policy": self.retry_policy,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationRun:
    """Observed metrics for one candidate over an eval dataset."""

    config: CandidateConfig
    task_count: int
    success_rate: float
    groundedness: float
    completeness: float
    schema_valid_rate: float
    safety_pass_rate: float
    hallucination_rate: float
    cost_per_task: float
    latency_p95_ms: float
    retry_rate: float = 0.0
    failure_counts: dict[str, int] = field(default_factory=dict)
    confidence_low: float | None = None
    confidence_high: float | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationRun":
        config_data = data.get("config", data)
        return cls(
            config=CandidateConfig.from_dict(config_data),
            task_count=int(data.get("task_count", 0)),
            success_rate=float(data.get("success_rate", 0.0)),
            groundedness=float(data.get("groundedness", 0.0)),
            completeness=float(data.get("completeness", 0.0)),
            schema_valid_rate=float(data.get("schema_valid_rate", 0.0)),
            safety_pass_rate=float(data.get("safety_pass_rate", 0.0)),
            hallucination_rate=float(data.get("hallucination_rate", 1.0)),
            cost_per_task=float(data.get("cost_per_task", 0.0)),
            latency_p95_ms=float(data.get("latency_p95_ms", 0.0)),
            retry_rate=float(data.get("retry_rate", 0.0)),
            failure_counts=dict(data.get("failure_counts", {})),
            confidence_low=(
                None if data.get("confidence_low") is None else float(data["confidence_low"])
            ),
            confidence_high=(
                None if data.get("confidence_high") is None else float(data["confidence_high"])
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "task_count": self.task_count,
            "success_rate": self.success_rate,
            "groundedness": self.groundedness,
            "completeness": self.completeness,
            "schema_valid_rate": self.schema_valid_rate,
            "safety_pass_rate": self.safety_pass_rate,
            "hallucination_rate": self.hallucination_rate,
            "cost_per_task": self.cost_per_task,
            "latency_p95_ms": self.latency_p95_ms,
            "retry_rate": self.retry_rate,
            "failure_counts": self.failure_counts,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
        }


@dataclass
class ObjectiveWeights:
    """Weights for constrained multi-objective scoring."""

    success: float = 0.34
    groundedness: float = 0.18
    completeness: float = 0.14
    schema_valid: float = 0.12
    safety: float = 0.12
    hallucination_penalty: float = 0.16
    cost_penalty: float = 0.08
    latency_penalty: float = 0.07
    retry_penalty: float = 0.04
