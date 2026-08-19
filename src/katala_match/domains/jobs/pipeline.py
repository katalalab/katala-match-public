"""Minimal jobs-domain pipeline to validate the shared core contract."""
from __future__ import annotations

from katala_match.core.pipeline import Pipeline
from katala_match.domains.common import (
    InMemorySource,
    NoopHydrator,
    RequiredFieldsGate,
    TopKSelector,
    WeightedFieldScorer,
)


DEMO_JOBS = [
    {"id": "job-1", "title": "AI product engineer", "skill_match": 0.9, "remote": True, "culture": 0.8, "discovery": 0.4, "risk": 0.1},
    {"id": "job-2", "title": "Legacy SI role", "skill_match": 0.6, "remote": False, "culture": 0.4, "discovery": 0.1, "risk": 0.5},
]


def build_demo_pipeline(items=None) -> Pipeline[dict]:
    return Pipeline(
        sources=[InMemorySource(items or DEMO_JOBS)],
        hydrators=[NoopHydrator()],
        gates=[RequiredFieldsGate(("title", "skill_match"))],
        scorer=WeightedFieldScorer({"skill_match": 0.5, "remote": 0.2, "culture": 0.3}),
        selector=TopKSelector(),
        side_effects=[],
    )
