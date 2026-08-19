"""Four-layer person model for variable-as-variable matching.

The model keeps declared preferences separate from behavior, inferred latent
needs, and relational/contextual constraints. This avoids collapsing a person
into a single average-fit vector too early.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EvidenceKind(str, Enum):
    DECLARATION = "declaration"
    BEHAVIOR = "behavior"
    INFERENCE = "inference"
    CONTEXT = "context"


class Variable(BaseModel):
    """A single match variable with provenance and uncertainty."""

    name: str
    value: Any
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: EvidenceKind = EvidenceKind.INFERENCE
    source: str = ""
    notes: str = ""

    def weighted_confidence(self) -> float:
        return round(self.weight * self.confidence, 4)


class DeclaredLayer(BaseModel):
    """Layer 1: explicit self-report and hard constraints."""

    goals: list[str] = Field(default_factory=list)
    hard_constraints: dict[str, Any] = Field(default_factory=dict)
    preferences: dict[str, Any] = Field(default_factory=dict)
    hard_dislikes: list[str] = Field(default_factory=list)
    direct_quotes: list[str] = Field(default_factory=list)


class BehavioralLayer(BaseModel):
    """Layer 2: choices, rejects, searches, and observed tradeoffs."""

    accepted: list[str] = Field(default_factory=list)
    rejected: list[str] = Field(default_factory=list)
    tradeoffs: dict[str, Any] = Field(default_factory=dict)
    revealed_variables: list[Variable] = Field(default_factory=list)


class LatentLayer(BaseModel):
    """Layer 3: inferred needs, values, fears, and non-obvious strengths."""

    needs: list[Variable] = Field(default_factory=list)
    values: list[Variable] = Field(default_factory=list)
    risks: list[Variable] = Field(default_factory=list)
    unique_strengths: list[Variable] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)


class ContextLayer(BaseModel):
    """Layer 4: roles, relationships, timing, resources, and power context."""

    roles: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    resources: dict[str, Any] = Field(default_factory=dict)
    time_horizon: str = ""
    power_constraints: list[str] = Field(default_factory=list)
    safety_constraints: list[str] = Field(default_factory=list)


class PersonModel(BaseModel):
    """A person represented as a sparse, evidence-backed variable space."""

    person_id: str
    label: str = ""
    domain: str = "generic"
    declared: DeclaredLayer = Field(default_factory=DeclaredLayer)
    behavioral: BehavioralLayer = Field(default_factory=BehavioralLayer)
    latent: LatentLayer = Field(default_factory=LatentLayer)
    context: ContextLayer = Field(default_factory=ContextLayer)

    def variables(self) -> list[Variable]:
        vars_: list[Variable] = []
        for key, value in self.declared.preferences.items():
            vars_.append(Variable(
                name=key,
                value=value,
                weight=0.8,
                confidence=0.8,
                evidence=EvidenceKind.DECLARATION,
            ))
        for key, value in self.declared.hard_constraints.items():
            vars_.append(Variable(
                name=key,
                value=value,
                weight=1.0,
                confidence=0.9,
                evidence=EvidenceKind.DECLARATION,
                notes="hard_constraint",
            ))
        vars_.extend(self.behavioral.revealed_variables)
        vars_.extend(self.latent.needs)
        vars_.extend(self.latent.values)
        vars_.extend(self.latent.risks)
        vars_.extend(self.latent.unique_strengths)
        return vars_

    def variable_map(self) -> dict[str, Variable]:
        """Return the strongest known variable for each name."""
        result: dict[str, Variable] = {}
        for var in self.variables():
            existing = result.get(var.name)
            if existing is None or var.weighted_confidence() > existing.weighted_confidence():
                result[var.name] = var
        return result

    def hard_constraint_failures(self, candidate: dict[str, Any]) -> list[str]:
        failures = []
        for key, expected in self.declared.hard_constraints.items():
            actual = candidate.get(key)
            if isinstance(expected, (list, tuple, set)):
                if actual not in expected:
                    failures.append(f"{key}: {actual!r} not in {list(expected)!r}")
            elif actual != expected:
                failures.append(f"{key}: {actual!r} != {expected!r}")
        return failures

    def add_inferred_need(
        self,
        name: str,
        value: Any,
        *,
        confidence: float = 0.5,
        weight: float = 0.7,
        source: str = "",
        notes: str = "",
    ) -> None:
        self.latent.needs.append(Variable(
            name=name,
            value=value,
            confidence=confidence,
            weight=weight,
            evidence=EvidenceKind.INFERENCE,
            source=source,
            notes=notes,
        ))


class MatchSide(str, Enum):
    SEEKER = "seeker"
    SUPPLIER = "supplier"
    MEDIATOR = "mediator"


class PersonMessage(BaseModel):
    person_id: str
    side: MatchSide = MatchSide.SEEKER
    text: str
    intent: Literal["opinion", "preference", "critique", "request"] = "opinion"
    metadata: dict[str, Any] = Field(default_factory=dict)
