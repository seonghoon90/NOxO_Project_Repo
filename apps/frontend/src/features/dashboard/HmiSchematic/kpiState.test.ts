import { describe, it, expect } from 'vitest'
import { computeKpiStates, type KpiThresholds } from './kpiState'

// SoT(digital_twin/simulation/config.py)와 정합한 운영 임계
const TH: KpiThresholds = {
  noxWarn: 25,
  noxCrit: 30,
  ttxmWarn: 642,
  ttxmCrit: 650,
  lambdaWarnLo: 2.0,
  lambdaWarnHi: 3.5,
  lambdaCritLo: 1.5,
  lambdaCritHi: 4.0,
}

describe('computeKpiStates', () => {
  it('nox: 10→normal, 27→warn, 35→crit', () => {
    expect(computeKpiStates({ nox: 10, ttxm: 580, dwatt: 240, lambda: 2.5 }, TH).nox).toBe('normal')
    expect(computeKpiStates({ nox: 27, ttxm: 580, dwatt: 240, lambda: 2.5 }, TH).nox).toBe('warn')
    expect(computeKpiStates({ nox: 35, ttxm: 580, dwatt: 240, lambda: 2.5 }, TH).nox).toBe('crit')
  })

  it('nox 경계값: 25=warn, 30=crit, 24.99=normal, 29.99=warn', () => {
    const f = (n: number) => computeKpiStates({ nox: n, ttxm: 580, dwatt: 240, lambda: 2.5 }, TH).nox
    expect(f(24.99)).toBe('normal')
    expect(f(25)).toBe('warn')
    expect(f(29.99)).toBe('warn')
    expect(f(30)).toBe('crit')
  })

  it('ttxm 경계값: 641=normal, 642=warn, 649=warn, 650=crit, 655=crit', () => {
    const f = (t: number) => computeKpiStates({ nox: 0, ttxm: t, dwatt: 240, lambda: 2.5 }, TH).ttxm
    expect(f(641)).toBe('normal')
    expect(f(642)).toBe('warn')
    expect(f(649)).toBe('warn')
    expect(f(650)).toBe('crit')
    expect(f(655)).toBe('crit')
  })

  it('dwatt 양방향: 180=crit, 195=warn, 210=normal, 270=normal, 285=warn, 305=crit', () => {
    const f = (d: number) => computeKpiStates({ nox: 0, ttxm: 580, dwatt: d, lambda: 2.5 }, TH).dwatt
    expect(f(180)).toBe('crit')
    expect(f(195)).toBe('warn')
    expect(f(210)).toBe('normal')
    expect(f(270)).toBe('normal')
    expect(f(285)).toBe('warn')
    expect(f(305)).toBe('crit')
  })

  it('lambda 양방향: 1.4=crit, 1.8=warn, 2.5=normal, 3.7=warn, 4.0=crit', () => {
    const f = (l: number) => computeKpiStates({ nox: 0, ttxm: 580, dwatt: 240, lambda: l }, TH).lambda
    expect(f(1.4)).toBe('crit')
    expect(f(1.8)).toBe('warn')
    expect(f(2.5)).toBe('normal')
    expect(f(3.7)).toBe('warn')
    expect(f(4.0)).toBe('crit')
  })

  it('NaN/Infinity 입력 → normal', () => {
    expect(computeKpiStates({ nox: NaN, ttxm: 580, dwatt: 240, lambda: 2.5 }, TH).nox).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: Infinity, dwatt: 240, lambda: 2.5 }, TH).ttxm).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: 580, dwatt: NaN, lambda: 2.5 }, TH).dwatt).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: 580, dwatt: 240, lambda: -Infinity }, TH).lambda).toBe('normal')
  })
})
