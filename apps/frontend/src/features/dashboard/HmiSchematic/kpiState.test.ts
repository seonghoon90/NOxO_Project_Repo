import { describe, it, expect } from 'vitest'
import { computeKpiStates } from './kpiState'

describe('computeKpiStates', () => {
  it('nox: 10→normal, 27→warn, 35→crit', () => {
    expect(computeKpiStates({ nox: 10, ttxm: 580, dwatt: 240, lambda: 1.10 }).nox).toBe('normal')
    expect(computeKpiStates({ nox: 27, ttxm: 580, dwatt: 240, lambda: 1.10 }).nox).toBe('warn')
    expect(computeKpiStates({ nox: 35, ttxm: 580, dwatt: 240, lambda: 1.10 }).nox).toBe('crit')
  })

  it('nox 경계값: 25=warn, 30=crit, 24.99=normal, 29.99=warn', () => {
    const f = (n: number) => computeKpiStates({ nox: n, ttxm: 580, dwatt: 240, lambda: 1.10 }).nox
    expect(f(24.99)).toBe('normal')
    expect(f(25)).toBe('warn')
    expect(f(29.99)).toBe('warn')
    expect(f(30)).toBe('crit')
  })

  it('ttxm 경계값: 599=normal, 600=warn, 619=warn, 620=crit, 625=crit', () => {
    const f = (t: number) => computeKpiStates({ nox: 0, ttxm: t, dwatt: 240, lambda: 1.10 }).ttxm
    expect(f(599)).toBe('normal')
    expect(f(600)).toBe('warn')
    expect(f(619)).toBe('warn')
    expect(f(620)).toBe('crit')
    expect(f(625)).toBe('crit')
  })

  it('dwatt 양방향: 180=crit, 195=warn, 210=normal, 270=normal, 285=warn, 305=crit', () => {
    const f = (d: number) => computeKpiStates({ nox: 0, ttxm: 580, dwatt: d, lambda: 1.10 }).dwatt
    expect(f(180)).toBe('crit')
    expect(f(195)).toBe('warn')
    expect(f(210)).toBe('normal')
    expect(f(270)).toBe('normal')
    expect(f(285)).toBe('warn')
    expect(f(305)).toBe('crit')
  })

  it('lambda 양방향: 0.95=crit, 1.02=warn, 1.10=normal, 1.22=warn, 1.30=crit', () => {
    const f = (l: number) => computeKpiStates({ nox: 0, ttxm: 580, dwatt: 240, lambda: l }).lambda
    expect(f(0.95)).toBe('crit')
    expect(f(1.02)).toBe('warn')
    expect(f(1.10)).toBe('normal')
    expect(f(1.22)).toBe('warn')
    expect(f(1.30)).toBe('crit')
  })

  it('NaN/Infinity 입력 → normal', () => {
    expect(computeKpiStates({ nox: NaN, ttxm: 580, dwatt: 240, lambda: 1.10 }).nox).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: Infinity, dwatt: 240, lambda: 1.10 }).ttxm).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: 580, dwatt: NaN, lambda: 1.10 }).dwatt).toBe('normal')
    expect(computeKpiStates({ nox: 0, ttxm: 580, dwatt: 240, lambda: -Infinity }).lambda).toBe('normal')
  })
})
