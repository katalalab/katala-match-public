from __future__ import annotations

from datetime import datetime, timezone

from katala_match.core import (
    TRUST_SIGNAL_CLAIM_STATE,
    TRUST_SIGNAL_PUBLIC_COMMIT_GATE,
    TRUST_SIGNAL_SCHEMA_VERSION,
    TrustGate,
    research_bundle_to_trust_signals,
)


NOW = datetime(2026, 6, 10, tzinfo=timezone.utc)


def sample_research_bundle() -> dict:
    return {
        "schema_version": "katala.research_bundle.v0.1",
        "source_system": "katala-web-research",
        "source_command": "kwr investigate --json",
        "query": "anti-filter-bubble",
        "claim_state": "hypothesis_only_no_truth_promotion",
        "public_commit_gate": "evidence_bundle_not_proof",
        "record_counts": {
            "web_results": 1,
            "repo_hits": 1,
            "feed_hits": 1,
            "pages": 1,
            "total_records": 4,
        },
        "records": [
            {
                "id": "kwr-web-001",
                "kind": "web_result",
                "title": "Official docs",
                "url": "https://example.org/docs",
                "source_type": "official",
                "provenance_tier": "external_candidate",
                "quality_score": 95,
                "published_at": "2026-06-09",
            },
            {
                "id": "kwr-repo-001",
                "kind": "repo_document",
                "title": "Katala Research v0",
                "url": "repo://example-research/README.md",
                "source_type": "local_repository",
                "provenance_tier": "local_repo",
                "captured_at": "2026-06-10T00:00:00+00:00",
                "metadata": {"repo_path": "/repos/example-research", "rel_path": "README.md"},
            },
            {
                "id": "kwr-feed-001",
                "kind": "feed_item",
                "title": "Feed item",
                "url": "https://example.org/feed/item",
                "source_type": "archived_feed",
                "provenance_tier": "archived_feed",
                "published_at": "2026-06-09",
            },
            {
                "id": "kwr-page-001",
                "kind": "page_snapshot",
                "title": "Captured official docs",
                "url": "https://example.org/docs",
                "source_type": "text/html",
                "provenance_tier": "captured_page",
                "captured_at": "2026-06-10T00:00:00+00:00",
            },
        ],
        "search_plan": [{"query": "anti-filter-bubble", "rationale": "direct"}],
        "open_questions": [],
    }


def test_research_bundle_to_trust_signals_preserves_no_truth_promotion() -> None:
    bundle = research_bundle_to_trust_signals(
        sample_research_bundle(),
        subject="example-research",
        claim="KWR evidence supports anti-filter-bubble synthesis",
        now=NOW,
    )

    assert bundle.schema_version == TRUST_SIGNAL_SCHEMA_VERSION
    assert bundle.claim_state == TRUST_SIGNAL_CLAIM_STATE
    assert bundle.public_commit_gate == TRUST_SIGNAL_PUBLIC_COMMIT_GATE
    assert bundle.source_bundle_schema == "katala.research_bundle.v0.1"
    assert bundle.record_counts["total_records"] == 4
    assert len(bundle.signals) == 1

    signal = bundle.signals[0]
    assert signal.claim_state == TRUST_SIGNAL_CLAIM_STATE
    assert signal.recommended_gate == TrustGate.ALLOW_HYPOTHESIS
    assert signal.verification_state == "captured_evidence"
    assert signal.aggregate_trust_score > 0.75
    assert set(signal.evidence_kinds) == {"feed_item", "page_snapshot", "repo_document", "web_result"}
    assert "kwr-page-001" in signal.source_record_ids


def test_research_bundle_to_trust_signals_holds_empty_bundle() -> None:
    bundle = research_bundle_to_trust_signals(
        {
            "schema_version": "katala.research_bundle.v0.1",
            "records": [],
            "record_counts": {"total_records": 0},
            "open_questions": [],
        },
        claim="empty evidence cannot support a public claim",
        now=NOW,
    )

    signal = bundle.signals[0]
    assert signal.verification_state == "insufficient_evidence"
    assert signal.recommended_gate == TrustGate.CLARIFY_OR_ABSTAIN
    assert signal.aggregate_trust_score == 0
    assert "no_evidence" in signal.risk_flags
    assert any("Populate evidence records" in question for question in bundle.open_questions)


def test_research_bundle_to_trust_signals_keeps_local_only_partial() -> None:
    bundle = research_bundle_to_trust_signals(
        {
            "schema_version": "katala.research_bundle.v0.1",
            "records": [
                {
                    "id": "kwr-repo-001",
                    "kind": "repo_document",
                    "title": "Local README",
                    "url": "repo://example-research/README.md",
                    "source_type": "local_repository",
                    "provenance_tier": "local_repo",
                    "captured_at": "2026-06-10T00:00:00+00:00",
                }
            ],
            "record_counts": {"repo_hits": 1, "total_records": 1},
            "open_questions": ["Which official source should corroborate this local repository evidence?"],
        },
        subject="example-research",
        claim="local evidence is enough",
        now=NOW,
    )

    signal = bundle.signals[0]
    assert signal.verification_state == "local_only"
    assert signal.recommended_gate == TrustGate.PARTIAL_COMMIT_WITH_VISIBLE_UNCERTAINTY
    assert "local_only_evidence" in signal.risk_flags
    assert any("external" in question for question in bundle.open_questions)
