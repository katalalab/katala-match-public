"""False-negative rescue for jobs-domain variable matching."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from katala_match.core.person_model import EvidenceKind, PersonModel, Variable


AVERAGE_SIGNAL_FIELDS = ("degree", "years_experience", "company_tier", "keyword_score")


class FalseNegativeRescueResult(BaseModel):
    candidate_id: str
    baseline_rejected: bool
    rescued: bool
    missing_average_signals: list[str] = Field(default_factory=list)
    matched_unique_variables: list[str] = Field(default_factory=list)
    matched_role_needs: list[str] = Field(default_factory=list)
    explanation: str


def screening_false_negative_person() -> PersonModel:
    """A candidate who is weak on average signals but strong on rare variables."""
    person = PersonModel(person_id="screening-rejected-candidate", label="Screening false negative", domain="jobs")
    person.declared.goals.append("AIプロダクト/業務設計の現場で、曖昧な課題を構造化して前に進めたい")
    person.declared.preferences.update({
        "autonomy": True,
        "hands_on_ai_workflow": True,
        "cross_functional_discovery": True,
    })
    person.behavioral.rejected.append("credential_first_screen")
    person.latent.unique_strengths.extend([
        Variable(
            name="ambiguous_problem_structuring",
            value=True,
            weight=0.95,
            confidence=0.85,
            evidence=EvidenceKind.INFERENCE,
            source="project history",
        ),
        Variable(
            name="operator_empathy",
            value=True,
            weight=0.85,
            confidence=0.8,
            evidence=EvidenceKind.INFERENCE,
            source="field workflow artifacts",
        ),
        Variable(
            name="agentic_tooling_literacy",
            value=True,
            weight=0.9,
            confidence=0.8,
            evidence=EvidenceKind.INFERENCE,
            source="agent tooling artifacts",
        ),
    ])
    person.context.power_constraints.append("書類上の平均シグナルだけで評価されるとfalse negative化する")
    return person


def _missing_average_signal(candidate: dict[str, Any], field: str) -> bool:
    value = candidate.get(field)
    if value in (None, "", False):
        return True
    if field == "keyword_score":
        return float(value or 0) < 0.35
    if field == "years_experience":
        return float(value or 0) <= 0
    return False


def evaluate_false_negative_rescue(candidate: dict[str, Any], person: PersonModel) -> FalseNegativeRescueResult:
    """Rescue a profile when role variables match despite weak average signals."""
    missing = [field for field in AVERAGE_SIGNAL_FIELDS if _missing_average_signal(candidate, field)]
    baseline_rejected = len(missing) >= 2 or float(candidate.get("keyword_score", 0) or 0) < 0.35

    variables = person.variable_map()
    role_needs = set(candidate.get("role_needs", []))
    matched_unique = sorted([
        name for name, var in variables.items()
        if name in role_needs and var.value is True and var.weighted_confidence() >= 0.6
    ])
    matched_role_needs = sorted(role_needs.intersection(variables))
    rescued = baseline_rejected and len(matched_unique) >= 2
    explanation = (
        "平均シグナルでは落ちるが、職務が必要とする固有変数と候補者の強みが一致する。"
        if rescued else
        "平均シグナルの弱さを覆すだけの固有変数一致がまだ足りない。"
    )
    return FalseNegativeRescueResult(
        candidate_id=str(candidate["id"]),
        baseline_rejected=baseline_rejected,
        rescued=rescued,
        missing_average_signals=missing,
        matched_unique_variables=matched_unique,
        matched_role_needs=matched_role_needs,
        explanation=explanation,
    )
