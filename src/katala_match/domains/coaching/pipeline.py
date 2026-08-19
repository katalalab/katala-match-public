"""Minimal coaching-domain pipeline to validate the shared core contract."""
from __future__ import annotations

from katala_match.core.pipeline import Pipeline
from katala_match.domains.common import (
    InMemorySource,
    NoopHydrator,
    RequiredFieldsGate,
    TopKSelector,
    WeightedFieldScorer,
)


DEMO_COACHES = [
    {"id": "coach-1", "name": "systems coach", "method_fit": 0.85, "availability": 0.7, "safety": 0.9, "discovery": 0.3, "risk": 0.1},
    {"id": "coach-2", "name": "high-pressure coach", "method_fit": 0.7, "availability": 0.9, "safety": 0.2, "discovery": 0.2, "risk": 0.6},
]


def build_demo_pipeline(items=None) -> Pipeline[dict]:
    return Pipeline(
        sources=[InMemorySource(items or DEMO_COACHES)],
        hydrators=[NoopHydrator()],
        gates=[RequiredFieldsGate(("name", "method_fit", "safety"))],
        scorer=WeightedFieldScorer({"method_fit": 0.45, "availability": 0.2, "safety": 0.35}),
        selector=TopKSelector(),
        side_effects=[],
    )
