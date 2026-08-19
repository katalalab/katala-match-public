"""Minimal dating-domain pipeline to validate the shared core contract."""
from __future__ import annotations

from katala_match.core.pipeline import Pipeline
from katala_match.domains.common import (
    InMemorySource,
    NoopHydrator,
    RequiredFieldsGate,
    TopKSelector,
    WeightedFieldScorer,
)


DEMO_MATCHES = [
    {"id": "date-1", "label": "values-first", "values_fit": 0.9, "lifestyle_fit": 0.8, "safety": 0.9, "discovery": 0.2, "risk": 0.1},
    {"id": "date-2", "label": "surface-spark", "values_fit": 0.4, "lifestyle_fit": 0.8, "safety": 0.5, "discovery": 0.6, "risk": 0.4},
]


def build_demo_pipeline(items=None) -> Pipeline[dict]:
    return Pipeline(
        sources=[InMemorySource(items or DEMO_MATCHES)],
        hydrators=[NoopHydrator()],
        gates=[RequiredFieldsGate(("label", "values_fit", "safety"))],
        scorer=WeightedFieldScorer({"values_fit": 0.45, "lifestyle_fit": 0.25, "safety": 0.3}),
        selector=TopKSelector(),
        side_effects=[],
    )
