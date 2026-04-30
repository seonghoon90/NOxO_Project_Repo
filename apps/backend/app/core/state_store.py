"""세션별 SimulationState 저장소.

Protocol 기반 추상화 — 추후 Redis 등 외부 저장소로 교체 가능 (`[추후 결정]`).
"""

from typing import Iterator, Protocol

from digital_twin.simulation import SimulationState


class StateStore(Protocol):
    def put(self, state: SimulationState) -> None: ...
    def get(self, sid: str) -> SimulationState | None: ...
    def remove(self, sid: str) -> SimulationState | None: ...
    def __contains__(self, sid: str) -> bool: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[str]: ...


class InMemoryStateStore:
    """초기 버전: 단일 프로세스 메모리에 dict로 보관."""

    def __init__(self) -> None:
        self._states: dict[str, SimulationState] = {}

    def put(self, state: SimulationState) -> None:
        self._states[state.sid] = state

    def get(self, sid: str) -> SimulationState | None:
        return self._states.get(sid)

    def remove(self, sid: str) -> SimulationState | None:
        return self._states.pop(sid, None)

    def __contains__(self, sid: str) -> bool:
        return sid in self._states

    def __len__(self) -> int:
        return len(self._states)

    def __iter__(self) -> Iterator[str]:
        return iter(list(self._states.keys()))
