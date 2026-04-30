"""DB engine / sessionmaker 인프라.

DATABASE_URL이 None이면 engine/sessionmaker가 None으로 유지되어
repository 레이어에서 fallback(더미 데이터)으로 동작한다.
"""

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DbContext:
    """전역 단일 인스턴스 — lifespan에서 init/dispose."""

    engine: Engine | None = None
    session_factory: sessionmaker[Session] | None = None

    @classmethod
    def init(cls, database_url: str | None) -> None:
        if not database_url:
            cls.engine = None
            cls.session_factory = None
            return
        cls.engine = create_engine(
            database_url,
            pool_pre_ping=True,   # idle 커넥션 자동 검증
            pool_size=5,
            max_overflow=5,
        )
        cls.session_factory = sessionmaker(bind=cls.engine, autoflush=False, expire_on_commit=False)

    @classmethod
    def dispose(cls) -> None:
        if cls.engine is not None:
            cls.engine.dispose()
        cls.engine = None
        cls.session_factory = None

    @classmethod
    def is_available(cls) -> bool:
        return cls.session_factory is not None


def get_db_session() -> Iterator[Session | None]:
    """FastAPI Depends용 DB 세션 컨텍스트.

    DB 미연결 환경에서는 None을 yield — repository가 fallback 처리.
    """
    if not DbContext.is_available():
        yield None
        return
    assert DbContext.session_factory is not None
    db = DbContext.session_factory()
    try:
        yield db
    finally:
        db.close()
