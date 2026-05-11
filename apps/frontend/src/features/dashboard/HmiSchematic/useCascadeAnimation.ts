import { useEffect, useRef, type RefObject } from 'react'

export interface CascadeTriggerArgs {
  thresholdRatio: number
  debounceMs: number
  onTrigger: () => void
}

export interface CascadeTrigger {
  notify(value: number, nowMs: number): void
}

// n2Flow가 (이전 값) 대비 thresholdRatio 이상 증가하고
// 마지막 trigger 후 debounceMs가 경과했으면 onTrigger 호출.
export function createCascadeTrigger(args: CascadeTriggerArgs): CascadeTrigger {
  let prev: number | null = null
  let lastTriggerAt = -Infinity
  return {
    notify(value, nowMs) {
      if (prev != null && Number.isFinite(prev) && prev > 0 && Number.isFinite(value)) {
        const ratio = (value - prev) / prev
        if (ratio >= args.thresholdRatio && nowMs - lastTriggerAt >= args.debounceMs) {
          lastTriggerAt = nowMs
          args.onTrigger()
        }
      }
      prev = value
    },
  }
}

const CASCADE_FRAMES: Keyframe[] = [
  { filter: 'drop-shadow(0 0 0 transparent)', offset: 0 },
  { filter: 'drop-shadow(0 0 12px rgba(120,200,255,0.95))', offset: 0.4 },
  { filter: 'drop-shadow(0 0 0 transparent)', offset: 1 },
]
const CASCADE_OPTS: KeyframeAnimationOptions = {
  duration: 1200,
  easing: 'ease-out',
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

export function useCascadeAnimation(
  n2Flow: number,
  rootRef: RefObject<HTMLElement | null>,
): void {
  const triggerRef = useRef<CascadeTrigger | null>(null)

  useEffect(() => {
    if (triggerRef.current != null) return
    triggerRef.current = createCascadeTrigger({
      thresholdRatio: 0.05,
      debounceMs: 800,
      onTrigger: () => {
        const root = rootRef.current
        if (!root) return
        if (prefersReducedMotion()) return
        for (const i of [1, 2, 3]) {
          const el = root.querySelector(`[data-role="cascade-${i}"]`)
          if (el && 'animate' in el) {
            ;(el as Element).animate(CASCADE_FRAMES, {
              ...CASCADE_OPTS,
              delay: (i - 1) * 300,
            })
          }
        }
      },
    })
  }, [rootRef])

  useEffect(() => {
    triggerRef.current?.notify(n2Flow, performance.now())
  }, [n2Flow])
}
