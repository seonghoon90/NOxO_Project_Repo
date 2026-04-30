import logging


def configure_logging(level: str = "info") -> None:
    """프로세스 전역 로거 설정. uvicorn 로거와도 호환되도록 root 레벨만 조정."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
