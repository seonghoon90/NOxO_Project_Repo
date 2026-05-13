"""실시간 예측 모드의 세션 도메인.

mode + control_override 상태를 보유. SimulationState는 기존대로 유지하되,
이번 spec에서 모드/override 정책은 Session이 담당한다.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.core.session_context import SessionContext
from app.exceptions import SessionModeConflictError
from digital_twin.simulation import ControlVars

Mode = Literal["sim", "realtime"]
_VALID_MODES: tuple[Mode, ...] = ("sim", "realtime")


@dataclass
class Session:
    sid: str
    context: SessionContext
    created_at: datetime
    last_active_at: datetime
    mode: Mode = "sim"
    control_override: ControlVars | None = None
    tick: int = 0

    def set_mode(self, mode: str) -> None:
        """모드 전환. realtime 진입 시 override + pending input flag 자동 해제."""
        if mode not in _VALID_MODES:
            raise ValueError(f"invalid mode: {mode}")
        self.mode = mode  # type: ignore[assignment]
        if mode == "realtime":
            self.control_override = None
            self.context.pending_input_flag = False
        self._touch()

    def set_override(self, controls: ControlVars) -> None:
        """사용자 제어값 고정. realtime 모드에서는 거부.

        spec §2.1 — 사용자 입력 즉시 ML 호출 게이트 활성화:
        pending_input_flag + last_input_t를 세팅해 MLSimulator._should_call_ml의
        debounce(1s) 분기를 통과시킨다.
        """
        if self.mode == "realtime":
            raise SessionModeConflictError(
                f"control disabled in realtime mode (sid={self.sid})"
            )
        self.control_override = controls
        self.context.pending_input_flag = True
        self.context.last_input_t = time.monotonic()
        self._touch()

    def clear_override(self) -> None:
        """Kafka 추종 복귀. idempotent (이미 None이거나 realtime이어도 no-op).

        override가 해제되므로 즉시 ML 호출 게이트(pending_input_flag)도 함께 해제.
        """
        self.control_override = None
        self.context.pending_input_flag = False
        self._touch()

    def _touch(self) -> None:
        self.last_active_at = datetime.now(timezone.utc)
