"""Katala mediator skeleton.

Habermas Machine generates candidate consensus statements and ranks them per
participant. Katala keeps that loop but replaces generic agreement with
person-model variable coverage and translation-loss reduction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from pydantic import BaseModel, Field

from .person_model import PersonMessage, PersonModel
from .translation_loss import TranslationLossReport, estimate_translation_loss


KATALA_MEDIATOR_PROMPT = """You are Katala Mediator.

Goal:
- Produce a candidate statement or match explanation that preserves each
  person's hard constraints, names the shared variable overlap, and identifies
  unresolved translation losses.

Rules:
- Do not average people into a generic majority preference.
- Separate explicit preferences from inferred needs.
- Translate criticism into observation, feeling, need, and request when possible.
- Keep minority hard constraints visible.
- Return: candidate statement, variable coverage, unresolved risks, next question.
"""


class CandidateStatement(BaseModel):
    text: str
    covered_variables: list[str] = Field(default_factory=list)
    unresolved_variables: list[str] = Field(default_factory=list)
    source: str = "katala"


class PersonRanking(BaseModel):
    person_id: str
    candidate_index: int
    score: float = Field(ge=0.0, le=1.0)
    coverage: float = Field(ge=0.0, le=1.0)
    loss: TranslationLossReport
    reasons: list[str] = Field(default_factory=list)


class MediationResult(BaseModel):
    question: str
    winner: CandidateStatement
    sorted_candidates: list[CandidateStatement]
    rankings: list[PersonRanking]
    next_questions: list[str] = Field(default_factory=list)


@dataclass
class KatalaMediator:
    """Deterministic mediation scaffold; LLM generation can plug in later."""

    loss_threshold: float = 0.45
    prompt_template: str = KATALA_MEDIATOR_PROMPT

    def draft_candidates(
        self,
        question: str,
        messages: Sequence[PersonMessage],
        people: Sequence[PersonModel],
    ) -> list[CandidateStatement]:
        variables = []
        hard_constraints = []
        for person in people:
            variables.extend(person.variable_map().keys())
            hard_constraints.extend(person.declared.hard_constraints.keys())
        top_variables = sorted(set(variables))[:8]
        hard = sorted(set(hard_constraints))
        opinion_refs = ", ".join(f"{m.person_id}:{m.intent}" for m in messages)
        base = (
            f"{question}について、{', '.join(top_variables) or '明示変数'}を軸に判断する。"
            f" hard constraints: {', '.join(hard) or 'none'}."
            f" inputs: {opinion_refs}."
        )
        return [
            CandidateStatement(
                text=base,
                covered_variables=top_variables,
                unresolved_variables=[],
                source="deterministic_variable_union",
            ),
            CandidateStatement(
                text=base + " 少数派の拒否条件を優先して、追加ヒアリング後に決定する。",
                covered_variables=top_variables + hard,
                unresolved_variables=["minority_constraints", "translation_loss"],
                source="deterministic_minority_safe",
            ),
        ]

    def rank_for_person(
        self,
        person: PersonModel,
        candidate: CandidateStatement,
        idx: int,
        *,
        context: dict | None = None,
    ) -> PersonRanking:
        var_map = person.variable_map()
        if not var_map:
            coverage = 0.0
        else:
            covered = set(candidate.covered_variables)
            coverage = len(covered.intersection(var_map.keys())) / len(var_map)
        loss = estimate_translation_loss(candidate.text, speaker=person, context=context)
        score = max(0.0, min(1.0, coverage * 0.7 + (1.0 - loss.overall) * 0.3))
        reasons = [
            f"coverage={coverage:.2f}",
            f"translation_loss={loss.overall:.2f}",
        ]
        return PersonRanking(
            person_id=person.person_id,
            candidate_index=idx,
            score=round(score, 3),
            coverage=round(coverage, 3),
            loss=loss,
            reasons=reasons,
        )

    def mediate(
        self,
        question: str,
        people: Sequence[PersonModel],
        messages: Sequence[PersonMessage],
        candidates: Sequence[CandidateStatement] | None = None,
        *,
        context: dict | None = None,
    ) -> MediationResult:
        candidate_list = list(candidates or self.draft_candidates(question, messages, people))
        rankings: list[PersonRanking] = []
        totals = [0.0 for _ in candidate_list]
        for idx, candidate in enumerate(candidate_list):
            for person in people:
                ranking = self.rank_for_person(person, candidate, idx, context=context)
                rankings.append(ranking)
                totals[idx] += ranking.score
        order = sorted(range(len(candidate_list)), key=lambda i: -totals[i])
        sorted_candidates = [candidate_list[i] for i in order]
        next_questions = self._next_questions(rankings, people)
        return MediationResult(
            question=question,
            winner=sorted_candidates[0],
            sorted_candidates=sorted_candidates,
            rankings=rankings,
            next_questions=next_questions,
        )

    def _next_questions(
        self,
        rankings: list[PersonRanking],
        people: Sequence[PersonModel],
    ) -> list[str]:
        questions = []
        high_loss_people = {
            r.person_id for r in rankings if r.loss.overall >= self.loss_threshold
        }
        people_by_id = {p.person_id: p for p in people}
        for person_id in sorted(high_loss_people):
            label = people_by_id[person_id].label or person_id
            questions.append(
                f"{label}: いまの表現で『違う』と感じる箇所を、観察・感情・必要・リクエストに分けて教えてください。"
            )
        return questions
