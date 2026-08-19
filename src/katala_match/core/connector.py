"""Connection discovery for people, knowledge, ideas, and experiences.

Connector creates testable connection hypotheses. It is deliberately
deterministic in v0: LLMs can explain or enrich candidates later, but the base
score should be inspectable and testable.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Iterable

from pydantic import BaseModel, Field

from .person_model import PersonModel


class ConnectorNodeKind(str, Enum):
    PERSON = "person"
    KNOWLEDGE = "knowledge"
    IDEA = "idea"
    EXPERIENCE = "experience"
    QUESTION = "question"
    PROJECT = "project"
    ACTION = "action"


class ConnectorAxis(str, Enum):
    PSYCHOLOGICAL = "psychological"
    BIOLOGICAL = "biological_ecological"
    COGNITIVE = "cognitive"
    SOCIAL_NETWORK = "social_network"
    INFORMATION = "information_theory"
    CREATIVITY = "creativity"
    SOCIOLOGICAL = "sociological_anthropological"
    PRACTICAL = "design_practice"


class ConnectorNode(BaseModel):
    """A node that can participate in a connection hypothesis."""

    id: str
    kind: ConnectorNodeKind
    label: str
    themes: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    offers: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)

    def tokens(self) -> set[str]:
        return _norm_set(self.themes + self.variables + self.needs + self.offers + self.contexts)


class ConnectionAxisScore(BaseModel):
    axis: ConnectorAxis
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    risk: str = ""
    next_probe: str = ""
    source_theory: str = ""


class ConnectionScore(BaseModel):
    need_fit: float = Field(ge=0.0, le=1.0)
    complementarity: float = Field(ge=0.0, le=1.0)
    translation_potential: float = Field(ge=0.0, le=1.0)
    timing_fit: float = Field(ge=0.0, le=1.0)
    trust_path: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    synergy_gain: float = Field(ge=0.0, le=1.0)
    translation_loss: float = Field(ge=0.0, le=1.0)
    activation_cost: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)

    def total(self) -> float:
        positive = (
            self.need_fit * 0.20
            + self.complementarity * 0.15
            + self.translation_potential * 0.15
            + self.timing_fit * 0.10
            + self.trust_path * 0.05
            + self.novelty * 0.10
            + self.synergy_gain * 0.20
        )
        penalty = (
            self.translation_loss * 0.15
            + self.activation_cost * 0.10
            + self.risk * 0.20
        )
        return round(max(0.0, min(1.0, positive - penalty)), 3)


class ConnectionCandidate(BaseModel):
    source_id: str
    target_id: str
    connection_type: str
    shared_variables: list[str] = Field(default_factory=list)
    complementary_variables: list[str] = Field(default_factory=list)
    axis_scores: list[ConnectionAxisScore] = Field(default_factory=list)
    score: ConnectionScore
    rationale: str
    next_action: str
    safety_notes: list[str] = Field(default_factory=list)

    @property
    def total_score(self) -> float:
        return self.score.total()

    def axis_map(self) -> dict[ConnectorAxis, ConnectionAxisScore]:
        return {axis_score.axis: axis_score for axis_score in self.axis_scores}


class KatalaConnector:
    """Deterministic connection hypothesis generator."""

    def evaluate(
        self,
        source: ConnectorNode,
        target: ConnectorNode,
        *,
        context: dict[str, Any] | None = None,
    ) -> ConnectionCandidate:
        context = context or {}
        shared = sorted(_norm_set(source.variables + source.themes).intersection(target.tokens()))
        forward = sorted(_norm_set(source.needs).intersection(_norm_set(target.offers + target.variables)))
        reverse = sorted(_norm_set(target.needs).intersection(_norm_set(source.offers + source.variables)))
        complementary = sorted(set(forward + reverse))

        context_tokens = _norm_set(context.get("contexts", []) + context.get("themes", []))
        timing_hits = sorted(_norm_set(source.contexts + target.contexts).intersection(context_tokens))
        if not timing_hits:
            timing_hits = sorted(_norm_set(source.contexts).intersection(_norm_set(target.contexts)))

        source_need_count = max(1, len(_norm_set(source.needs)))
        target_need_count = max(1, len(_norm_set(target.needs)))
        need_fit = _clamp(len(forward) / source_need_count)
        reverse_fit = _clamp(len(reverse) / target_need_count)
        complementarity = _clamp((len(forward) + len(reverse)) / max(1, source_need_count + target_need_count))

        overlap = _jaccard(source.tokens(), target.tokens())
        novelty = _clamp(1.0 - overlap)
        bridge = _clamp((len(shared) + len(complementary)) / 8)
        translation_potential = _clamp(0.35 + bridge * 0.65)
        timing_fit = 0.75 if timing_hits else 0.45
        trust_path = _trust_path(source, target, context)
        activation_cost = _activation_cost(source, target, context)
        risk = _risk(source, target, context)
        translation_loss = _clamp(0.75 - translation_potential * 0.55 + risk * 0.25)
        synergy_gain = _clamp((complementarity * 0.45) + (novelty * 0.25) + (bridge * 0.30))

        score = ConnectionScore(
            need_fit=round(max(need_fit, reverse_fit * 0.5), 3),
            complementarity=round(complementarity, 3),
            translation_potential=round(translation_potential, 3),
            timing_fit=round(timing_fit, 3),
            trust_path=round(trust_path, 3),
            novelty=round(novelty, 3),
            synergy_gain=round(synergy_gain, 3),
            translation_loss=round(translation_loss, 3),
            activation_cost=round(activation_cost, 3),
            risk=round(risk, 3),
        )
        axis_scores = self._axis_scores(source, target, shared, complementary, timing_hits, score)
        safety_notes = _safety_notes(source, target, score)
        return ConnectionCandidate(
            source_id=source.id,
            target_id=target.id,
            connection_type=f"{source.kind.value}_to_{target.kind.value}",
            shared_variables=shared,
            complementary_variables=complementary,
            axis_scores=axis_scores,
            score=score,
            rationale=_rationale(source, target, shared, complementary, score),
            next_action=_next_action(source, target, complementary, score),
            safety_notes=safety_notes,
        )

    def rank(
        self,
        source: ConnectorNode,
        targets: Iterable[ConnectorNode],
        *,
        context: dict[str, Any] | None = None,
    ) -> list[ConnectionCandidate]:
        candidates = [self.evaluate(source, target, context=context) for target in targets]
        return self.select(candidates)

    def select(self, candidates: Iterable[ConnectionCandidate], k: int | None = None) -> list[ConnectionCandidate]:
        ranked = sorted(candidates, key=lambda c: (c.total_score, c.score.novelty), reverse=True)
        return ranked if k is None else ranked[:k]

    def _axis_scores(
        self,
        source: ConnectorNode,
        target: ConnectorNode,
        shared: list[str],
        complementary: list[str],
        timing_hits: list[str],
        score: ConnectionScore,
    ) -> list[ConnectionAxisScore]:
        shared_or_comp = shared + complementary
        return [
            ConnectionAxisScore(
                axis=ConnectorAxis.PSYCHOLOGICAL,
                score=round(_clamp(score.need_fit * 0.6 + (1 - score.activation_cost) * 0.4), 3),
                evidence=shared_or_comp[:4],
                risk="cognitive load or identity resistance" if score.activation_cost > 0.55 else "",
                next_probe="Ask whether the proposed bridge feels energizing or heavy.",
                source_theory="motivation, cognitive load, self-efficacy",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.BIOLOGICAL,
                score=round(_clamp(score.timing_fit * 0.4 + score.complementarity * 0.4 + score.novelty * 0.2), 3),
                evidence=timing_hits + complementary[:3],
                risk="energy cost exceeds adaptive gain" if score.activation_cost > 0.6 else "",
                next_probe="Find the smallest low-energy experiment for this connection.",
                source_theory="niche fit, mutualism, exploration/exploitation",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.COGNITIVE,
                score=round(_clamp(score.translation_potential * 0.7 + (1 - score.translation_loss) * 0.3), 3),
                evidence=shared[:4],
                risk="schema mismatch" if score.translation_loss > 0.6 else "",
                next_probe="Name the analogy and the part that does not transfer.",
                source_theory="analogy, schema bridge, conceptual combination",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.SOCIAL_NETWORK,
                score=round(_clamp(score.trust_path * 0.3 + score.novelty * 0.3 + score.complementarity * 0.4), 3),
                evidence=shared_or_comp[:4],
                risk="burden asymmetry or weak consent path" if score.risk > 0.55 else "",
                next_probe="Keep this as knowledge bridge unless both sides opt in.",
                source_theory="weak ties, structural holes, brokerage",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.INFORMATION,
                score=round(_clamp(score.translation_potential * 0.6 + (1 - score.translation_loss) * 0.4), 3),
                evidence=shared[:3] + complementary[:3],
                risk="noise or lossy translation" if score.translation_loss > 0.55 else "",
                next_probe="Compress the bridge into one sentence and one counterexample.",
                source_theory="signal/noise, compression, entropy, translation loss",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.CREATIVITY,
                score=round(_clamp(score.novelty * 0.35 + score.synergy_gain * 0.45 + (1 - score.risk) * 0.2), 3),
                evidence=shared_or_comp[:5],
                risk="novel but fragile" if score.risk > 0.45 else "",
                next_probe="Test whether the bridge creates a new action or structure.",
                source_theory="remote association, meaningful distance, structural gain",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.SOCIOLOGICAL,
                score=round(_clamp(score.trust_path * 0.6 + (1 - score.risk) * 0.4), 3),
                evidence=source.contexts[:2] + target.contexts[:2],
                risk="role, norm, privacy, or power mismatch" if score.risk > 0.5 else "",
                next_probe="State consent, burden, and refusal path before introducing people.",
                source_theory="role, norm, power, relational capital",
            ),
            ConnectionAxisScore(
                axis=ConnectorAxis.PRACTICAL,
                score=round(_clamp((1 - score.activation_cost) * 0.55 + score.need_fit * 0.25 + score.timing_fit * 0.2), 3),
                evidence=complementary[:4] or shared[:4],
                risk="too vague or expensive to try" if score.activation_cost > 0.6 else "",
                next_probe="Turn the connection into a 30-minute artifact or test.",
                source_theory="affordance, prototypeability, adoption cost",
            ),
        ]


def node_from_person(person: PersonModel) -> ConnectorNode:
    variables = sorted(person.variable_map().keys())
    needs = [var.name for var in person.latent.needs] + person.declared.goals
    constraints = list(person.declared.hard_constraints.keys()) + person.context.safety_constraints
    return ConnectorNode(
        id=person.person_id,
        kind=ConnectorNodeKind.PERSON,
        label=person.label or person.person_id,
        themes=[person.domain],
        variables=variables,
        needs=needs,
        offers=[var.name for var in person.latent.unique_strengths],
        constraints=constraints,
        contexts=person.context.roles + [person.context.time_horizon] if person.context.time_horizon else person.context.roles,
        evidence={"source": "PersonModel"},
    )


def _norm_set(values: Iterable[Any]) -> set[str]:
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a.intersection(b)) / len(a.union(b))


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _trust_path(source: ConnectorNode, target: ConnectorNode, context: dict[str, Any]) -> float:
    trusted = _norm_set(context.get("trusted_sources", []))
    target_sources = _norm_set(target.evidence.values())
    if target_sources.intersection(trusted):
        return 0.8
    if target.kind in {ConnectorNodeKind.KNOWLEDGE, ConnectorNodeKind.IDEA, ConnectorNodeKind.EXPERIENCE}:
        return 0.6
    if source.kind == ConnectorNodeKind.PERSON and target.kind == ConnectorNodeKind.PERSON:
        return 0.35
    return 0.5


def _activation_cost(source: ConnectorNode, target: ConnectorNode, context: dict[str, Any]) -> float:
    base = 0.35
    if target.kind == ConnectorNodeKind.PERSON:
        base += 0.25
    if len(target.constraints) > 3:
        base += 0.15
    if "quick_test" in _norm_set(context.get("preferred_actions", [])):
        base -= 0.15
    if _norm_set(source.contexts).intersection(_norm_set(target.contexts)):
        base -= 0.05
    return _clamp(base)


def _risk(source: ConnectorNode, target: ConnectorNode, context: dict[str, Any]) -> float:
    base = 0.2
    if source.kind == ConnectorNodeKind.PERSON and target.kind == ConnectorNodeKind.PERSON:
        base += 0.35
    if target.kind == ConnectorNodeKind.PERSON and "consent_path" not in context:
        base += 0.2
    sensitive = {"privacy", "health", "family", "money", "career"}
    if _norm_set(source.constraints + target.constraints).intersection(sensitive):
        base += 0.15
    return _clamp(base)


def _rationale(
    source: ConnectorNode,
    target: ConnectorNode,
    shared: list[str],
    complementary: list[str],
    score: ConnectionScore,
) -> str:
    bridge = ", ".join(complementary or shared or ["context"])
    return (
        f"{source.label} can be connected to {target.label} through {bridge}. "
        f"The edge is worth testing because total={score.total():.3f}, "
        f"synergy={score.synergy_gain:.3f}, translation_loss={score.translation_loss:.3f}."
    )


def _next_action(
    source: ConnectorNode,
    target: ConnectorNode,
    complementary: list[str],
    score: ConnectionScore,
) -> str:
    if score.risk >= 0.75:
        return "Do not introduce directly; first ask a clarifying or consent question."
    if score.translation_loss >= 0.75:
        return "Write a one-sentence bridge and one counterexample before acting."
    variable = complementary[0] if complementary else "shared variable"
    return f"Run a 30-minute artifact test: apply {target.label} to {variable} for {source.label}."


def _safety_notes(source: ConnectorNode, target: ConnectorNode, score: ConnectionScore) -> list[str]:
    notes = []
    if source.kind == ConnectorNodeKind.PERSON and target.kind == ConnectorNodeKind.PERSON:
        notes.append("person_to_person requires consent, burden, and refusal path")
    if score.risk >= 0.6:
        notes.append("high risk: prefer knowledge bridge or question before recommendation")
    if score.translation_loss >= 0.65:
        notes.append("translation loss: add analogy, counterexample, and clarifying question")
    if score.activation_cost >= 0.65:
        notes.append("activation cost: shrink next action")
    return notes

