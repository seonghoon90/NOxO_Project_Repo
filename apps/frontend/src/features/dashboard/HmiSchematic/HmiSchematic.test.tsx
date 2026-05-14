import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { HmiSchematic } from './HmiSchematic'
import type { VariableConfig } from '../mockConsole'

const vc = (value: number, min: number, max: number): VariableConfig =>
  ({
    key: 'test' as never,
    label: '',
    shortLabel: '',
    rawName: '',
    value,
    min,
    max,
    digits: 1,
    unit: '',
    step: 1,
    base: value,
  } as unknown as VariableConfig)

const baseProps = {
  syngasFlow: vc(1500, 800, 2200),
  syngasSrv: vc(50, 0, 100),
  syngasGcv1: vc(50, 0, 100),
  syngasGcv1a: vc(50, 0, 100),
  syngasGcv2: vc(50, 0, 100),
  n2Offset: vc(0, -10, 10),
  n2Valve1: vc(50, 0, 100),
  n2Flow: vc(100, 0, 200),
  igvOpening: vc(50, 0, 100),
  ibhValve: vc(50, 0, 100),
  nox: 10,
  ttxm: 580,
  lambda: 2.5,
  power: 240,
  kpiThresholds: {
    noxWarn: 25,
    noxCrit: 30,
    ttxmWarn: 642,
    ttxmCrit: 650,
    lambdaWarnLo: 2.0,
    lambdaWarnHi: 3.5,
    lambdaCritLo: 1.5,
    lambdaCritHi: 4.0,
  },
}

describe('HmiSchematic', () => {
  it('마운트 시 SVG inline 렌더 (data-testid)', () => {
    const { getByTestId } = render(<HmiSchematic {...baseProps} />)
    expect(getByTestId('hmi-schematic-root')).toBeTruthy()
  })

  it('14개 <text> 렌더 (4 KPI + 10 보조), 메인 KPI textContent가 props 값과 일치', () => {
    const { container } = render(
      <HmiSchematic {...baseProps} nox={26.5} ttxm={580} power={248.6} lambda={2.50} />,
    )
    const texts = container.querySelectorAll('text[data-role^="kpi-text-"]')
    expect(texts.length).toBe(14)
    const map = new Map<string, string>()
    texts.forEach((t) => map.set(t.getAttribute('data-role')!, t.textContent ?? ''))
    expect(map.get('kpi-text-nox')).toBe('26.5')
    expect(map.get('kpi-text-ttxm')).toBe('580.0')
    expect(map.get('kpi-text-dwatt')).toBe('248.6')
    expect(map.get('kpi-text-lambda')).toBe('2.50')
  })

  it('nox=10 → data-kpi-nox=normal, 27 → warn, 35 → crit', () => {
    const { rerender, getByTestId } = render(<HmiSchematic {...baseProps} nox={10} />)
    expect(getByTestId('hmi-schematic-root').getAttribute('data-kpi-nox')).toBe('normal')
    rerender(<HmiSchematic {...baseProps} nox={27} />)
    expect(getByTestId('hmi-schematic-root').getAttribute('data-kpi-nox')).toBe('warn')
    rerender(<HmiSchematic {...baseProps} nox={35} />)
    expect(getByTestId('hmi-schematic-root').getAttribute('data-kpi-nox')).toBe('crit')
  })

  it('ttxm/dwatt/lambda 양방향 임계 반영', () => {
    const { rerender, getByTestId } = render(
      <HmiSchematic {...baseProps} ttxm={651} power={170} lambda={1.4} />,
    )
    const root = getByTestId('hmi-schematic-root')
    expect(root.getAttribute('data-kpi-ttxm')).toBe('crit')
    expect(root.getAttribute('data-kpi-dwatt')).toBe('crit')
    expect(root.getAttribute('data-kpi-lambda')).toBe('crit')
    rerender(<HmiSchematic {...baseProps} ttxm={580} power={240} lambda={2.5} />)
    expect(root.getAttribute('data-kpi-ttxm')).toBe('normal')
    expect(root.getAttribute('data-kpi-dwatt')).toBe('normal')
    expect(root.getAttribute('data-kpi-lambda')).toBe('normal')
  })

  it('NaN/Infinity 입력 → 메인 KPI text "--", state normal', () => {
    const { container, getByTestId } = render(
      <HmiSchematic {...baseProps} nox={NaN} ttxm={Infinity} power={NaN} lambda={NaN} />,
    )
    const mainKeys = ['nox', 'ttxm', 'dwatt', 'lambda']
    for (const k of mainKeys) {
      const t = container.querySelector(`text[data-role="kpi-text-${k}"]`)
      expect(t?.textContent).toBe('--')
    }
    const root = getByTestId('hmi-schematic-root')
    expect(root.getAttribute('data-kpi-nox')).toBe('normal')
    expect(root.getAttribute('data-kpi-ttxm')).toBe('normal')
    expect(root.getAttribute('data-kpi-dwatt')).toBe('normal')
    expect(root.getAttribute('data-kpi-lambda')).toBe('normal')
  })
})
