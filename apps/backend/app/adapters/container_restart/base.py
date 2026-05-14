"""컨테이너 재시작 어댑터 Protocol.

운영(`DockerSocketAdapter`) / 개발(`NoopRestartAdapter`) 두 구현체로 분기.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ContainerRestartAdapter(Protocol):
    def is_available(self) -> bool:
        """현재 환경에서 restart 호출이 의미 있는지 여부."""
        ...

    async def restart(self, container_name: str) -> None:
        """주어진 이름의 컨테이너를 재시작. 실패는 로깅 후 swallow."""
        ...
