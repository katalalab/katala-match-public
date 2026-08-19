"""Translation loss estimators for human-to-human and human-to-AI mediation.

L2 RSA and L3 NVC are intentionally first-class because they are where simple
keyword matching fails: people imply more than they say, and complaints often
encode unmet needs.
"""
from __future__ import annotations

import math
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .person_model import PersonModel


class LossLevel(str, Enum):
    L1_LEXICAL = "L1_lexical_ambiguity"
    L2_RSA = "L2_pragmatic_rsa_mismatch"
    L3_NVC = "L3_nvc_need_translation"
    L4_PREFERENCE_COMPRESSION = "L4_preference_compression"
    L5_CONTEXT_OMISSION = "L5_context_omission"
    L6_POWER_INCENTIVE = "L6_power_incentive_distortion"
    L7_TEMPORAL_DRIFT = "L7_temporal_drift"


class LossSignal(BaseModel):
    level: LossLevel
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str = ""


class TranslationLossReport(BaseModel):
    text: str
    overall: float = Field(ge=0.0, le=1.0)
    signals: list[LossSignal]

    def by_level(self) -> dict[LossLevel, LossSignal]:
        return {signal.level: signal for signal in self.signals}


AMBIGUOUS_TERMS = {
    "普通", "いい感じ", "ちゃんと", "なるべく", "柔軟", "ほどよく", "安心",
    "カルチャー", "成長", "自走", "相性", "余裕", "近い", "高い", "低い",
}
HEDGES = {"少し", "ちょっと", "できれば", "一応", "多分", "気がする", "かも", "なんとなく"}
EVALUATION_WORDS = {"最悪", "無理", "嫌", "雑", "怖い", "不安", "押し切", "信用できない"}
FEELING_WORDS = {"不安", "怖い", "焦る", "疲れる", "安心", "納得", "困る", "嬉しい"}
NEED_WORDS = {"安全", "尊重", "透明", "裁量", "安定", "成長", "休息", "公平", "信頼", "余白"}
POWER_WORDS = {"契約", "上司", "貸主", "仲介", "保証", "評価", "給与", "年収", "断れない"}
TIME_WORDS = {"今", "すぐ", "将来", "来月", "更新", "長期", "短期", "一時的", "そのうち"}


def _contains_any(text: str, words: set[str]) -> list[str]:
    return [w for w in words if w in text]


def _score(count: int, denominator: int = 4) -> float:
    return round(min(1.0, count / denominator), 3)


def estimate_l1_lexical(text: str) -> LossSignal:
    hits = _contains_any(text, AMBIGUOUS_TERMS)
    return LossSignal(
        level=LossLevel.L1_LEXICAL,
        score=_score(len(hits), 5),
        evidence=hits,
        recommendation="曖昧語を測定可能な条件・反例・許容幅に分解する。",
    )


def estimate_l2_rsa(text: str, speaker: PersonModel | None = None) -> LossSignal:
    """Estimate Rational Speech Act / pragmatic mismatch risk.

    High when the utterance is hedged, indirect, or relies on unstated context.
    Speaker hard-dislikes reduce uncertainty only when the text names them.
    """
    evidence = []
    hedges = _contains_any(text, HEDGES)
    if hedges:
        evidence.extend([f"hedge:{h}" for h in hedges])
    if re.search(r"(本当は|実は|とはいえ|でも|ただ)", text):
        evidence.append("contrastive_implicature")
    if "?" in text or "？" in text:
        evidence.append("question_as_indirect_request")
    if speaker:
        named_dislikes = [d for d in speaker.declared.hard_dislikes if d and d in text]
        missing_dislikes = len(speaker.declared.hard_dislikes) - len(named_dislikes)
        if missing_dislikes > 0:
            evidence.append(f"speaker_known_dislikes_not_explicit:{missing_dislikes}")
    score = _score(len(evidence), 4)
    return LossSignal(
        level=LossLevel.L2_RSA,
        score=score,
        evidence=evidence,
        recommendation="発話者がなぜその表現を選んだか、代替表現と隠れた拒否条件を推定して確認する。",
    )


def estimate_l3_nvc(text: str) -> LossSignal:
    """Estimate NVC translation loss: evaluation without observation/need/request."""
    evidence = []
    evaluations = _contains_any(text, EVALUATION_WORDS)
    feelings = _contains_any(text, FEELING_WORDS)
    needs = _contains_any(text, NEED_WORDS)
    has_request = bool(re.search(r"(してほしい|お願いします|必要|避けたい|欲しい|ください)", text))
    if evaluations:
        evidence.extend([f"evaluation:{w}" for w in evaluations])
    if feelings:
        evidence.extend([f"feeling:{w}" for w in feelings])
    if not needs:
        evidence.append("need_not_named")
    if not has_request:
        evidence.append("request_not_named")
    score = _score(len(evaluations) + (0 if needs else 2) + (0 if has_request else 1), 5)
    return LossSignal(
        level=LossLevel.L3_NVC,
        score=score,
        evidence=evidence,
        recommendation="評価語を観察・感情・必要・リクエストに分解し、相手に渡せる形へ翻訳する。",
    )


def estimate_translation_loss(
    text: str,
    *,
    speaker: PersonModel | None = None,
    listener: PersonModel | None = None,
    context: dict[str, Any] | None = None,
) -> TranslationLossReport:
    context = context or {}
    signals = [
        estimate_l1_lexical(text),
        estimate_l2_rsa(text, speaker),
        estimate_l3_nvc(text),
    ]

    constraints = len((speaker.declared.hard_constraints if speaker else {}) or {})
    preferences = len((speaker.declared.preferences if speaker else {}) or {})
    compression = 0.0 if preferences + constraints <= 3 else min(1.0, (preferences + constraints - 3) / 8)
    signals.append(LossSignal(
        level=LossLevel.L4_PREFERENCE_COMPRESSION,
        score=round(compression, 3),
        evidence=[f"known_variables:{preferences + constraints}"] if speaker else [],
        recommendation="一つの総合点に潰さず、変数ごとの重み・許容度・例外条件を残す。",
    ))

    missing_context = []
    if speaker and not speaker.context.roles:
        missing_context.append("speaker_roles_missing")
    if listener and not listener.context.roles:
        missing_context.append("listener_roles_missing")
    if not context:
        missing_context.append("shared_context_missing")
    signals.append(LossSignal(
        level=LossLevel.L5_CONTEXT_OMISSION,
        score=_score(len(missing_context), 3),
        evidence=missing_context,
        recommendation="誰が誰に、どの制約下で話しているかを明示してから評価する。",
    ))

    power_hits = _contains_any(text, POWER_WORDS)
    signals.append(LossSignal(
        level=LossLevel.L6_POWER_INCENTIVE,
        score=_score(len(power_hits), 4),
        evidence=power_hits,
        recommendation="利害・評価権・断りにくさを別変数として扱い、合意と服従を分ける。",
    ))

    time_hits = _contains_any(text, TIME_WORDS)
    signals.append(LossSignal(
        level=LossLevel.L7_TEMPORAL_DRIFT,
        score=_score(len(time_hits), 4),
        evidence=time_hits,
        recommendation="短期の痛みと長期の価値を分け、次回更新日を設定する。",
    ))

    weighted = sum(s.score for s in signals) / len(signals)
    # Penalize simultaneous L2+L3 risk slightly more because it is the mediator hot path.
    l2 = signals[1].score
    l3 = signals[2].score
    overall = min(1.0, weighted + 0.15 * math.sqrt(l2 * l3))
    return TranslationLossReport(text=text, overall=round(overall, 3), signals=signals)
