"""테스트용 결정론적 Forecaster.

Simulator Stub과 유사한 단조 거동의 5분 뒤 NOx placeholder.
실제 시계열 ML이 들어오기 전 프론트가 응답 포맷을 받아볼 수 있게 한다.

거동 (3변수 기반, 신규 7변수는 P3 또는 실제 모델로 처리):
- 합성가스 유량 ↑ → 5분 뒤 NOx ↑ (현재 운전 조건이 이어진다는 가정)
- IGV 개도 ↑ → λ ↑ → 5분 뒤 NOx ↑ (lean 운전)
- N2 오프셋 ↑ → 5분 뒤 NOx ↓ (희석 효과)
"""

from app.adapters.forecaster.base import Forecaster, ForecastInput


class StubForecaster:
    name = "stub"

    BASE_NOX = 25.0  # 기준 운전점 NOx [ppm]

    REF_SYNGAS = 1500.0
    REF_N2 = 200.0
    REF_IGV = 75.0

    def predict(self, inputs: ForecastInput) -> float:
        # 입력 피처가 비어있을 수도 있음 — 기준 운전점 NOx를 반환
        f = inputs.features
        delta = 0.0
        if "syngas_flow" in f:
            delta += (f["syngas_flow"] - self.REF_SYNGAS) * 0.012
        if "n2_offset" in f:
            delta -= (f["n2_offset"] - self.REF_N2) * 0.018
        if "igv_opening" in f:
            delta += (f["igv_opening"] - self.REF_IGV) * 0.10
        return max(0.0, self.BASE_NOX + delta)


_assert_protocol: Forecaster = StubForecaster()
