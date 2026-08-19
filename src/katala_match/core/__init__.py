"""Shared core: pipeline / scoring / gates / selector / hearing / choice arch.

These are domain-agnostic primitives used by all `katala_match.domains.*`.
Person model / mediator / translation loss are the shared variable-matching
layer used across domains.
"""

from .mediator import CandidateStatement, KatalaMediator, MediationResult
from .match_context import MatchContext
from .person_model import EvidenceKind, PersonMessage, PersonModel, Variable
from .translation_loss import LossLevel, TranslationLossReport, estimate_translation_loss
from .domain_decision import DomainDecision, domain_decision_summary
from .trust_signal import (
    CLAIM_STATE as TRUST_SIGNAL_CLAIM_STATE,
    PUBLIC_COMMIT_GATE as TRUST_SIGNAL_PUBLIC_COMMIT_GATE,
    SCHEMA_VERSION as TRUST_SIGNAL_SCHEMA_VERSION,
    TrustGate,
    TrustSignal,
    TrustSignalBundle,
    research_bundle_to_trust_signal,
    research_bundle_to_trust_signals,
    trust_gate_penalty,
    trust_signal_summary,
)
from .connector import (
    ConnectionAxisScore,
    ConnectionCandidate,
    ConnectionScore,
    ConnectorAxis,
    ConnectorNode,
    ConnectorNodeKind,
    KatalaConnector,
    node_from_person,
)
from .core_layer import (
    AttractorNode,
    BifurcationMap,
    BifurcationPoint,
    CoreLayer,
    CorePole,
    CreativityMode,
    DialetheiaEntry,
    ObservabilityReport,
    PhiEdge,
    build_core_layer,
    promotion_decision,
    rebuild_core,
    score_candidate_with_core,
)

__all__ = [
    "AttractorNode",
    "BifurcationMap",
    "BifurcationPoint",
    "CandidateStatement",
    "ConnectionAxisScore",
    "ConnectionCandidate",
    "ConnectionScore",
    "ConnectorAxis",
    "ConnectorNode",
    "ConnectorNodeKind",
    "CoreLayer",
    "CorePole",
    "CreativityMode",
    "DialetheiaEntry",
    "DomainDecision",
    "EvidenceKind",
    "KatalaMediator",
    "KatalaConnector",
    "LossLevel",
    "MatchContext",
    "MediationResult",
    "ObservabilityReport",
    "PersonMessage",
    "PersonModel",
    "PhiEdge",
    "TRUST_SIGNAL_CLAIM_STATE",
    "TRUST_SIGNAL_PUBLIC_COMMIT_GATE",
    "TRUST_SIGNAL_SCHEMA_VERSION",
    "TranslationLossReport",
    "TrustGate",
    "TrustSignal",
    "TrustSignalBundle",
    "Variable",
    "build_core_layer",
    "estimate_translation_loss",
    "domain_decision_summary",
    "node_from_person",
    "promotion_decision",
    "research_bundle_to_trust_signal",
    "research_bundle_to_trust_signals",
    "rebuild_core",
    "score_candidate_with_core",
    "trust_gate_penalty",
    "trust_signal_summary",
]
