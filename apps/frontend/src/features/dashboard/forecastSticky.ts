import type { RealtimeStreamPayload } from './mockConsole'
import { isForecastReady } from './mockConsole'

type ForecastPayload = NonNullable<RealtimeStreamPayload['forecast']>

/**
 * ForecastCard sticky 디바운스 상태.
 *
 * - `lastReady` : 마지막으로 ready였던 forecast (없으면 null)
 * - `notReadyStreak` : 연속 not-ready payload 수 (ready 들어오면 0)
 */
export interface ForecastStickyState {
  lastReady: ForecastPayload | null
  notReadyStreak: number
}

export const initialForecastStickyState: ForecastStickyState = {
  lastReady: null,
  notReadyStreak: 0,
}

// WS payload는 1Hz. not-ready가 이 횟수(약 4초) 연속될 때만 "준비 중"으로 폴백.
// 백엔드 stale grace보다 짧게 잡아, 백엔드가 hold 못 하는 짧은 공백도
// 프론트에서 한 번 더 흡수하는 이중 방어.
export const FORECAST_STICKY_TICKS = 4

export interface ForecastStickyStep {
  /** 이 payload 반영 후 다음 state (참조 동일하면 추가 리렌더 없음) */
  next: ForecastStickyState
  /** 화면에 표시할 forecast — null이면 "준비 중" 폴백 */
  effective: ForecastPayload | null
}

/**
 * payload 1개를 sticky 상태에 반영하고, 그 즉시 표시할 forecast까지 함께
 * 반환하는 단일 순수 함수. state 갱신과 표시 판정을 한 곳에 모아
 * (reduce → resolve 2단계의) 한 렌더 지연 / grace 경계 불일치를 제거한다.
 *
 * - ready              : lastReady 갱신·streak 0, 그 forecast 즉시 표시
 * - not-ready & grace내 : streak 증가, 직전 ready forecast를 hold (깜빡임 차단)
 * - not-ready & grace초과: streak 증가, null → "준비 중" 폴백
 * - lastReady 없음(warmup 전): state 불변, null
 *
 * state가 실제로 바뀌지 않으면 prev를 그대로 돌려줘 불필요한 리렌더를 막는다.
 */
export function stepForecastSticky(
  prev: ForecastStickyState,
  forecast: RealtimeStreamPayload['forecast'],
  warning: RealtimeStreamPayload['warning'],
): ForecastStickyStep {
  if (isForecastReady(forecast, warning)) {
    const next =
      prev.lastReady === forecast && prev.notReadyStreak === 0
        ? prev
        : { lastReady: forecast, notReadyStreak: 0 }
    return { next, effective: forecast }
  }

  // 한 번도 ready였던 적이 없으면 (새 세션 warmup 전) hold할 값이 없다.
  if (prev.lastReady === null) {
    return { next: prev, effective: null }
  }

  const notReadyStreak = prev.notReadyStreak + 1
  const next: ForecastStickyState = { lastReady: prev.lastReady, notReadyStreak }
  const effective =
    notReadyStreak <= FORECAST_STICKY_TICKS ? prev.lastReady : null
  return { next, effective }
}
