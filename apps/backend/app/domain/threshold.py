from dataclasses import dataclass


@dataclass(frozen=True)
class Threshold:
    """NOx 등의 운영 임계치. [조사 필요] 출처."""

    nox_ppm_limit: float
