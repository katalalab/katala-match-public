"""Person-aware match context shared by domain adapters."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .person_model import PersonMessage, PersonModel


class MatchContext(BaseModel):
    """A single mediation unit: people + candidate + domain context."""

    domain: str
    candidate_id: str
    candidate_label: str = ""
    candidate_payload: dict[str, Any] = Field(default_factory=dict)
    people: list[PersonModel] = Field(default_factory=list)
    messages: list[PersonMessage] = Field(default_factory=list)
    shared_context: dict[str, Any] = Field(default_factory=dict)

    def compact_candidate(self) -> dict[str, Any]:
        keys = [
            "id", "name", "building_name", "layout", "rent_man", "size_m2",
            "year", "access", "futako_min", "shibuya_min", "structure",
            "total_floors", "my_floor", "address",
        ]
        return {key: self.candidate_payload.get(key) for key in keys if key in self.candidate_payload}

    def all_variable_names(self) -> list[str]:
        names = []
        for person in self.people:
            names.extend(person.variable_map().keys())
        return sorted(set(names))
