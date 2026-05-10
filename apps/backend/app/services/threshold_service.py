"""운영 임계치 조회. DT config의 ThresholdConfig을 단일 진실원으로 사용.

운영 중 변경이 필요 없는 상수 성격이라 DB 분리를 두지 않는다.
시뮬 엔진(`digital_twin/simulation/engine.py`)의 warning 판정과 동일한 NOx 한계를
공유해 프론트 표시 한계와 시뮬 내부 한계의 이중 기준 발생을 차단한다.
"""

from app.schemas.threshold import ThresholdResponse
from digital_twin.simulation import DEFAULT_CONFIG, DTConfig


class ThresholdService:
    def __init__(self, dt_config: DTConfig = DEFAULT_CONFIG) -> None:
        self.dt_config = dt_config

    def get(self) -> ThresholdResponse:
        t = self.dt_config.thresholds
        return ThresholdResponse(
            nox_ppm_limit=t.nox_warning_ppm,
            efficiency_caution=t.efficiency_caution,
            efficiency_danger=t.efficiency_danger,
            exhaust_caution_c=t.exhaust_caution_c,
            exhaust_danger_c=t.exhaust_danger_c,
            lambda_caution_lo=t.lambda_caution_lo,
            lambda_caution_hi=t.lambda_caution_hi,
            lambda_danger_lo=t.lambda_danger_lo,
            lambda_danger_hi=t.lambda_danger_hi,
        )
