"""Jobs adapter that reuses the Katala mediation shape."""
from __future__ import annotations

from typing import Any

from katala_match.core.match_context import MatchContext
from katala_match.core.mediator import CandidateStatement, KatalaMediator, MediationResult
from katala_match.core.person_model import PersonMessage, PersonModel

from .false_negative import FalseNegativeRescueResult, evaluate_false_negative_rescue


def match_context_for_role(role: dict[str, Any], person: PersonModel) -> MatchContext:
    return MatchContext(
        domain="jobs",
        candidate_id=str(role["id"]),
        candidate_label=role.get("title", ""),
        candidate_payload=role,
        people=[person],
        messages=[
            PersonMessage(
                person_id=person.person_id,
                text="; ".join(person.declared.goals + person.context.power_constraints),
                intent="preference",
            )
        ],
        shared_context={"case": "screening_false_negative_rescue"},
    )


def candidate_statement_for_role(role: dict[str, Any], rescue: FalseNegativeRescueResult) -> CandidateStatement:
    average_gaps = ", ".join(rescue.missing_average_signals) or "none"
    unique_matches = ", ".join(rescue.matched_unique_variables) or "none"
    text = (
        f"{role.get('title', role['id'])} は平均シグナル({average_gaps})では落ちやすい。"
        f" ただし職務ニーズと固有変数({unique_matches})が一致するため、"
        f"{'救済候補として再評価する' if rescue.rescued else '追加証拠が必要'}。"
    )
    return CandidateStatement(
        text=text,
        covered_variables=rescue.matched_role_needs,
        unresolved_variables=rescue.missing_average_signals,
        source="jobs_false_negative_adapter",
    )


def mediate_false_negative_role(
    role: dict[str, Any],
    person: PersonModel,
    *,
    mediator: KatalaMediator | None = None,
) -> dict[str, Any]:
    rescue = evaluate_false_negative_rescue(role, person)
    context = match_context_for_role(role, person)
    candidate = candidate_statement_for_role(role, rescue)
    result: MediationResult = (mediator or KatalaMediator(loss_threshold=0.35)).mediate(
        "平均シグナルで落ちる候補を固有変数で救済すべきか",
        [person],
        context.messages,
        [candidate],
        context=context.shared_context,
    )
    return {
        "role_id": str(role["id"]),
        "title": role.get("title", ""),
        "baseline_rejected": rescue.baseline_rejected,
        "rescued": rescue.rescued,
        "missing_average_signals": ", ".join(rescue.missing_average_signals),
        "matched_unique_variables": ", ".join(rescue.matched_unique_variables),
        "matched_role_needs": ", ".join(rescue.matched_role_needs),
        "mediator_winner": result.winner.text,
        "mediator_score": round(sum(r.score for r in result.rankings) / max(1, len(result.rankings)), 3),
        "next_questions": "\n".join(result.next_questions) or "固有変数を示す成果物・面談質問で再確認する。",
        "context_domain": context.domain,
        "context_candidate_id": context.candidate_id,
    }
