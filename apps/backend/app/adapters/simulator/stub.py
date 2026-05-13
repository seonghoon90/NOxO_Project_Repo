"""테스트용 결정론적 Simulator.

진짜 ML 모델이 들어오기 전에 프론트가 화면을 그려보고 트렌드를 검증할 수 있도록
물리적 직관에 부합하는 단조 함수로 출력을 산출한다. 실제 수치는 의미 없음.

거동 요약:

기존 3변수 (지배적)
- 합성가스 유량 ↑    : 배기온도 ↑, 발전량 ↑, λ ↓
- IGV 개도 ↑        : 배기온도 ↑, 발전량 ↑, λ ↑
- N2 오프셋 ↑       : 배기온도 ↓, 발전량 ↓ (희석 냉각)

신규 7변수 (약한 보정 — `[추후 결정]` 가안 거동)
- N2 주입계 (n2_valve_1, n2_flow): NOx ↓ / 배기온도 약간 ↓ / 발전량 약간 ↓ (희석)
- Syngas 공급계 (syngas_srv, gcv_1/1a/2): 배기온도 ↑ / 발전량 ↑ (연료 공급)
- IBH 밸브 (ibh_valve): 효율 ↓ / 배기온도 약간 ↑ (heating bleed)
"""

import math

from app.adapters.simulator.base import Simulator
from digital_twin.simulation import ControlVars, OutputVars
from digital_twin.simulation.features import compute_efficiency


class StubSimulator:
    name = "stub"

    # 기준점 — 운영 한계 중간값을 디폴트 운전점으로 가정
    REF_SYNGAS = 1500.0
    REF_N2 = 200.0
    REF_IGV = 75.0

    # 신규 7변수 기준점 — `BACKEND_ARCHITECTURE.md §7` 가안값
    REF_N2_VALVE_1 = 50.0
    REF_SYNGAS_SRV = 60.0
    REF_SYNGAS_GCV_1 = 55.0
    REF_SYNGAS_GCV_1A = 55.0
    REF_SYNGAS_GCV_2 = 55.0
    REF_IBH_VALVE = 30.0
    REF_N2_FLOW = 100.0

    # 베이스 출력값 — 기준점에서의 정상상태 가안
    BASE_EXHAUST_TEMP = 580.0  # °C — IGCC.CC.G1.TTXM
    BASE_LAMBDA = 1.10
    BASE_NOX = 25.0            # ppm
    BASE_POWER = 248.6         # MW (기준 운전점)

    def predict(self, controls: ControlVars) -> OutputVars:
        exhaust_temp = self._exhaust_temp(controls)
        lambda_ = self._lambda(controls)
        nox = self._nox(controls, exhaust_temp, lambda_)
        power = self._power(controls)
        # efficiency는 features 근사식 + IBH bleed 페널티.
        # RealtimeEngine이 power/(syngas_flow×LHV)로 덮어쓰므로 placeholder.
        base_eff = compute_efficiency(controls.syngas_flow, exhaust_temp)
        ibh_penalty = max(0.0, controls.ibh_valve - self.REF_IBH_VALVE) * 0.001
        efficiency = max(0.0, min(1.0, base_eff - ibh_penalty))
        return OutputVars(
            nox=nox,
            exhaust_temp=exhaust_temp,
            power=power,
            lambda_=lambda_,
            efficiency=efficiency,
        )

    def predict_for_session(self, controls: ControlVars, session_ctx) -> OutputVars:
        """Simulator Protocol(predict_for_session) 호환 — Stub은 ctx 무시 + predict 위임."""
        return self.predict(controls)

    # ----- 내부 함수 -----
    def _exhaust_temp(self, c: ControlVars) -> float:
        # 합성가스 유량 +500 → +12°C, IGV +25 → +6°C, N2 +300 → -9°C
        delta = (
            (c.syngas_flow - self.REF_SYNGAS) * 0.024
            + (c.igv_opening - self.REF_IGV) * 0.24
            - (c.n2_offset - self.REF_N2) * 0.030
        )
        # 신규 변수 기여 (약한 보정).
        delta += self._syngas_supply_bonus(c) * 0.05  # 연료 공급계 → 약한 온도 ↑
        delta += self._n2_dilution(c) * -0.02         # N2 주입 ↑ → 온도 ↓
        delta += (c.ibh_valve - self.REF_IBH_VALVE) * 0.04  # IBH bleed → 약한 ↑
        return max(400.0, self.BASE_EXHAUST_TEMP + delta)

    def _lambda(self, c: ControlVars) -> float:
        # IGV 개도가 공기 유량 비례 → λ 직접 영향, 합성가스 ↑ 시 λ ↓
        igv_ratio = max(c.igv_opening, 1.0) / self.REF_IGV
        fuel_ratio = max(c.syngas_flow, 1.0) / self.REF_SYNGAS
        # N2는 약한 보정 (질량 추가 → 약간 lean 방향)
        n2_bonus = (c.n2_offset - self.REF_N2) * 0.0005
        return max(0.5, self.BASE_LAMBDA * (igv_ratio / fuel_ratio) + n2_bonus)

    def _nox(self, c: ControlVars, exhaust_temp: float, lambda_: float) -> float:
        # Zeldovich: T가 지배적, λ는 산소 가용성 (최대치는 약 lean 영역)
        temp_factor = math.exp((exhaust_temp - self.BASE_EXHAUST_TEMP) / 12.0)
        lambda_factor = 1.0 + 0.6 * max(0.0, lambda_ - 1.0)
        # N2 주입계 강화 시 NOx 저감 (희석 + thermal NOx 억제 효과 흉내).
        n2_reduction = 1.0 - min(0.3, max(0.0, self._n2_dilution(c)) * 0.0015)
        return max(0.0, self.BASE_NOX * temp_factor * lambda_factor * n2_reduction)

    def _power(self, c: ControlVars) -> float:
        # 합성가스 유량 +500 → +22.5MW, IGV +25 → +33.8MW, N2 +300 → -24MW
        delta = (
            (c.syngas_flow - self.REF_SYNGAS) * 0.045
            + (c.igv_opening - self.REF_IGV) * 1.35
            - (c.n2_offset - self.REF_N2) * 0.08
        )
        # 신규 변수: 연료 공급계 ↑ 시 출력 ↑, N2 주입 ↑ 시 출력 약간 ↓
        delta += self._syngas_supply_bonus(c) * 0.10
        delta -= self._n2_dilution(c) * 0.03
        return max(0.0, self.BASE_POWER + delta)

    # ----- 신규 7변수 합산 헬퍼 -----
    def _syngas_supply_bonus(self, c: ControlVars) -> float:
        """Syngas 공급계 4개 밸브 개도 편차 합 (기준 대비)."""
        return (
            (c.syngas_srv - self.REF_SYNGAS_SRV)
            + (c.syngas_gcv_1 - self.REF_SYNGAS_GCV_1)
            + (c.syngas_gcv_1a - self.REF_SYNGAS_GCV_1A)
            + (c.syngas_gcv_2 - self.REF_SYNGAS_GCV_2)
        )

    def _n2_dilution(self, c: ControlVars) -> float:
        """N2 주입계 2변수 편차 합 (기준 대비)."""
        return (
            (c.n2_valve_1 - self.REF_N2_VALVE_1)
            + (c.n2_flow - self.REF_N2_FLOW)
        )


# 모듈 import 시점에 프로토콜 적합성을 정적으로 강제
_assert_protocol: Simulator = StubSimulator()
