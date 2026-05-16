import type { RealtimeStreamPayload } from './mockConsole'
import { isForecastReady } from './mockConsole'

type ForecastPayload = NonNullable<RealtimeStreamPayload['forecast']>

/**
 * ForecastCard warmup gate + latch 상태.
 *
 * - `lastReady` : 마지막으로 ready였던 forecast (없으면 null = 아직 latch 전)
 */
export interface ForecastStickyState {
  lastReady: ForecastPayload | null
}

export const initialForecastStickyState: ForecastStickyState = {
  lastReady: null,
}

// WS payload는 1Hz. 세션(재)연결 직후 이 tick 수만큼은 forecast가 와도
// 무조건 "준비 중"으로 표시한다(warmup gate). 새로고침 직후 짧은 구간에
// 세션 재생성/sticky 전이 등으로 "값 ↔ 준비 중"이 깜빡이는 것을 통째로
// 흡수한다 — 이 게이트 안에서 일어나는 모든 전이는 화면에 노출되지 않는다.
export const FORECAST_WARMUP_TICKS = 10

export interface ForecastStickyStep {
  /** 이 payload 반영 후 다음 state (참조 동일하면 추가 리렌더 없음) */
  next: ForecastStickyState
  /** 화면에 표시할 forecast — null이면 "준비 중" 폴백 */
  effective: ForecastPayload | null
}

/**
 * payload 1개를 warmup gate + latch 상태에 반영하고, 그 즉시 표시할
 * forecast까지 함께 반환하는 단일 순수 함수.
 *
 * 정책 (사용자 요구: "처음엔 의도적으로 준비 중, 실제 값이 확인되면 값"):
 *
 * - warmup gate 내(elapsedTicks < FORECAST_WARMUP_TICKS)
 *     : forecast가 ready여도 표시하지 않고 "준비 중"(null) 유지.
 *       단, ready면 lastReady에는 적재해 둬 게이트 종료 즉시 값이 뜨게 한다.
 * - gate 종료 후 ready : lastReady 갱신, 그 forecast 즉시 표시
 * - gate 종료 후 not-ready & lastReady 있음 : 직전 ready forecast를 영구 hold
 *       (한 번 latch되면 not-ready/warning이 와도 "준비 중"으로 되돌아가지
 *        않는다 — "값 → 준비 중 → 값" 깜빡임 원천 차단)
 * - lastReady 없음 : "준비 중"(null)
 *
 * state가 실제로 바뀌지 않으면 prev를 그대로 돌려줘 불필요한 리렌더를 막는다.
 *
 * @param elapsedTicks 세션(재)연결 후 누적된 WS payload 수 (1Hz ≈ 초)
 */
export function stepForecastSticky(
  prev: ForecastStickyState,
  forecast: RealtimeStreamPayload['forecast'],
  warning: RealtimeStreamPayload['warning'],
  elapsedTicks: number,
): ForecastStickyStep {
  const ready = isForecastReady(forecast, warning)

  // ready면 게이트 중이라도 lastReady에 적재 — 게이트 종료 즉시 표시되도록.
  const next: ForecastStickyState =
    ready && prev.lastReady !== forecast ? { lastReady: forecast } : prev

  // warmup gate 내에서는 무조건 "준비 중".
  if (elapsedTicks < FORECAST_WARMUP_TICKS) {
    return { next, effective: null }
  }

  // gate 종료 — ready면 방금 적재된 값, not-ready면 마지막 latch 값을
  // 영구 hold. 둘 다 next.lastReady로 수렴(아직 한 번도 ready 전이면 null).
  return { next, effective: next.lastReady }
}
