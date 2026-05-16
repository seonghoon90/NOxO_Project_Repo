import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { ForecastCard } from '../../pages/ServicePage'
import { FORECAST_STICKY_TICKS } from './forecastSticky'
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

describe('ForecastCard sticky 디바운스 (컴포넌트 레벨)', () => {
  it('정상 forecast면 값을 표시한다', () => {
    const feed = makeFeed()
    const { container } = render(feed.next(fc(12.1), null))
    expect(container.textContent).toContain('12')
    expect(container.textContent).not.toContain(READY)
  })

  it('한 번 ready 후 단발 stale payload 1개로는 깜빡이지 않는다', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    rerender(feed.next(null, 'kafka stream stale'))
    expect(container.textContent).not.toContain(READY)
    expect(container.textContent).toContain('12') // 직전 값 hold
  })

  it(`stale이 grace 한도(${FORECAST_STICKY_TICKS})를 초과하면 "준비 중"으로 폴백한다`, () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    // streak 1..한도까지는 hold (깜빡임 없음)
    for (let i = 0; i < FORECAST_STICKY_TICKS; i += 1) {
      rerender(feed.next(null, 'kafka stream stale'))
      expect(container.textContent).not.toContain(READY)
    }
    // 한도 초과 step — 폴백
    rerender(feed.next(null, 'kafka stream stale'))
    expect(container.textContent).toContain(READY)
  })

  it('stale 도중 정상 payload가 오면 즉시 값으로 복귀한다', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    rerender(feed.next(null, 'kafka stream stale'))
    rerender(feed.next(fc(13.4), null))
    expect(container.textContent).toContain('13')
    expect(container.textContent).not.toContain(READY)
  })

  it('한 번도 ready였던 적 없으면 (새 세션 warmup 전) "준비 중"을 표시한다', () => {
    const feed = makeFeed()
    const { container } = render(feed.next(null, 'forecast warmup'))
    expect(container.textContent).toContain(READY)
  })

  it('지속 stale 후 stream 복귀: 폴백 → 정상값으로 회복', () => {
    const feed = makeFeed()
    const { container, rerender } = render(feed.next(fc(12.1), null))
    for (let i = 0; i <= FORECAST_STICKY_TICKS; i += 1) {
      rerender(feed.next(null, 'kafka stream stale'))
    }
    expect(container.textContent).toContain(READY) // 폴백됨
    rerender(feed.next(fc(14.2), null)) // stream 복귀
    expect(container.textContent).toContain('14')
    expect(container.textContent).not.toContain(READY)
  })
})
