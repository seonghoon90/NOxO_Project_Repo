import { describe, expect, it } from 'vitest'
import type { RealtimeStreamPayload } from './mockConsole'
import {
  FORECAST_WARMUP_TICKS,
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

// gate 통과 기준 elapsedTicks (이 값 이상이면 게이트 종료)
const PAST_GATE = FORECAST_WARMUP_TICKS

describe('stepForecastSticky — warmup gate', () => {
  it('gate 내에서는 ready여도 "준비 중"(null) 표시', () => {
    const f = fc(12.1)
    const { effective } = stepForecastSticky(
      initialForecastStickyState,
      f,
      null,
      0,
    )
    expect(effective).toBeNull()
  })

  it('gate 내 ready는 lastReady에 적재해 둔다 (게이트 종료 즉시 표시되도록)', () => {
    const f = fc(12.1)
    const { next } = stepForecastSticky(initialForecastStickyState, f, null, 3)
    expect(next.lastReady).toBe(f)
  })

  it('gate 경계: elapsedTicks가 정확히 한도면 게이트 종료 (off-by-one 가드)', () => {
    const f = fc(12.1)
    const { effective } = stepForecastSticky(
      initialForecastStickyState,
      f,
      null,
      FORECAST_WARMUP_TICKS,
    )
    expect(effective).toBe(f)
  })

  it('gate 내내 not-ready여도 "준비 중" 유지', () => {
    let state = initialForecastStickyState
    for (let t = 0; t < FORECAST_WARMUP_TICKS; t += 1) {
      const s = stepForecastSticky(state, null, 'forecast warmup', t)
      expect(s.effective).toBeNull()
      state = s.next
    }
  })

  it('gate 동안 ready 적재 → 게이트 종료 tick에 즉시 그 값 표시', () => {
    let state = initialForecastStickyState
    const v = fc(12.1)
    // gate 내 ready 수신 (아직 표시 안 됨)
    let s = stepForecastSticky(state, v, null, 2)
    expect(s.effective).toBeNull()
    state = s.next
    // 게이트 종료 직후 not-ready가 와도, 적재해 둔 값을 hold
    s = stepForecastSticky(state, null, 'forecast warmup', PAST_GATE)
    expect(s.effective).toBe(v)
  })
})

describe('stepForecastSticky — latch (gate 종료 후)', () => {
  it('ready payload면 lastReady 갱신, 그 forecast 즉시 표시', () => {
    const f = fc(12.1)
    const { next, effective } = stepForecastSticky(
      initialForecastStickyState,
      f,
      null,
      PAST_GATE,
    )
    expect(next.lastReady).toBe(f)
    expect(effective).toBe(f)
  })

  it('latch 후 not-ready가 와도 마지막 ready 값을 영구 hold', () => {
    const last = fc(12.1)
    const prev: ForecastStickyState = { lastReady: last }
    const { effective } = stepForecastSticky(
      prev,
      null,
      'kafka stream stale',
      PAST_GATE,
    )
    expect(effective).toBe(last)
  })

  it('latch 후 warning이 장시간 지속돼도 "준비 중"으로 되돌아가지 않는다', () => {
    let state: ForecastStickyState = { lastReady: fc(12.1) }
    for (let i = 0; i < 100; i += 1) {
      const s = stepForecastSticky(
        state,
        null,
        'forecast warmup',
        PAST_GATE + i,
      )
      expect(s.effective).toBe(state.lastReady)
      state = s.next
    }
  })

  it('한 번도 ready였던 적 없으면 gate 종료 후에도 null', () => {
    const { next, effective } = stepForecastSticky(
      initialForecastStickyState,
      null,
      'forecast warmup',
      PAST_GATE,
    )
    expect(next).toBe(initialForecastStickyState)
    expect(effective).toBeNull()
  })

  it('동일 ready forecast 재수신 시 prev state를 그대로 반환 (불필요 리렌더 방지)', () => {
    const f = fc(12.1)
    const prev: ForecastStickyState = { lastReady: f }
    const { next } = stepForecastSticky(prev, f, null, PAST_GATE)
    expect(next).toBe(prev)
  })

  it('새 ready 값이 오면 lastReady가 그 값으로 갱신된다', () => {
    const v1 = fc(12.1)
    const v2 = fc(13.4)
    let s = stepForecastSticky(initialForecastStickyState, v1, null, PAST_GATE)
    expect(s.effective).toBe(v1)
    s = stepForecastSticky(s.next, v2, null, PAST_GATE)
    expect(s.next.lastReady).toBe(v2)
    expect(s.effective).toBe(v2)
  })
})

describe('stepForecastSticky — 전체 시나리오', () => {
  it('새로고침 직후: gate 동안 준비 중 → 종료 후 정상값 → 단발 stale에도 깜빡임 없음', () => {
    let state = initialForecastStickyState
    const v1 = fc(12.1)

    // 1) gate 동안 — backend가 정상값을 보내도 의도적으로 "준비 중"
    for (let t = 0; t < FORECAST_WARMUP_TICKS; t += 1) {
      const s = stepForecastSticky(state, v1, null, t)
      expect(s.effective).toBeNull()
      state = s.next
    }

    // 2) gate 종료 — 정상값 표시 (latch)
    let s = stepForecastSticky(state, v1, null, FORECAST_WARMUP_TICKS)
    expect(s.effective).toBe(v1)
    state = s.next

    // 3) 단발 stale — 깜빡이면 안 됨 (영구 hold)
    s = stepForecastSticky(state, null, 'kafka stream stale', FORECAST_WARMUP_TICKS + 1)
    expect(s.effective).toBe(v1)
    state = s.next

    // 4) 다시 정상값으로 자연 갱신
    const v2 = fc(13.4)
    s = stepForecastSticky(state, v2, null, FORECAST_WARMUP_TICKS + 2)
    expect(s.effective).toBe(v2)
  })
})
