import { describe, it, expect } from 'vitest'
import path from 'node:path'
import { buildHmiSvg } from '../buildHmiSvg'
import { BuildValidationError } from '../buildHmiSvg/BuildValidationError'

const FIXTURES = path.resolve(__dirname, 'fixtures')

describe('buildHmiSvg (E2E)', () => {
  it('valid fixture는 svg 문자열 + roles 문자열을 반환', async () => {
    const result = await buildHmiSvg({
      sourcePath: path.join(FIXTURES, 'valid.svg'),
      // 부분 매핑만 사용 (fixture에 모든 ROLE_MAP id가 있지 않으므로)
      roleMap: {
        'card-nox':      { id: 'metric_NOx',     kind: 'kpi-card' },
        'card-box-nox':  { id: 'box_NOx',        kind: 'kpi-box' },
        'kpi-value-nox': { id: '26.5',           kind: 'kpi-value-remove' },
        'flow-fuel':     { id: 'flow_fuel_pink', kind: 'flow-group' },
        'combustor':     { id: 'COMBUSTOR',      kind: 'flame-anchor' },
      },
    })
    expect(result.svg).toContain('data-role="card-nox"')
    expect(result.svg).toContain('data-role="card-box-nox"')
    expect(result.svg).toContain('data-role="flow-fuel"')
    expect(result.svg).toContain('data-role="combustor"')
    // 26.5 path는 제거
    expect(result.svg).not.toContain('id="26.5"')
    // KPI_ANCHORS 산출
    expect(result.kpiAnchors.nox).toBeDefined()
  })

  it('missing-id fixture는 BuildValidationError throw', async () => {
    await expect(
      buildHmiSvg({
        sourcePath: path.join(FIXTURES, 'missing-id.svg'),
        roleMap: {
          'card-nox':     { id: 'metric_NOx', kind: 'kpi-card' }, // missing
          'card-box-nox': { id: 'box_NOx',    kind: 'kpi-box' },
        },
      }),
    ).rejects.toBeInstanceOf(BuildValidationError)
  })

  it('roles.ts 문자열에 ROLES + KPI_ANCHORS + VIEW_BOX 포함', async () => {
    const result = await buildHmiSvg({
      sourcePath: path.join(FIXTURES, 'valid.svg'),
      roleMap: {
        'card-nox':      { id: 'metric_NOx', kind: 'kpi-card' },
        'kpi-value-nox': { id: '26.5',       kind: 'kpi-value-remove' },
      },
    })
    expect(result.rolesTs).toContain('export const ROLES')
    expect(result.rolesTs).toContain('export const KPI_ANCHORS')
    expect(result.rolesTs).toContain('export const VIEW_BOX')
  })
})
