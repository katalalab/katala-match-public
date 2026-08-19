"""Choice Architecture — 判断疲労を消すUX.

Layer 0 (全候補 n=1000) → Layer 4 (採用 n=1) のテーパリング.
Decoy Effect は透明性ある裏付けでのみ使用.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Tapering:
    """Layer 別の提示数."""
    full: int = 1000        # Layer 0
    top: int = 10           # Layer 1: 上位提示
    compare: int = 3        # Layer 2: テーパリング
    binary: int = 2         # Layer 3: 比較
    final: int = 1          # Layer 4: 採用


def taper(candidates: list, layer: int, tapering: Tapering = Tapering()) -> list:
    """Layer に応じて候補数を絞る.

    candidates はすでにスコア順に並んでいる前提.
    """
    n = [tapering.full, tapering.top, tapering.compare,
         tapering.binary, tapering.final][layer]
    return candidates[:n]


def select_decoy(top2: list, all_candidates: list) -> dict | None:
    """Decoy Effect 用の比較候補を選ぶ.

    Layer 3 (binary) の判断を助けるため、両方より劣る第3候補を提示.
    ⚠ 倫理: ユーザーには "比較を助ける候補" と明示する.
    """
    if len(top2) < 2 or not all_candidates:
        return None
    # top2 と類似だが一段劣る候補を探す
    for c in all_candidates:
        if c in top2:
            continue
        # ここで簡易判定: 両方より低スコア かつ 類似条件
        if all(c.metadata.get("score", {}).get("total", 0) <
               t.metadata.get("score", {}).get("total", 0) for t in top2):
            return {"candidate": c, "note": "比較を助けるための候補です"}
    return None
