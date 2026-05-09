import { describe, it, expect } from 'vitest'
import { validateRoles } from '../buildHmiSvg/validateRoles'
import { BuildValidationError } from '../buildHmiSvg/BuildValidationError'

describe('validateRoles', () => {
  it('모든 id가 originalIds에 있으면 throw 없음', () => {
    const ids = new Set(['a', 'b', 'c'])
    const map = {
      ra: { id: 'a', kind: 'kpi-card' as const },
      rb: { id: 'b', kind: 'kpi-card' as const },
    }
    expect(() => validateRoles(ids, map)).not.toThrow()
  })

  it('매핑 id가 SVG에 없으면 BuildValidationError', () => {
    const ids = new Set(['a'])
    const map = {
      ra: { id: 'a', kind: 'kpi-card' as const },
      rb: { id: 'missing-id', kind: 'kpi-card' as const },
    }
    try {
      validateRoles(ids, map)
      expect.fail('should throw')
    } catch (e) {
      expect(e).toBeInstanceOf(BuildValidationError)
      const err = e as BuildValidationError
      expect(err.detail.missing).toEqual([{ role: 'rb', id: 'missing-id' }])
      expect(err.detail.conflicts).toEqual([])
    }
  })

  it('같은 id를 두 role이 가리키면 conflict', () => {
    const ids = new Set(['a'])
    const map = {
      ra: { id: 'a', kind: 'kpi-card' as const },
      rb: { id: 'a', kind: 'kpi-box' as const },
    }
    try {
      validateRoles(ids, map)
      expect.fail('should throw')
    } catch (e) {
      const err = e as BuildValidationError
      expect(err.detail.conflicts).toEqual([{ id: 'a', roles: ['ra', 'rb'] }])
    }
  })

  it('extra id (SVG에 있지만 매핑 안 된 id)는 throw 안 함', () => {
    const ids = new Set(['a', 'extra1', 'extra2'])
    const map = { ra: { id: 'a', kind: 'kpi-card' as const } }
    expect(() => validateRoles(ids, map)).not.toThrow()
  })

  it('toReport()는 missing/conflict 모두 포함', () => {
    const ids = new Set<string>([])
    const map = {
      ra: { id: 'a', kind: 'kpi-card' as const },
      rb: { id: 'b', kind: 'kpi-card' as const },
    }
    try {
      validateRoles(ids, map)
    } catch (e) {
      const err = e as BuildValidationError
      const report = err.toReport()
      expect(report).toContain('role="ra"')
      expect(report).toContain('id="a"')
      expect(report).toContain('role="rb"')
    }
  })
})
