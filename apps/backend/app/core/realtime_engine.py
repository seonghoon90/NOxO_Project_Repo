"""1초 tick 통합 엔진.

모든 활성 세션을 1개 asyncio task가 순회하며 mode/override 기반으로 추론한다.
세션별 sim_loop 모델(폐기) → 전역 1 tick 모델로 단일화 (spec §5).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from app.adapters.forecaster import Forecaster, ForecastInput
from app.adapters.simulator import Simulator
from app.config import Settings
from app.core.sensor_buffer import SensorBuffer
from app.core.session import Session
from app.core.ws_manager import WebSocketManager
from digital_twin.simulation import (
    DEFAULT_CONFIG,
    ControlVars,
    DTConfig,
    OutputVars,
)
from digital_twin.simulation.features import compute_lambda

logger = logging.getLogger(__name__)

FORECAST_HORIZON_MINUTES = 5  # spec §0.2


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
            loop = asyncio.get_event_loop()
            next_deadline = loop.time()
            while self._stop_event is not None and not self._stop_event.is_set():
                await self._tick()
                # deadline 기반 — _tick 처리 시간만큼 sleep 단축해 drift 방지
                next_deadline += self.tick_interval
                delay = max(0.0, next_deadline - loop.time())
                if delay == 0.0:
                    # 처리가 tick보다 느리면 다음 deadline을 현재 시각으로 리셋
                    next_deadline = loop.time()
                await asyncio.sleep(delay)
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
        op = self.dt_config.operating_point
        return {
            "syngas_flow": op.syngas_flow,
            "igv_opening": op.igv_opening,
            "n2_offset": op.n2_offset,
            "n2_valve_1": op.n2_valve_1,
            "syngas_srv": op.syngas_srv,
            "syngas_gcv_1": op.syngas_gcv_1,
            "syngas_gcv_1a": op.syngas_gcv_1a,
            "syngas_gcv_2": op.syngas_gcv_2,
            "ibh_valve": op.ibh_valve,
            "n2_flow": op.n2_flow,
            "exhaust_temp": op.exhaust_temp,
        }

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

        # 2. SessionContext.recent_df_buffer 갱신 (외란 + 사용된 제어)
        synthesized = self._synthesize_row(kafka_row, input_controls)
        session.context.recent_df_buffer.append(synthesized)

        # 3. DT current 추론 + lambda_/efficiency 후처리
        ml_outputs = self.simulator.predict_for_session(
            input_controls, session.context
        )
        current_outputs = self._postprocess_outputs(ml_outputs, input_controls)

        # 4. realtime 모드면 forecast
        forecast_payload = None
        warning = None
        if session.mode == "realtime":
            if stream_stale:
                # spec §2.3 — Kafka stream 끊김 시 realtime 모드는 warning 채움
                warning = "kafka stream stale"
            else:
                try:
                    features = self._controls_to_features(input_controls)
                    predicted = self.forecaster.predict(ForecastInput(features=features))
                    forecast_payload = self._build_forecast_payload(predicted)
                except Exception as exc:
                    logger.warning("forecast_failed sid=%s err=%s", session.sid, exc)
                    warning = "forecast unavailable"

        # 5. payload 조립
        return self._build_payload(
            session=session,
            input_controls=input_controls,
            current_outputs=current_outputs,
            override_active=override_active,
            kafka_controls=kafka_controls,
            kafka_ts=kafka_row.get("measured_at"),
            forecast_payload=forecast_payload,
            warning=warning,
        )

    def _postprocess_outputs(
        self, ml_outputs: OutputVars, controls: ControlVars
    ) -> OutputVars:
        """ML 출력의 lambda_/efficiency 덮어쓰기.

        ML 모델은 두 필드를 학습 타깃에 포함하지 않으므로 dummy(0.0)를 반환한다.
        - lambda_ : digital_twin.simulation.features.compute_lambda로 재계산
        - efficiency: power / (syngas_flow × syngas_lhv) 후처리 + [0,1] 클램프
        StubSimulator는 자체 lambda_/efficiency를 반환하지만, 일관성을 위해 모든
        simulator 출력에 동일 후처리를 적용한다 (Stub의 lambda_/efficiency도 동일식).
        """
        lambda_ = compute_lambda(
            syngas_flow=controls.syngas_flow,
            n2_offset=controls.n2_offset,
            igv_opening=controls.igv_opening,
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
        self, kafka_row: dict[str, Any], input_controls: ControlVars
    ) -> dict[str, Any]:
        """외란(kafka) + input_controls 합쳐 한 행 dict 반환 — recent_df_buffer용.

        SessionContext.recent_df_buffer는 원천 태그(IGCC.*) 네임스페이스로 운영된다
        (RAW_FEATURES + TTXM). kafka_row는 normalize_raw_message가 만든 도메인
        snake_case이므로 denormalize로 되돌리고, 제어값은 control_vars_to_tag_dict로
        덮어쓴다. measured_at 등 비태그 키는 제거(원천 태그 dict로만).
        """
        from app.domain.tags import control_vars_to_tag_dict, denormalize_to_raw_tags

        merged_raw = denormalize_to_raw_tags(
            {k: v for k, v in kafka_row.items() if k != "measured_at"}
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

    def _build_forecast_payload(self, predicted_nox: float) -> dict[str, Any]:
        threshold = self.dt_config.thresholds.nox_warning_ppm
        target = datetime.now(timezone.utc) + timedelta(minutes=FORECAST_HORIZON_MINUTES)
        return {
            "predicted_nox": round(predicted_nox, 3),
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
    ) -> dict[str, Any]:
        now_iso = (
            datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        controls_dict = self._controls_to_features(input_controls)
        outputs_dict = {
            "nox": current_outputs.nox,
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
