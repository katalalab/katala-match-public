from katala_match.core.anti_bubble import AntiBubbleConfig, select_with_diversity
from katala_match.core.choice_arch import Tapering, taper
from katala_match.core.pipeline import Candidate


def _c(cid: str, total: float, domain: str, discovery: float = 0.0) -> Candidate[dict]:
    return Candidate(
        id=cid,
        payload={},
        metadata={"score": {"total": total, "discovery": discovery}, "domain": domain},
    )


def test_domain_cap_blocks_a_single_source_from_filling_the_slate():
    scored = [_c(f"a{i}", 0.9 - i * 0.01, "agent-a") for i in range(6)]
    scored += [_c("b1", 0.5, "agent-b"), _c("b2", 0.49, "agent-b")]

    selected = select_with_diversity(scored, k=4)

    cap = max(1, int(4 * AntiBubbleConfig().domain_cap_ratio))
    from_a = [c for c in selected if c.metadata["domain"] == "agent-a"]
    assert len(from_a) <= cap
    assert any(c.metadata["domain"] == "agent-b" for c in selected)
    # The cap can leave the slate short of k rather than refilling from one source.
    assert len(selected) <= 4


def test_discovery_floor_swaps_in_a_high_discovery_candidate():
    scored = [_c(f"top{i}", 0.9 - i * 0.01, f"d{i}", discovery=0.0) for i in range(4)]
    scored.append(_c("hidden", 0.2, "d9", discovery=0.9))

    selected = select_with_diversity(scored, k=4)

    assert "hidden" in {c.id for c in selected}


def test_taper_narrows_candidates_layer_by_layer():
    candidates = list(range(50))
    tapering = Tapering()

    assert len(taper(candidates, 1, tapering)) == tapering.top
    assert len(taper(candidates, 2, tapering)) == tapering.compare
    assert len(taper(candidates, 4, tapering)) == tapering.final
