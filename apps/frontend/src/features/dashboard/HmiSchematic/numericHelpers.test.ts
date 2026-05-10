import { describe, it, expect } from 'vitest'
import { clamp, lerp, normalize, finiteOr, formatKpi } from './numericHelpers'

describe('clamp', () => {
  it('범위 안의 값은 그대로', () => expect(clamp(5, 0, 10)).toBe(5))
  it('상한 초과는 상한으로', () => expect(clamp(15, 0, 10)).toBe(10))
  it('하한 미만은 하한으로', () => expect(clamp(-3, 0, 10)).toBe(0))
})

describe('normalize', () => {
  it('0~max 범위를 0~1로', () => expect(normalize(25, 0, 50)).toBe(0.5))
  it('min/max 같으면 0', () => expect(normalize(7, 5, 5)).toBe(0))
  it('범위 초과는 클램프됨', () => expect(normalize(60, 0, 50)).toBe(1))
  it('음수 입력은 0으로 클램프', () => expect(normalize(-5, 0, 50)).toBe(0))
})

describe('lerp', () => {
  it('t=0이면 a', () => expect(lerp(10, 20, 0)).toBe(10))
  it('t=1이면 b', () => expect(lerp(10, 20, 1)).toBe(20))
  it('t=0.5는 중간', () => expect(lerp(10, 20, 0.5)).toBe(15))
})

describe('finiteOr', () => {
  it('finite 값은 그대로', () => expect(finiteOr(3.14, 0)).toBe(3.14))
  it('NaN은 fallback', () => expect(finiteOr(NaN, 0)).toBe(0))
  it('Infinity는 fallback', () => expect(finiteOr(Infinity, -1)).toBe(-1))
  it('undefined는 fallback', () => expect(finiteOr(undefined, 7)).toBe(7))
})

describe('formatKpi', () => {
  it('유한 숫자는 toFixed로 포맷', () => {
    expect(formatKpi(26.5, 1)).toBe('26.5')
    expect(formatKpi(580, 1)).toBe('580.0')
    expect(formatKpi(1.1, 2)).toBe('1.10')
  })

  it('NaN/Infinity → "--"', () => {
    expect(formatKpi(NaN, 1)).toBe('--')
    expect(formatKpi(Infinity, 1)).toBe('--')
    expect(formatKpi(-Infinity, 1)).toBe('--')
  })
})
