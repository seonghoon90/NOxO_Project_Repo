import { describe, it, expect } from 'vitest'
import { cssVarsFromProps, type SchematicInputs } from './cssVarsFromProps'

// 테스트용 mock VariableConfig
function vc(value: number, min: number, max: number) {
  return {
    key: 'mock', label: '', shortLabel: '', rawName: '', unit: '',
    digits: 1, step: 1, base: value, min, max, value,
  } as never
}

const baseInputs: SchematicInputs = {
  syngasFlow: vc(1500, 800, 2200),    // 정규화 → (1500-800)/(2200-800) = 0.5
  syngasSrv:  vc(50, 0, 100),
  syngasGcv1: vc(50, 0, 100),
  syngasGcv1a:vc(50, 0, 100),
  syngasGcv2: vc(50, 0, 100),
  n2Offset:   vc(250, 0, 500),         // 0.5
  n2Valve1:   vc(50, 0, 100),
  n2Flow:     vc(30, 0, 60),           // 0.5
  igvOpening: vc(65, 30, 100),         // (65-30)/70 = 0.5
  ibhValve:   vc(50, 0, 100),
  nox: 25,        // 0~50 → 0.5
  ttxm: 1040,     // 580~1500 → 0.5
  lambda: 1.15,   // 0.9~1.4 → 0.5
  power: 120,     // 0~240 → 0.5
}

function getVar(vars: Record<string, string | number>, name: string): number {
  const raw = vars[name]
  return typeof raw === 'number' ? raw : parseFloat(String(raw))
}

describe('cssVarsFromProps — 합성가스', () => {
  it('syngasFlow value=min이면 --syn-flow는 0.05 floor', () => {
    const v = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(800, 800, 2200) })
    expect(getVar(v, '--syn-flow')).toBeCloseTo(0.05, 5)
  })
  it('syngasFlow value=max이면 --syn-flow는 1.0', () => {
    const v = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(2200, 800, 2200) })
    expect(getVar(v, '--syn-flow')).toBeCloseTo(1.0, 5)
  })
  it('FSAGR(syngasSrv) 50/100이면 --valve-fsagr는 0.5', () => {
    expect(getVar(cssVarsFromProps(baseInputs), '--valve-fsagr')).toBeCloseTo(0.5, 5)
  })
  it('IGV(igvOpening) min(30)이면 --air-flow는 0.05 floor', () => {
    const v = cssVarsFromProps({ ...baseInputs, igvOpening: vc(30, 30, 100) })
    expect(getVar(v, '--air-flow')).toBeCloseTo(0.05, 5)
  })
})

describe('cssVarsFromProps — flame', () => {
  it('TTXM 580°C이면 hue는 45', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, ttxm: 580 }), '--flame-hue')).toBeCloseTo(45, 1)
  })
  it('TTXM 1500°C이면 hue는 12', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, ttxm: 1500 }), '--flame-hue')).toBeCloseTo(12, 1)
  })
  it('TTXM 580°C이면 scale은 0.85', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, ttxm: 580 }), '--flame-scale')).toBeCloseTo(0.85, 5)
  })
  it('--flame-intensity는 syngasFlow 정규화 값 (0~1)', () => {
    const v0 = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(800, 800, 2200) })
    expect(v0['--flame-intensity']).toBe(0)
    const vMid = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(1500, 800, 2200) })
    expect(vMid['--flame-intensity']).toBe(0.5)
    const vMax = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(2200, 800, 2200) })
    expect(vMax['--flame-intensity']).toBe(1)
  })
})

describe('cssVarsFromProps — smoke (NOx threshold 0.6)', () => {
  it('NOx 비율 0.5(=25ppm)면 --smoke-opacity는 0', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, nox: 25 }), '--smoke-opacity')).toBe(0)
  })
  it('NOx 비율 0.6(=30ppm)에서 가시 시작 (0)', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, nox: 30 }), '--smoke-opacity')).toBeCloseTo(0, 5)
  })
  it('NOx 50ppm이면 --smoke-opacity는 0.85', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, nox: 50 }), '--smoke-opacity')).toBeCloseTo(0.85, 5)
  })
})

describe('cssVarsFromProps — KPI cards', () => {
  it('NOx 50ppm이면 --card-glow-nox는 1.0', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, nox: 50 }), '--card-glow-nox')).toBeCloseTo(1, 5)
  })
  it('lambda 1.15(중간값)이면 --card-glow-lambda는 0.5', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, lambda: 1.15 }), '--card-glow-lambda')).toBeCloseTo(0.5, 5)
  })
  it('power 120MW(중간값)이면 --card-glow-dwatt는 0.5', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, power: 120 }), '--card-glow-dwatt')).toBeCloseTo(0.5, 5)
  })
})

describe('cssVarsFromProps — guards', () => {
  it('NaN nox는 0으로', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, nox: NaN }), '--card-glow-nox')).toBe(0)
  })
  it('undefined ttxm은 fallback (0)', () => {
    expect(getVar(cssVarsFromProps({ ...baseInputs, ttxm: undefined as unknown as number }), '--flame-scale')).toBeCloseTo(0.85, 5)
  })
  it('VariableConfig value가 NaN이면 0으로', () => {
    const v = cssVarsFromProps({ ...baseInputs, syngasFlow: vc(NaN, 800, 2200) })
    expect(getVar(v, '--syn-flow')).toBe(0.05) // floor
  })
})
