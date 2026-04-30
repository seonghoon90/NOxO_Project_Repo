"""테스트용 결정론적 Predictor.

진짜 ML 모델이 들어오기 전에 프론트가 화면을 그려보고 트렌드를 검증할 수 있도록
물리적 직관에 부합하는 단조 함수로 출력을 산출한다. 실제 수치는 의미 없음.

거동 요약:
- 화염온도 ↑ : 합성가스 유량, IGV 개도 ↑ / 질소 오프셋 ↑ 시 ↓ (희석 냉각)
- λ (공기비) ↑ : IGV 개도 ↑ (공기 더 들어옴) / 합성가스 유량 ↑ 시 ↓
- NOx : 화염온도와 λ에 강하게 의존 (Zeldovich 흉내, 단조 증가)
- CO : λ가 1 근처에서 최저, 멀어질수록 증가
- 발전량(MW) : 합성가스 유량과 IGV 개도에 비례, 질소 오프셋 ↑ 시 약간 ↓
"""

import math

from app.adapters.predictor.base import Predictor
from app.domain.tags import ControlVars, OutputVars


class StubPredictor:
    name = "stub"

    # 기준점 — 운영 한계 중간값을 디폴트 운전점으로 가정
    REF_SYNGAS = 1500.0
    REF_N2 = 200.0
    REF_IGV = 75.0

    # 베이스 출력값 — 기준점에서의 정상상태 가안
    BASE_FLAME_TEMP = 1450.0  # K
    BASE_LAMBDA = 1.10
    BASE_NOX = 25.0           # ppm
    BASE_CO = 12.0            # ppm
    BASE_POWER = 248.6        # MW (기준 운전점)

    def predict(self, controls: ControlVars) -> OutputVars:
        flame_temp = self._flame_temp(controls)
        lambda_ = self._lambda(controls)
        nox = self._nox(flame_temp, lambda_)
        co = self._co(lambda_)
        power = self._power(controls)
        return OutputVars(
            nox=nox,
            co=co,
            flame_temp=flame_temp,
            lambda_=lambda_,
            power=power,
        )

    # ----- 내부 함수 -----
    def _flame_temp(self, c: ControlVars) -> float:
        # 합성가스 유량 +500 → +120K, IGV +25 → +60K, N2 +300 → -90K
        delta = (
            (c.syngas_flow - self.REF_SYNGAS) * 0.24
            + (c.igv_opening - self.REF_IGV) * 2.4
            - (c.n2_offset - self.REF_N2) * 0.30
        )
        return max(900.0, self.BASE_FLAME_TEMP + delta)

    def _lambda(self, c: ControlVars) -> float:
        # IGV 개도가 공기 유량 비례 → λ 직접 영향, 합성가스 ↑ 시 λ ↓
        igv_ratio = max(c.igv_opening, 1.0) / self.REF_IGV
        fuel_ratio = max(c.syngas_flow, 1.0) / self.REF_SYNGAS
        # N2는 약한 보정 (질량 추가 → 약간 lean 방향)
        n2_bonus = (c.n2_offset - self.REF_N2) * 0.0005
        return max(0.5, self.BASE_LAMBDA * (igv_ratio / fuel_ratio) + n2_bonus)

    def _nox(self, flame_temp: float, lambda_: float) -> float:
        # Zeldovich: T가 지배적, λ는 산소 가용성 (최대치는 약 lean 영역)
        temp_factor = math.exp((flame_temp - self.BASE_FLAME_TEMP) / 120.0)
        lambda_factor = 1.0 + 0.6 * max(0.0, lambda_ - 1.0)
        return max(0.0, self.BASE_NOX * temp_factor * lambda_factor)

    def _co(self, lambda_: float) -> float:
        # λ=1 근처 최저, 멀어질수록 증가 (간단한 2차)
        return max(0.0, self.BASE_CO + 80.0 * (lambda_ - 1.0) ** 2)

    def _power(self, c: ControlVars) -> float:
        # 합성가스 유량 +500 → +22.5MW, IGV +25 → +33.8MW, N2 +300 → -24MW
        delta = (
            (c.syngas_flow - self.REF_SYNGAS) * 0.045
            + (c.igv_opening - self.REF_IGV) * 1.35
            - (c.n2_offset - self.REF_N2) * 0.08
        )
        return max(0.0, self.BASE_POWER + delta)


# 모듈 import 시점에 프로토콜 적합성을 정적으로 강제
_assert_protocol: Predictor = StubPredictor()
