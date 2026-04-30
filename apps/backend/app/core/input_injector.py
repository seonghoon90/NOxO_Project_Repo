"""세션별 제어 입력 큐.

REST `POST /control`로 들어온 입력을 다음 sim step에 반영하기 위한 버퍼.
overwrite 정책 — 동일 step 내 여러 입력이 들어오면 마지막 값만 적용.
"""

from app.domain.tags import ControlVars


class InputInjector:
    def __init__(self) -> None:
        self._pending: dict[str, ControlVars] = {}

    def submit(self, sid: str, controls: ControlVars) -> None:
        self._pending[sid] = controls

    def consume(self, sid: str) -> ControlVars | None:
        return self._pending.pop(sid, None)

    def discard(self, sid: str) -> None:
        self._pending.pop(sid, None)
