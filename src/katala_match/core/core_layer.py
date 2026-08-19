"""Core layer: bifurcation map, observability, and dialetheia (contradiction) holding.

Design contract (from MEMORY):
- Window-invariant: fields within a snapshot window do not mutate.
- Cross-window-mutable: BifurcationMap nodes may be promoted between windows.
- Contradiction is held, not resolved: DialetheiaEntry keeps both horns.
- Observability is structural: ObservabilityReport is derived, never estimated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .person_model import PersonModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CreativityMode(str, Enum):
    """Controls how BifurcationMap explores branches."""

    CONSERVATIVE = "conservative"  # Stay close to stated preferences.
    EXPLORATORY = "exploratory"  # Generate distant but coherent alternatives.
    DIALECTIC = "dialectic"  # Surface contradictions as generative force.


class CorePole(str, Enum):
    """The two irreducible poles of a person's core tension."""

    KNOWN = "known"  # What the person already believes/needs.
    UNKNOWN = "unknown"  # What the person is moving toward but cannot name.


# ---------------------------------------------------------------------------
# Bifurcation graph
# ---------------------------------------------------------------------------


class BifurcationPoint(BaseModel):
    """A decision node where a person's possibility space forks."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    label: str
    question: str
    left_branch: str = ""  # Branch label if person chooses left.
    right_branch: str = ""  # Branch label if person chooses right.
    weight: float = Field(default=1.0, ge=0.0, le=2.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AttractorNode(BaseModel):
    """A stable state that the person tends to converge on."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    label: str
    pole: CorePole = CorePole.KNOWN
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class PhiEdge(BaseModel):
    """Weighted edge between two nodes representing integrated information flow."""

    model_config = ConfigDict(frozen=True)

    source_id: str
    target_id: str
    phi: float = Field(default=0.0, ge=0.0)  # Integrated-information proxy.
    label: str = ""


class BifurcationMap(BaseModel):
    """Directed graph of bifurcation points and attractor nodes for one person.

    Intentionally mutable: callers use add_* methods to build the map before
    assigning it to a CoreLayer. Once assigned, treat as append-only within
    the window. Cross-window updates must go through rebuild_core().
    """

    person_id: str
    bifurcation_points: list[BifurcationPoint] = Field(default_factory=list)
    attractors: list[AttractorNode] = Field(default_factory=list)
    edges: list[PhiEdge] = Field(default_factory=list)
    window_id: str = "w0"

    def add_bifurcation(self, point: BifurcationPoint) -> None:
        self.bifurcation_points.append(point)

    def add_attractor(self, node: AttractorNode) -> None:
        self.attractors.append(node)

    def add_edge(self, edge: PhiEdge) -> None:
        self.edges.append(edge)

    def dominant_pole(self) -> CorePole:
        """Return the pole with higher mean attractor strength."""
        known = [a.strength for a in self.attractors if a.pole == CorePole.KNOWN]
        unknown = [a.strength for a in self.attractors if a.pole == CorePole.UNKNOWN]
        known_mean = sum(known) / len(known) if known else 0.0
        unknown_mean = sum(unknown) / len(unknown) if unknown else 0.0
        return CorePole.KNOWN if known_mean >= unknown_mean else CorePole.UNKNOWN


# ---------------------------------------------------------------------------
# Dialetheia: contradiction holding
# ---------------------------------------------------------------------------


class DialetheiaEntry(BaseModel):
    """Hold two contradictory beliefs without forcing resolution.

    A dialetheia is a pair of propositions (p, not-p) that are both accepted
    as operationally true within the person's model. The tension is kept live
    rather than collapsed into a single dominant belief.
    """

    entry_id: str
    thesis: str  # The first horn: what the person believes.
    antithesis: str  # The second horn: the contradictory belief.
    resolution: str = ""  # If empty, contradiction is unresolved (held).
    salience: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return bool(self.resolution.strip())


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


class ObservabilityReport(BaseModel):
    """Structural summary of what is visible in a CoreLayer snapshot."""

    person_id: str
    window_id: str
    n_variables: int = 0
    n_bifurcations: int = 0
    n_attractors: int = 0
    n_dialetheias: int = 0
    n_unresolved_dialetheias: int = 0
    dominant_pole: CorePole = CorePole.KNOWN
    coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CoreLayer
# ---------------------------------------------------------------------------


@dataclass
class CoreLayer:
    """Person's core: bifurcation map + dialetheia store + observability.

    Window invariant: once built, fields are not mutated within a window.
    Cross-window mutation is handled by rebuild_core().

    Note: CoreLayer is a @dataclass (not a Pydantic BaseModel) because it
    holds a PersonModel alongside BifurcationMap. This means .model_dump()
    and .model_validate() are NOT available on CoreLayer itself. Custom
    serialization is required if JSON round-trip is needed.
    """

    person: PersonModel
    bmap: BifurcationMap = field(default_factory=lambda: BifurcationMap(person_id=""))
    dialetheias: list[DialetheiaEntry] = field(default_factory=list)
    mode: CreativityMode = CreativityMode.CONSERVATIVE
    window_id: str = "w0"

    def __post_init__(self) -> None:
        if not self.bmap.person_id:
            self.bmap = BifurcationMap(
                person_id=self.person.person_id, window_id=self.window_id
            )

    def add_dialetheia(self, entry: DialetheiaEntry) -> None:
        self.dialetheias.append(entry)

    def observability(self) -> ObservabilityReport:
        unresolved = [d for d in self.dialetheias if not d.is_resolved]
        n_vars = len(self.person.variable_map())
        n_bi = len(self.bmap.bifurcation_points)
        n_att = len(self.bmap.attractors)
        n_dia = len(self.dialetheias)
        n_unres = len(unresolved)
        # Coverage: fraction of variables that have bifurcation or attractor coverage.
        covered_labels = {a.label for a in self.bmap.attractors}
        covered_labels |= {p.label for p in self.bmap.bifurcation_points}
        var_names = set(self.person.variable_map().keys())
        coverage = (
            len(var_names & covered_labels) / len(var_names) if var_names else 0.0
        )
        return ObservabilityReport(
            person_id=self.person.person_id,
            window_id=self.window_id,
            n_variables=n_vars,
            n_bifurcations=n_bi,
            n_attractors=n_att,
            n_dialetheias=n_dia,
            n_unresolved_dialetheias=n_unres,
            dominant_pole=self.bmap.dominant_pole(),
            coverage_score=round(coverage, 4),
        )


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def score_candidate_with_core(
    core: CoreLayer,
    candidate: dict[str, Any],
    *,
    boost_unknown_pole: float = 0.1,
) -> float:
    """Score a candidate dict against a CoreLayer.

    Returns a float in [0, 1]. Hard-constraint failures return 0.0.
    Unknown-pole attractor gives a small boost when mode is EXPLORATORY/DIALECTIC.
    """
    person = core.person
    failures = person.hard_constraint_failures(candidate)
    if failures:
        return 0.0

    var_map = person.variable_map()
    if not var_map:
        base = 0.5
    else:
        scores = []
        for name, var in var_map.items():
            cval = candidate.get(name)
            if cval is None:
                scores.append(0.0)
            elif cval == var.value:
                scores.append(var.weighted_confidence())
            else:
                scores.append(var.weighted_confidence() * 0.3)
        base = sum(scores) / len(scores)

    pole = core.bmap.dominant_pole()
    if pole == CorePole.UNKNOWN and core.mode in (
        CreativityMode.EXPLORATORY,
        CreativityMode.DIALECTIC,
    ):
        base = min(1.0, base + boost_unknown_pole)

    return round(base, 4)


# ---------------------------------------------------------------------------
# Promotion decision
# ---------------------------------------------------------------------------


def promotion_decision(
    core: CoreLayer,
    candidate: dict[str, Any],
    *,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Decide whether to promote a candidate, given core scoring.

    Returns a dict with keys: promote (bool), score (float), reason (str).
    """
    score = score_candidate_with_core(core, candidate)
    promote = score >= threshold
    reason = f"score={score:.3f} {'≥' if promote else '<'} threshold={threshold:.3f}"
    return {"promote": promote, "score": score, "reason": reason}


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def build_core_layer(
    person: PersonModel,
    *,
    mode: CreativityMode = CreativityMode.CONSERVATIVE,
    window_id: str = "w0",
    bifurcations: Sequence[BifurcationPoint] | None = None,
    attractors: Sequence[AttractorNode] | None = None,
    dialetheias: Sequence[DialetheiaEntry] | None = None,
) -> CoreLayer:
    """Construct a CoreLayer from a PersonModel with optional initial graph."""
    bmap = BifurcationMap(person_id=person.person_id, window_id=window_id)
    for bp in bifurcations or []:
        bmap.add_bifurcation(bp)
    for att in attractors or []:
        bmap.add_attractor(att)
    core = CoreLayer(
        person=person,
        bmap=bmap,
        mode=mode,
        window_id=window_id,
    )
    for dia in dialetheias or []:
        core.add_dialetheia(dia)
    return core


def rebuild_core(
    core: CoreLayer,
    *,
    new_window_id: str,
    additional_bifurcations: Sequence[BifurcationPoint] | None = None,
    additional_attractors: Sequence[AttractorNode] | None = None,
    additional_dialetheias: Sequence[DialetheiaEntry] | None = None,
    mode: CreativityMode | None = None,
) -> CoreLayer:
    """Produce a new CoreLayer in a new window, carrying forward existing state.

    Cross-window-mutable: the new layer starts from the previous state and
    extends it. The old CoreLayer remains unchanged (window-invariant).
    """
    new_bmap = BifurcationMap(
        person_id=core.person.person_id,
        bifurcation_points=[
            bp.model_copy(deep=True) for bp in core.bmap.bifurcation_points
        ],
        attractors=[a.model_copy(deep=True) for a in core.bmap.attractors],
        edges=[e.model_copy(deep=True) for e in core.bmap.edges],
        window_id=new_window_id,
    )
    for bp in additional_bifurcations or []:
        new_bmap.add_bifurcation(bp)
    for att in additional_attractors or []:
        new_bmap.add_attractor(att)
    new_core = CoreLayer(
        person=core.person.model_copy(deep=True),
        bmap=new_bmap,
        dialetheias=list(core.dialetheias),
        mode=mode if mode is not None else core.mode,
        window_id=new_window_id,
    )
    for dia in additional_dialetheias or []:
        new_core.add_dialetheia(dia)
    return new_core
