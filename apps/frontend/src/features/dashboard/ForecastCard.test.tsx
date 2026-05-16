import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { ForecastCard } from '../../pages/ServicePage'
import { FORECAST_WARMUP_TICKS } from './forecastSticky'
import type { RealtimeStreamPayload } from './mockConsole'

function fc(value: number): NonNullable<RealtimeStreamPayload['forecast']> {
  return {
    predicted_nox: value,
    predicted_nox_15pct: value,
    target_time: '2026-05-16T00:05:00Z',
    threshold_exceeded: false,
  } as NonNullable<RealtimeStreamPayload['forecast']>
}

const READY = '예측 모델 준비 중...'

// WS payload 1개 = tick +1. 실제 런타임 동작을 모사하는 렌더 헬퍼.
// 첫 tick=1이 baseTick이 되므로, 게이트(elapsed >= FORECAST_WARMUP_TICKS)는
// (FORECAST_WARMUP_TICKS + 1)번째 payload부터 종료된다.
function makeFeed() {
  let tick = 0
  return {
    next(
      forecast: RealtimeStreamPayload['forecast'],
      warning: RealtimeStreamPayload['warning'],
    ) {
      tick += 1
      return (
        <ForecastCard
          forecast={forecast}
          warning={warning}
          tick={tick}
          noxLimit={50}
          currentNox={15.5}
        />
      )
    },
  }
}

describe('ForecastCard warmup gate + latch (컴포넌트 레벨)', () => {
  it('새로고침 직후 gate 동안은 정상 forecast가 와도 "준비 중"', () => {
    const feed = makeFeed()
    const { container } = render(feed.next(fc(12.1), null))
    expect(container.textContent).toContain(READY)
    expect(container.textContent).not.toContain('12')
  })

  it('gate 내내 정상값이 와도 "준비 중" 유지', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    for (let i = 1; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(fc(12.1), null))
      expect(container.textContent).toContain(READY)
    }
  })

  it('gate 종료 후 정상 forecast면 값을 표시한다', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    // baseTick=1. elapsed가 FORECAST_WARMUP_TICKS에 도달할 때까지 진행.
    for (let i = 0; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(fc(12.1), null))
    }
    expect(container.textContent).toContain('12')
    expect(container.textContent).not.toContain(READY)
  })

  it('latch 후 단발 stale payload 1개로는 깜빡이지 않는다 (영구 hold)', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    for (let i = 0; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(fc(12.1), null))
    }
    expect(container.textContent).toContain('12') // latch 완료
    rerender(feed.next(null, 'kafka stream stale'))
    expect(container.textContent).not.toContain(READY)
    expect(container.textContent).toContain('12') // 직전 값 영구 hold
  })

  it('latch 후 지속 stale이어도 "준비 중"으로 되돌아가지 않는다', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    for (let i = 0; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(fc(12.1), null))
    }
    expect(container.textContent).toContain('12')
    // grace 없이 영구 hold — 100틱 stale에도 값 유지
    for (let i = 0; i < 100; i += 1) {
      rerender(feed.next(null, 'kafka stream stale'))
      expect(container.textContent).not.toContain(READY)
    }
  })

  it('latch 후 새 정상값이 오면 그 값으로 갱신된다', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    for (let i = 0; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(fc(12.1), null))
    }
    expect(container.textContent).toContain('12')
    rerender(feed.next(fc(13.4), null))
    expect(container.textContent).toContain('13')
  })

  it('gate 동안 ready 적재 → 종료 후 not-ready여도 적재값 표시', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    // gate 내 ready 한 번 (적재만, 표시 X)
    rerender(feed.next(fc(12.1), null))
    expect(container.textContent).toContain(READY)
    // 나머지 gate 동안 not-ready
    for (let i = 2; i < FORECAST_WARMUP_TICKS; i += 1) {
      rerender(feed.next(null, 'forecast warmup'))
    }
    // 게이트 종료 — not-ready지만 적재해 둔 12.1을 hold
    rerender(feed.next(null, 'forecast warmup'))
    expect(container.textContent).toContain('12')
    expect(container.textContent).not.toContain(READY)
  })

  it('gate 종료까지 한 번도 ready 없으면 "준비 중" 유지', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(null, 'forecast warmup'))
    for (let i = 0; i < FORECAST_WARMUP_TICKS + 2; i += 1) {
      rerender(feed.next(null, 'forecast warmup'))
    }
    expect(container.textContent).toContain(READY)
  })
})
