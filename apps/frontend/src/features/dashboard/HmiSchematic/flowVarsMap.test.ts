import { describe, it, expect } from 'vitest'
import { getFlowAnimationVars } from './flowVarsMap'

function durationSeconds(v: string): number {
  return parseFloat(v.replace('s', ''))
}

describe('getFlowAnimationVars (연속 보간)', () => {
  it('ratio < 0.05 → paused', () => {
    const v = getFlowAnimationVars({ fuel: 0.04, nox: 0.5, air: 0.5 })
    expect(v['--flow-fuel-state']).toBe('paused')
  })

  it('ratio ≥ 0.05 → running, duration 0.4~4s 범위', () => {
    const v = getFlowAnimationVars({ fuel: 0.30, nox: 0.30, air: 0.30 })
    expect(v['--flow-fuel-state']).toBe('running')
    const d = durationSeconds(v['--flow-fuel-duration'])
    expect(d).toBeGreaterThanOrEqual(0.4)
    expect(d).toBeLessThanOrEqual(4.0)
  })

  it('ratio가 클수록 duration 더 짧음 (단조 감소)', () => {
    const low = durationSeconds(getFlowAnimationVars({ fuel: 0.20, nox: 0, air: 0 })['--flow-fuel-duration'])
    const mid = durationSeconds(getFlowAnimationVars({ fuel: 0.50, nox: 0, air: 0 })['--flow-fuel-duration'])
    const high = durationSeconds(getFlowAnimationVars({ fuel: 0.90, nox: 0, air: 0 })['--flow-fuel-duration'])
    expect(low).toBeGreaterThan(mid)
    expect(mid).toBeGreaterThan(high)
  })

  it('ratio 1.0 → 약 0.4s', () => {
    const v = getFlowAnimationVars({ fuel: 1.0, nox: 0, air: 0 })
    expect(durationSeconds(v['--flow-fuel-duration'])).toBeCloseTo(0.4, 1)
  })

  it('flow-cards는 항상 1.2s, running', () => {
    const a = getFlowAnimationVars({ fuel: 0.05, nox: 0.05, air: 0.05 })
    const b = getFlowAnimationVars({ fuel: 0.95, nox: 0.95, air: 0.95 })
    expect(a['--flow-cards-duration']).toBe('1.2s')
    expect(a['--flow-cards-state']).toBe('running')
    expect(b['--flow-cards-duration']).toBe('1.2s')
  })

  it('각 입력 독립 매핑', () => {
    const v = getFlowAnimationVars({ fuel: 0.85, nox: 0.30, air: 0.04 })
    expect(v['--flow-fuel-state']).toBe('running')
    expect(v['--flow-nox-state']).toBe('running')
    expect(v['--flow-air-state']).toBe('paused')
    // fuel duration < nox duration (fuel ratio가 더 큼)
    expect(durationSeconds(v['--flow-fuel-duration'])).toBeLessThan(durationSeconds(v['--flow-nox-duration']))
  })

  it('NaN 입력 → paused', () => {
    const v = getFlowAnimationVars({ fuel: NaN, nox: 0.5, air: 0.5 })
    expect(v['--flow-fuel-state']).toBe('paused')
  })
})
