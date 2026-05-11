"""ML simulator readiness predicate shared by API and services."""

import os
from typing import Any


def is_ml_mode_ready(data_source: Any, simulator: Any) -> bool:
    return (
        data_source is not None
        and getattr(simulator, "name", None) == "ml"
        and os.getenv("SIMULATOR_FALLBACK_STUB", "").lower() != "true"
    )
