"""Jobs domain: role/candidate matching."""

from .false_negative import (
    FalseNegativeRescueResult,
    evaluate_false_negative_rescue,
    screening_false_negative_person,
)
from .mediator_adapter import (
    candidate_statement_for_role,
    match_context_for_role,
    mediate_false_negative_role,
)
from .pipeline import build_demo_pipeline

__all__ = [
    "FalseNegativeRescueResult",
    "build_demo_pipeline",
    "candidate_statement_for_role",
    "evaluate_false_negative_rescue",
    "match_context_for_role",
    "mediate_false_negative_role",
    "screening_false_negative_person",
]
