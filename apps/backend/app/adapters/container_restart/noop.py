"""개발/테스트용 폴백 — 호출돼도 아무것도 하지 않음.

`is_available() == False`이므로 ResetService는 이 어댑터를 갖고 있는 한
`ResetUnavailableError`를 raise한다. 즉 restart()는 사실상 호출되지 않는다.
"""

import logging

logger = logging.getLogger(__name__)


class NoopRestartAdapter:
    def is_available(self) -> bool:
        return False

    async def restart(self, container_name: str) -> None:
        logger.info("noop_restart container=%s (no docker socket)", container_name)
