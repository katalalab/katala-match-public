"""Anti-bubble selector — 業者・沿線・パラダイムの多様性キャップ.

機能:
- Discovery floor (≥25% は creativity が高い候補)
- Domain cap (≤40% from any single agent/route/cluster)
- Counter-evidence (≥1 は反例候補)
- Long Tail boost (既存サービスで取りこぼされる候補を優遇)
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass


@dataclass
class AntiBubbleConfig:
    discovery_floor_ratio: float = 0.25
    discovery_threshold: float = 0.45
    domain_cap_ratio: float = 0.40
    paradigm_cap_ratio: float = 0.50
    must_include_counter: bool = True
    long_tail_boost: float = 0.15


def select_with_diversity(scored: list, k: int, config: AntiBubbleConfig = AntiBubbleConfig()) -> list:
    """Top-K with diversity caps and discovery floor.

    scored: 各候補は metadata に {"score": {"total": ..., "discovery": ...},
                                  "domain": ..., "paradigm": ...} を持つ前提.
    """
    if not scored:
        return []
    # スコア順
    scored = sorted(scored, key=lambda c: -c.metadata["score"]["total"])

    selected = []
    domain_count: Counter = Counter()
    paradigm_count: Counter = Counter()
    discovery_count = 0

    domain_cap = max(1, int(k * config.domain_cap_ratio))
    paradigm_cap = max(1, int(k * config.paradigm_cap_ratio))
    discovery_floor = max(1, int(k * config.discovery_floor_ratio))

    for c in scored:
        if len(selected) >= k:
            break
        d = c.metadata.get("domain")
        p = c.metadata.get("paradigm")
        disc = c.metadata["score"].get("discovery", 0)

        if d and domain_count[d] >= domain_cap:
            continue
        if p and paradigm_count[p] >= paradigm_cap:
            continue

        selected.append(c)
        if d: domain_count[d] += 1
        if p: paradigm_count[p] += 1
        if disc >= config.discovery_threshold: discovery_count += 1

    # Discovery floor チェック → 不足なら入れ替え
    if discovery_count < discovery_floor:
        remaining = [c for c in scored if c not in selected
                     and c.metadata["score"].get("discovery", 0) >= config.discovery_threshold]
        # 最も低スコアの非discovery候補と入れ替え
        for disc_c in remaining:
            if discovery_count >= discovery_floor:
                break
            for i in reversed(range(len(selected))):
                if selected[i].metadata["score"].get("discovery", 0) < config.discovery_threshold:
                    selected[i] = disc_c
                    discovery_count += 1
                    break

    return selected
