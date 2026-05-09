import { describe, it, expect } from 'vitest'
import { getFlowAnimationVars } from './flowVarsMap'

describe('getFlowAnimationVars', () => {
  it('정규화 0.05 → state=paused', () => {
    const v = getFlowAnimationVars({ fuel: 0.05, nox: 0.5, air: 0.5 })
    expect(v['--flow-fuel-state']).toBe('paused')
  })

  it('정규화 0.30 → low (2.5s)', () => {
    const v = getFlowAnimationVars({ fuel: 0.30, nox: 0.30, air: 0.30 })
    expect(v['--flow-fuel-duration']).toBe('2.5s')
    expect(v['--flow-fuel-state']).toBe('running')
  })

  it('정규화 0.55 → mid (1.2s)', () => {
    const v = getFlowAnimationVars({ fuel: 0.55, nox: 0.55, air: 0.55 })
    expect(v['--flow-fuel-duration']).toBe('1.2s')
  })

  it('정규화 0.85 → high (0.5s)', () => {
    const v = getFlowAnimationVars({ fuel: 0.85, nox: 0.85, air: 0.85 })
    expect(v['--flow-fuel-duration']).toBe('0.5s')
  })

  it('flow-cards는 항상 1.2s, running', () => {
    const a = getFlowAnimationVars({ fuel: 0.05, nox: 0.05, air: 0.05 })
    const b = getFlowAnimationVars({ fuel: 0.95, nox: 0.95, air: 0.95 })
    expect(a['--flow-cards-duration']).toBe('1.2s')
    expect(a['--flow-cards-state']).toBe('running')
    expect(b['--flow-cards-duration']).toBe('1.2s')
  })

  it('각 입력 독립 매핑', () => {
    const v = getFlowAnimationVars({ fuel: 0.85, nox: 0.30, air: 0.05 })
    expect(v['--flow-fuel-duration']).toBe('0.5s')
    expect(v['--flow-nox-duration']).toBe('2.5s')
    expect(v['--flow-air-state']).toBe('paused')
  })

  it('NaN 입력 → paused', () => {
    const v = getFlowAnimationVars({ fuel: NaN, nox: 0.5, air: 0.5 })
    expect(v['--flow-fuel-state']).toBe('paused')
  })
})
