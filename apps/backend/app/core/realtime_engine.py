"""1초 tick 통합 엔진.

모든 활성 세션을 1개 asyncio task가 순회하며 mode/override 기반으로 추론한다.
세션별 sim_loop 모델(폐기) → 전역 1 tick 모델로 단일화 (spec §5).
"""

from __future__ import annotations

import asyncio
import logging
import math
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.forecaster import Forecaster, ForecastInput
from app.adapters.simulator import Simulator
from app.config import Settings
from app.core.sensor_buffer import SensorBuffer, operating_point_to_sensor_row
from app.core.session import Session
from app.core.ws_manager import WebSocketManager
from app.domain.tags import control_vars_to_tag_dict, denormalize_to_raw_tags
from digital_twin.simulation import (
    DEFAULT_CONFIG,
    ControlVars,
    DTConfig,
    OutputVars,
)
from digital_twin.simulation.features import compute_lambda

logger = logging.getLogger(__name__)

FORECAST_HORIZON_MINUTES = 5  # spec §0.2

# NOx 15% O2 표준 보정식의 기준 산소 농도 [%]
# nox_15pct = nox * (20.9 - 15) / (20.9 - o2)
# O2가 20.4% 이상이면 분모가 0.5% 미만이 되어 보정값이 발산 → raw nox fallback.
_NOX_REF_O2_PCT: float = 15.0
_NOX_AMB_O2_PCT: float = 20.9
_NOX_O2_MIN_DENOM: float = 0.5


def correct_nox_15pct(nox: float, o2_pct: float | None) -> float:
    """NOx를 15% O2 기준으로 보정. 입력 O2가 비정상이면 raw nox 반환.

    비정상 케이스 — 모두 raw nox로 fallback:
    - None
    - 음수 (센서 fault)
    - 21% 이상 (분모 < 0.5%로 보정값 발산)
    """
    if o2_pct is None or o2_pct < 0.0:
        return nox
    denom = _NOX_AMB_O2_PCT - o2_pct
    if denom < _NOX_O2_MIN_DENOM:
        return nox
    return nox * (_NOX_AMB_O2_PCT - _NOX_REF_O2_PCT) / denom


class RealtimeEngine:
    """전역 1초 tick + 세션 순회 + WS broadcast."""

    def __init__(
        self,
        settings: Settings,
        sensor_buffer: SensorBuffer,
        simulator: Simulator,
        forecaster: Forecaster,
        ws_manager: WebSocketManager,
        sessions: dict[str, Session],
        dt_config: DTConfig = DEFAULT_CONFIG,
    ) -> None:
        self.settings = settings
        self.sensor_buffer = sensor_buffer
        self.simulator = simulator
        self.forecaster = forecaster
        self.ws_manager = ws_manager
        self.sessions = sessions
        self.dt_config = dt_config
        self.tick_interval = dt_config.sim_step.dt
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        # 세션별 마지막 broadcast payload 캐시 — WS 재연결 시 즉시 snapshot push용
        self._last_payloads: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_forever(), name="realtime-engine")
        logger.info("RealtimeEngine started (tick=%.2fs)", self.tick_interval)

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        self._task = None
        self._stop_event = None

    async def _run_forever(self) -> None:
        try:
            loop = asyncio.get_running_loop()
            # 첫 tick은 즉시 실행 → 이후 매 1초 deadline 누적 (offset 없이 시작).
            next_deadline = loop.time()
            while self._stop_event is not None and not self._stop_event.is_set():
                await self._tick()
                now = loop.time()
                # 처리가 한 tick 이상 밀린 경우만 deadline 리셋 (drift 누적 방지).
                # 정상 경로(now ≤ next_deadline+interval)는 누적 deadline 유지 → 평균 drift 0.
                if now > next_deadline + self.tick_interval:
                    next_deadline = now + self.tick_interval
                else:
                    next_deadline += self.tick_interval
                await asyncio.sleep(max(0.0, next_deadline - loop.time()))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("realtime_engine_crashed")

    async def _tick(self) -> None:
        sessions_snapshot = list(self.sessions.items())
        if not sessions_snapshot:
            return
        # spec §2.3 — SensorBuffer 비어있어도 broadcast 유지:
        #   sim 모드: 마지막 bootstrap 값(lifespan에서 operating_point 폴백 보장).
        #   realtime 모드: warning="kafka stream stale" 채워 broadcast.
        # lifespan에서 fallback row를 주입하므로 latest_row()는 정상적으로 None이 아니지만,
        # 방어적으로 None일 때도 broadcast 시도(stale warning).
        kafka_row = self.sensor_buffer.latest_row()
        stream_stale = kafka_row is None
        if kafka_row is None:
            kafka_row = self._stale_fallback_row()
        await asyncio.gather(
            *[
                self._step_and_broadcast(sid, session, kafka_row, stream_stale)
                for sid, session in sessions_snapshot
            ],
            return_exceptions=True,
        )

    def _stale_fallback_row(self) -> dict[str, Any]:
        """SensorBuffer가 완전히 빈 경우의 최종 폴백 — operating_point 기반."""
        return operating_point_to_sensor_row(self.dt_config.operating_point)

    async def _step_and_broadcast(
        self, sid: str, session: Session, kafka_row: dict[str, Any],
        stream_stale: bool = False,
    ) -> None:
        try:
            session.tick += 1
            payload = self._step_session(session, kafka_row, stream_stale=stream_stale)
            self._last_payloads[sid] = payload
            await self.ws_manager.broadcast(sid, payload)
        except Exception:
            logger.exception("tick_failed sid=%s", sid)

    def last_payload(self, sid: str) -> dict[str, Any] | None:
        """세션의 마지막 broadcast payload — WS 재연결 시 즉시 snapshot push용."""
        return self._last_payloads.get(sid)

    def discard_session(self, sid: str) -> None:
        """세션 종료 시 캐시 정리."""
        self._last_payloads.pop(sid, None)

    def _step_session(
        self, session: Session, kafka_row: dict[str, Any],
        *, stream_stale: bool = False,
    ) -> dict[str, Any]:
        kafka_controls = self._kafka_row_to_controls(kafka_row)

        # 1. input_controls 결정
        if session.control_override is not None:
            input_controls = session.control_override
            override_active = True
        else:
            input_controls = kafka_controls
            override_active = False

        # 2. SessionContext.recent_df_buffer 갱신 (외란 + 사용된 제어).
        # H4 — realtime + stream_stale: fallback row가 매 tick 누적되어 학습 분포를
        # 평탄화시키므로 append skip. sim 모드는 자기재생이라 유지.
        skip_buffer_append = stream_stale and session.mode == "realtime"
        if not skip_buffer_append:
            synthesized = self._synthesize_row(kafka_row, input_controls, session)
            session.context.recent_df_buffer.append(synthesized)

        # 3. O2 추출 (lambda_ 역산식 + nox_15pct 표시 보정 공용 입력).
        # 학습/예측 입력엔 미사용. bool은 isinstance(_, int) 통과하므로 명시적 제외,
        # 비숫자/NaN은 None으로 폴백 → compute_lambda가 IGV/syngas 근사식으로 자동 전환.
        raw_o2 = kafka_row.get("o2_pct")
        if isinstance(raw_o2, bool) or not isinstance(raw_o2, (int, float)):
            o2_pct = None
        else:
            o2_pct = float(raw_o2)
            if not math.isfinite(o2_pct):
                o2_pct = None

        # 4. DT current 추론 + lambda_/efficiency 후처리
        ml_outputs = self.simulator.predict_for_session(
            input_controls, session.context
        )
        current_outputs = self._postprocess_outputs(ml_outputs, input_controls, o2_pct)

        # 5. realtime 모드면 forecast (o2_pct로 표시 보정값도 함께 채움)
        forecast_payload = None
        warning = None
        if session.mode == "realtime":
            if stream_stale:
                # spec §2.3 — Kafka stream 끊김 시 realtime 모드는 warning 채움
                warning = "kafka stream stale"
            else:
                try:
                    inputs = self._build_forecast_input(session, input_controls)
                    predicted = self.forecaster.predict(inputs)
                    forecast_payload = self._build_forecast_payload(predicted, o2_pct)
                except Exception as exc:
                    logger.warning("forecast_failed sid=%s err=%s", session.sid, exc)
                    warning = "forecast unavailable"

        # 6. payload 조립
        return self._build_payload(
            session=session,
            input_controls=input_controls,
            current_outputs=current_outputs,
            override_active=override_active,
            kafka_controls=kafka_controls,
            kafka_ts=kafka_row.get("measured_at"),
            forecast_payload=forecast_payload,
            warning=warning,
            o2_pct=o2_pct,
        )

    def _postprocess_outputs(
        self,
        ml_outputs: OutputVars,
        controls: ControlVars,
        o2_pct: float | None,
    ) -> OutputVars:
        """ML 출력의 lambda_/efficiency 덮어쓰기.

        ML 모델은 두 필드를 학습 타깃에 포함하지 않으므로 dummy(0.0)를 반환한다.
        - lambda_ : digital_twin.simulation.features.compute_lambda로 재계산
            O2 측정값(AIT_H1_902)이 있으면 20.9/(20.9-O2) 역산식,
            없으면 IGV/syngas 근사식 폴백.
        - efficiency: power / (syngas_flow × syngas_lhv) 후처리 + [0,1] 클램프
        StubSimulator는 자체 lambda_/efficiency를 반환하지만, 일관성을 위해 모든
        simulator 출력에 동일 후처리를 적용한다 (Stub의 lambda_/efficiency도 동일식).
        """
        lambda_ = compute_lambda(
            syngas_flow=controls.syngas_flow,
            n2_offset=controls.n2_offset,
            igv_opening=controls.igv_opening,
            o2_dry_pct=o2_pct,
            op=self.dt_config.operating_point,
            fc=self.dt_config.features,
        )
        denom = controls.syngas_flow * self.settings.syngas_lhv
        if denom > 0.0:
            efficiency = max(0.0, min(1.0, ml_outputs.power / denom))
        else:
            efficiency = ml_outputs.efficiency
        return OutputVars(
            nox=ml_outputs.nox,
            exhaust_temp=ml_outputs.exhaust_temp,
            power=ml_outputs.power,
            lambda_=lambda_,
            efficiency=efficiency,
        )

    def _kafka_row_to_controls(self, kafka_row: dict[str, Any]) -> ControlVars:
        return ControlVars(
            syngas_flow=float(kafka_row.get("syngas_flow", 0.0)),
            igv_opening=float(kafka_row.get("igv_opening", 0.0)),
            n2_offset=float(kafka_row.get("n2_offset", 0.0)),
            n2_valve_1=float(kafka_row.get("n2_valve_1", 0.0)),
            syngas_srv=float(kafka_row.get("syngas_srv", 0.0)),
            syngas_gcv_1=float(kafka_row.get("syngas_gcv_1", 0.0)),
            syngas_gcv_1a=float(kafka_row.get("syngas_gcv_1a", 0.0)),
            syngas_gcv_2=float(kafka_row.get("syngas_gcv_2", 0.0)),
            ibh_valve=float(kafka_row.get("ibh_valve", 0.0)),
            n2_flow=float(kafka_row.get("n2_flow", 0.0)),
        )

    def _synthesize_row(
        self,
        kafka_row: dict[str, Any],
        input_controls: ControlVars,
        session: Session,
    ) -> dict[str, Any]:
        """외란(plant_context) + kafka 도메인값 + input_controls 합쳐 한 행 dict 반환.

        SessionContext.recent_df_buffer는 원천 태그(IGCC.*) 네임스페이스(RAW 39 + TTXM).
        외란 매핑 미완(DISTURBANCE_TAGS={})이라 kafka_row에는 제어 10 + 출력 3밖에
        없으므로 plant_context(스냅샷 시점 외란 29 + TTXM)를 베이스로 깔고
        kafka 도메인값(denormalize) → input_controls 순으로 덮어쓴다.
        이렇게 해야 deque(maxlen=900)가 evict된 뒤에도 RAW 39 + TTXM 컬럼이 보존되어
        dt_predict의 recent_df 요구를 충족한다.
        """
        merged_raw = dict(session.context.plant_context)
        merged_raw.update(
            denormalize_to_raw_tags(
                {k: v for k, v in kafka_row.items() if k != "measured_at"}
            )
        )
        merged_raw.update(control_vars_to_tag_dict(input_controls))
        return merged_raw

    def _controls_to_features(self, controls: ControlVars) -> dict[str, float]:
        return {
            "syngas_flow": controls.syngas_flow,
            "igv_opening": controls.igv_opening,
            "n2_offset": controls.n2_offset,
            "n2_valve_1": controls.n2_valve_1,
            "syngas_srv": controls.syngas_srv,
            "syngas_gcv_1": controls.syngas_gcv_1,
            "syngas_gcv_1a": controls.syngas_gcv_1a,
            "syngas_gcv_2": controls.syngas_gcv_2,
            "ibh_valve": controls.ibh_valve,
            "n2_flow": controls.n2_flow,
        }

    def _build_forecast_input(
        self, session: Session, controls: ControlVars
    ) -> ForecastInput:
        # MLForecaster는 raw 시계열 DataFrame을 요구, Stub은 features dict.
        # SessionContext.recent_df_buffer는 _synthesize_row가 RAW 39 + TTXM 키를 매 tick
        # 채워주지만 NOX/DWATT는 BUFFER_COLS에 없어 누락 → forecaster.predict가 ValueError
        # raise. forecast_service의 REST 경로와 동일하게 누락 컬럼 0.0 폴백.
        if self.forecaster.name != "ml":
            return ForecastInput(features=self._controls_to_features(controls))
        # 지역 import — 모듈 import 순환 방지 + lazy 의존성.
        from digital_twin.forecaster.predict import DWATT_COL, TTXM_COL
        from digital_twin.forecaster.preprocess import NOX_TARGET_COL, RAW_FEATURES
        recent_df = session.context.buffer_to_df()
        if recent_df.empty:
            # cold start — buffer 비어 있으면 features dict로 graceful degrade.
            return ForecastInput(features=self._controls_to_features(controls))
        required = set(RAW_FEATURES) | {TTXM_COL, NOX_TARGET_COL, DWATT_COL}
        for col in required - set(recent_df.columns):
            recent_df[col] = 0.0
        return ForecastInput(recent_df=recent_df)

    def _build_forecast_payload(
        self, predicted_nox: float, o2_pct: float | None
    ) -> dict[str, Any]:
        # threshold_exceeded는 raw 기준 — current 임계 비교와 단위 일관성 유지.
        # frontend ForecastCard는 표시값(predicted_nox_15pct)으로 delta/색상 판정.
        threshold = self.dt_config.thresholds.nox_warning_ppm
        target = datetime.now(timezone.utc) + timedelta(minutes=FORECAST_HORIZON_MINUTES)
        return {
            "predicted_nox": round(predicted_nox, 3),
            "predicted_nox_15pct": round(correct_nox_15pct(predicted_nox, o2_pct), 3),
            "target_time": target.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "threshold_value": threshold,
            "threshold_exceeded": predicted_nox > threshold,
        }

    def _build_payload(
        self,
        *,
        session: Session,
        input_controls: ControlVars,
        current_outputs: OutputVars,
        override_active: bool,
        kafka_controls: ControlVars,
        kafka_ts: Any,
        forecast_payload: dict[str, Any] | None,
        warning: str | None,
        o2_pct: float | None = None,
    ) -> dict[str, Any]:
        now_iso = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        controls_dict = self._controls_to_features(input_controls)
        outputs_dict = {
            "nox": current_outputs.nox,
            "nox_15pct": correct_nox_15pct(current_outputs.nox, o2_pct),
            "exhaust_temp": current_outputs.exhaust_temp,
            "power": current_outputs.power,
            "lambda_": current_outputs.lambda_,
            "efficiency": current_outputs.efficiency,
        }
        kafka_latest_dict = None
        if override_active:
            # spec §2.2 — kafka_latest.ts는 Kafka 메시지의 measured_at(센서 측정 시각).
            # 보존 실패 시에만 wall-clock으로 폴백.
            kafka_latest_dict = {
                "controls": self._controls_to_features(kafka_controls),
                "ts": kafka_ts if isinstance(kafka_ts, str) and kafka_ts else now_iso,
            }
        return {
            "v": 1,
            "sid": session.sid,
            "tick": session.tick,
            "ts": now_iso,
            "mode": session.mode,
            "override_active": override_active,
            "current": {"controls": controls_dict, "outputs": outputs_dict},
            "kafka_latest": kafka_latest_dict,
            "forecast": forecast_payload,
            "warning": warning,
        }
