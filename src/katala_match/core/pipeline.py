"""Source → Hydrator → Filter → Scorer → Selector → SideEffect.

Abstract pipeline shape: Source -> Hydrator -> Gate -> Scorer -> Selector -> SideEffect.
Domain implementations subclass these to specialize.

"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Iterable, TypeVar

T = TypeVar("T")  # Candidate payload type (e.g. a listing dict, a job dict)


@dataclass
class Candidate(Generic[T]):
    """Pipeline を流れる候補オブジェクト. ドメイン固有データは payload に."""
    id: str
    payload: T
    metadata: dict[str, Any] = field(default_factory=dict)


class Source(ABC, Generic[T]):
    """候補の生成元(スクレイパー, メール受信, 外部API 等)."""
    @abstractmethod
    def fetch(self) -> Iterable[Candidate[T]]: ...


class Hydrator(ABC, Generic[T]):
    """候補に外部データを付与(地理情報・公的統計・外部API 等)."""
    @abstractmethod
    def hydrate(self, candidate: Candidate[T]) -> Candidate[T]: ...


class Gate(ABC, Generic[T]):
    """硬性条件で候補を弾く. 失敗時は reason を返す."""
    @abstractmethod
    def check(self, candidate: Candidate[T]) -> tuple[bool, str | None]: ...


class Scorer(ABC, Generic[T]):
    """Score(z) = α·Fit + β·Discovery − γ·Risk を計算."""
    @abstractmethod
    def score(self, candidate: Candidate[T]) -> dict[str, float]: ...


class Selector(ABC, Generic[T]):
    """Top-K + creativity floor + diversity caps."""
    @abstractmethod
    def select(self, scored: list[Candidate[T]], k: int) -> list[Candidate[T]]: ...


class SideEffect(ABC, Generic[T]):
    """ledger 書き込み・通知送信・新着監視ジョブ作成 等の副作用."""
    @abstractmethod
    def emit(self, selected: list[Candidate[T]]) -> None: ...


@dataclass
class Pipeline(Generic[T]):
    """Pipeline 全体を組み立てて回す."""
    sources: list[Source[T]]
    hydrators: list[Hydrator[T]]
    gates: list[Gate[T]]
    scorer: Scorer[T]
    selector: Selector[T]
    side_effects: list[SideEffect[T]]

    def run(self, k: int = 10) -> list[Candidate[T]]:
        # 1. Source
        candidates: list[Candidate[T]] = []
        for src in self.sources:
            candidates.extend(src.fetch())
        # 2. Hydrator
        for h in self.hydrators:
            candidates = [h.hydrate(c) for c in candidates]
        # 3. Filter (Gates)
        passed = []
        for c in candidates:
            failed_reasons = []
            for g in self.gates:
                ok, reason = g.check(c)
                if not ok:
                    failed_reasons.append(reason)
            if not failed_reasons:
                passed.append(c)
            else:
                c.metadata["gate_failures"] = failed_reasons
        # 4. Scorer
        for c in passed:
            c.metadata["score"] = self.scorer.score(c)
        # 5. Selector
        selected = self.selector.select(passed, k)
        # 6. SideEffect
        for fx in self.side_effects:
            fx.emit(selected)
        return selected
