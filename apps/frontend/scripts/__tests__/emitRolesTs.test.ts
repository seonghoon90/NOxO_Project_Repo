import { describe, it, expect } from 'vitest'
import { emitRolesTs } from '../buildHmiSvg/emitRolesTs'

describe('emitRolesTs', () => {
  it('AUTO-GENERATED 헤더 포함', () => {
    const out = emitRolesTs({
      roleMap: {
        'card-nox': { id: 'metric_NOx', kind: 'kpi-card' },
      },
      kpiAnchors: {
        nox: { x: 10, y: 20, textAnchor: 'start' },
      },
      viewBox: { width: 1316, height: 540 },
    })
    expect(out).toContain('// AUTO-GENERATED. DO NOT EDIT.')
    expect(out).toContain('/* eslint-disable */')
  })

  it('ROLES export — kpi-value-remove kind 제외, 16 entries만 emit (소스 ROLE_MAP 기준)', () => {
    const out = emitRolesTs({
      roleMap: {
        'card-nox': { id: 'metric_NOx', kind: 'kpi-card' },
        'kpi-value-nox': { id: '26.5', kind: 'kpi-value-remove' },
      },
      kpiAnchors: { nox: { x: 10, y: 20, textAnchor: 'start' } },
      viewBox: { width: 1316, height: 540 },
    })
    expect(out).toContain("cardNox: 'card-nox'")
    expect(out).not.toContain("'kpi-value-nox'")
  })

  it('KPI_ANCHORS export', () => {
    const out = emitRolesTs({
      roleMap: {},
      kpiAnchors: {
        nox: { x: 1124.88, y: 130.4, textAnchor: 'start' },
      },
      viewBox: { width: 1316, height: 540 },
    })
    expect(out).toContain('export const KPI_ANCHORS')
    expect(out).toMatch(/nox:\s*{\s*x:\s*1124\.88/)
    expect(out).toContain("textAnchor: 'start'")
  })

  it('VIEW_BOX export', () => {
    const out = emitRolesTs({
      roleMap: {},
      kpiAnchors: {},
      viewBox: { width: 1316, height: 540 },
    })
    expect(out).toContain('export const VIEW_BOX = { width: 1316, height: 540 }')
  })
})
