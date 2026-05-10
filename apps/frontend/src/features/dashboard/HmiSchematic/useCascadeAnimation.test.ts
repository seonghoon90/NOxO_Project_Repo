import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import {
  createCascadeTrigger,
  useCascadeAnimation,
} from './useCascadeAnimation'
import { useRef } from 'react'

describe('createCascadeTrigger', () => {
  it('초기 호출은 무시 (이전 값 없음)', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, performance.now())
    expect(onTrigger).not.toHaveBeenCalled()
  })

  it('5% 이상 증가하면 trigger 호출', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, 0)
    trigger.notify(106, 100) // 6% 증가
    expect(onTrigger).toHaveBeenCalledTimes(1)
  })

  it('5% 미만 증가는 trigger 안 함', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, 0)
    trigger.notify(103, 100) // 3% 증가
    expect(onTrigger).not.toHaveBeenCalled()
  })

  it('800ms 디바운스 — 첫 trigger 후 800ms 안의 추가 증가 무시', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, 0)
    trigger.notify(110, 100)  // 10% — trigger
    trigger.notify(120, 500)  // 추가 9% — 디바운스 안
    expect(onTrigger).toHaveBeenCalledTimes(1)
  })

  it('800ms 후 다시 증가하면 재 trigger', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, 0)
    trigger.notify(110, 100)
    trigger.notify(120, 1000) // 900ms 경과 — 재 trigger
    expect(onTrigger).toHaveBeenCalledTimes(2)
  })

  it('값 감소는 trigger 안 함', () => {
    const onTrigger = vi.fn()
    const trigger = createCascadeTrigger({ thresholdRatio: 0.05, debounceMs: 800, onTrigger })
    trigger.notify(100, 0)
    trigger.notify(80, 100)
    expect(onTrigger).not.toHaveBeenCalled()
  })
})

describe('useCascadeAnimation', () => {
  let animateMock: ReturnType<typeof vi.fn>
  let originalAnimate: typeof Element.prototype.animate

  beforeEach(() => {
    animateMock = vi.fn(
      (_kf: Keyframe[], _opts?: KeyframeAnimationOptions | number) =>
        ({
          cancel: () => {},
          finish: () => {},
          play: () => {},
          pause: () => {},
          onfinish: null,
        }) as unknown as Animation,
    )
    originalAnimate = Element.prototype.animate
    Element.prototype.animate = animateMock
  })
  afterEach(() => {
    Element.prototype.animate = originalAnimate
  })

  function setup(initialFlow: number) {
    const root = document.createElement('div')
    for (const i of [1, 2, 3]) {
      const box = document.createElement('div')
      box.setAttribute('data-role', `cascade-${i}`)
      root.appendChild(box)
    }
    document.body.appendChild(root)
    const { rerender } = renderHook(
      ({ flow }: { flow: number }) => {
        const ref = useRef<HTMLElement | null>(root)
        useCascadeAnimation(flow, ref)
        return ref
      },
      { initialProps: { flow: initialFlow } },
    )
    return { rerender, root, animateMock }
  }

  it('5% 이상 증가하면 3개 element에 element.animate 호출', () => {
    const { rerender } = setup(100)
    rerender({ flow: 110 })
    expect(animateMock).toHaveBeenCalledTimes(3)
  })

  it('delay 0/300/600 정확히 부여', () => {
    const { rerender } = setup(100)
    rerender({ flow: 110 })
    const delays = animateMock.mock.calls.map((c) => {
      const opts = c[1]
      return typeof opts === 'object' && opts !== null ? opts.delay : undefined
    })
    expect(delays).toEqual([0, 300, 600])
  })

  it('동일 값 반복 → animate 호출 0건', () => {
    const { rerender } = setup(100)
    rerender({ flow: 100 })
    rerender({ flow: 100 })
    expect(animateMock).not.toHaveBeenCalled()
  })

  it('prefers-reduced-motion: reduce 시 animate 호출 0건', () => {
    const original = window.matchMedia
    window.matchMedia = ((q: string) =>
      ({
        matches: q.includes('reduce'),
        media: q,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => false,
      }) as unknown as MediaQueryList) as typeof window.matchMedia
    try {
      const { rerender } = setup(100)
      rerender({ flow: 110 })
      expect(animateMock).not.toHaveBeenCalled()
    } finally {
      window.matchMedia = original
    }
  })
})
