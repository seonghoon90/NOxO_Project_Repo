import { describe, expect, it } from 'vitest'
import type { RealtimeStreamPayload } from './mockConsole'
import {
  FORECAST_STICKY_TICKS,
  initialForecastStickyState,
  stepForecastSticky,
  type ForecastStickyState,
} from './forecastSticky'

function fc(value: number): NonNullable<RealtimeStreamPayload['forecast']> {
  return {
    predicted_nox: value,
    predicted_nox_15pct: value,
    target_time: '2026-05-16T00:05:00Z',
    threshold_exceeded: false,
  } as NonNullable<RealtimeStreamPayload['forecast']>
}

describe('stepForecastSticky', () => {
  it('ready payload면 lastReady 갱신·streak 0, 그 forecast를 즉시 표시', () => {
    const f = fc(12.1)
    const { next, effective } = stepForecastSticky(
      initialForecastStickyState,
      f,
      null,
    )
    expect(next.lastReady).toBe(f)
    expect(next.notReadyStreak).toBe(0)
    expect(effective).toBe(f)
  })

  it('not-ready & grace 이내면 직전 ready forecast를 hold (깜빡임 차단)', () => {
    const last = fc(12.1)
    const prev: ForecastStickyState = { lastReady: last, notReadyStreak: 0 }
    const { next, effective } = stepForecastSticky(
      prev,
      null,
      'kafka stream stale',
    )
    expect(next.notReadyStreak).toBe(1)
    expect(effective).toBe(last) // 한 렌더 지연 없이 이번 step에서 hold
  })

  it('streak가 grace 한도를 초과하는 step에서 null → 준비 중 폴백', () => {
    const prev: ForecastStickyState = {
      lastReady: fc(12.1),
      notReadyStreak: FORECAST_STICKY_TICKS, // 이번 step에서 +1 → 초과
    }
    const { next, effective } = stepForecastSticky(prev, null, 'kafka stream stale')
    expect(next.notReadyStreak).toBe(FORECAST_STICKY_TICKS + 1)
    expect(effective).toBeNull()
  })

  it('grace 경계: streak가 정확히 한도면 아직 hold (off-by-one 가드)', () => {
    const last = fc(12.1)
    const prev: ForecastStickyState = {
      lastReady: last,
      notReadyStreak: FORECAST_STICKY_TICKS - 1, // 이번 step에서 +1 → 정확히 한도
    }
    const { effective } = stepForecastSticky(prev, null, 'kafka stream stale')
    expect(effective).toBe(last)
  })

  it('한 번도 ready였던 적 없으면 state 불변 + null', () => {
    const { next, effective } = stepForecastSticky(
      initialForecastStickyState,
      null,
      'forecast warmup',
    )
    expect(next).toBe(initialForecastStickyState)
    expect(effective).toBeNull()
  })

  it('동일 ready forecast 재수신 시 prev state를 그대로 반환 (불필요 리렌더 방지)', () => {
    const f = fc(12.1)
    const prev: ForecastStickyState = { lastReady: f, notReadyStreak: 0 }
    const { next } = stepForecastSticky(prev, f, null)
    expect(next).toBe(prev)
  })

  it('단발 stale 시나리오: 값 → stale 1개 → 값 (깜빡임 없이 유지)', () => {
    let state = initialForecastStickyState
    const v1 = fc(12.1)
    let s = stepForecastSticky(state, v1, null)
    expect(s.effective).toBe(v1)
    state = s.next

    // 단발 stale payload — 깜빡이면 안 됨
    s = stepForecastSticky(state, null, 'kafka stream stale')
    expect(s.effective).toBe(v1)
    state = s.next

    // 다시 정상값
    const v2 = fc(13.4)
    s = stepForecastSticky(state, v2, null)
    expect(s.effective).toBe(v2)
  })

  it('새로고침 직후 stale 버스트: warmup 전 stale은 준비 중, latch 후엔 hold', () => {
    let state = initialForecastStickyState
    // warmup 전 — lastReady 없음 → 준비 중
    let s = stepForecastSticky(state, null, 'forecast warmup')
    expect(s.effective).toBeNull()
    state = s.next

    // 첫 정상 예측 (latch)
    const v = fc(12.1)
    s = stepForecastSticky(state, v, null)
    expect(s.effective).toBe(v)
    state = s.next

    // 이후 stale 버스트 — grace 한도까지 hold
    for (let i = 0; i < FORECAST_STICKY_TICKS; i += 1) {
      s = stepForecastSticky(state, null, 'kafka stream stale')
      expect(s.effective).toBe(v)
      state = s.next
    }
    // 한도 초과 — 준비 중 폴백
    s = stepForecastSticky(state, null, 'kafka stream stale')
    expect(s.effective).toBeNull()
  })
})
