from pydantic import BaseModel


class ThresholdResponse(BaseModel):
    """프론트 화면 임계 색상/배지 판정용 운영 한계 묶음.

    단일 진실원은 `digital_twin/simulation/config.py`의 `ThresholdConfig`.
    시뮬 엔진 내부 안전 클램프(nox_ceiling/floor 등)는 노출하지 않는다.
    """

    nox_ppm_limit: float

    # 발전 효율 — 정격 0.89 기준, 미만 시 주의/위험. 이상 시 항상 정상.
    efficiency_caution: float
    efficiency_danger: float

    # 배기온도 상한 [°C]
    exhaust_caution_c: float
    exhaust_danger_c: float

    # 공기비(λ) 운영 한계
    lambda_caution_lo: float
    lambda_caution_hi: float
    lambda_danger_lo: float
    lambda_danger_hi: float
