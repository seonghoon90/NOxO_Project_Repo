import { describe, it, expect } from 'vitest'
import type { INode } from 'svgson'
import { transformAst, collectIds } from '../buildHmiSvg/transformAst'

function el(name: string, attrs: Record<string, string>, children: INode[] = []): INode {
  return { name, type: 'element', value: '', attributes: attrs, children }
}

describe('transformAst', () => {
  it('kpi-card kind는 data-role 부여 + id 보존', () => {
    const ast = el('svg', {}, [
      el('g', { id: 'metric_NOx' }, [el('rect', { id: 'box_NOx' })]),
    ])
    const map = {
      'card-nox': { id: 'metric_NOx', kind: 'kpi-card' as const },
      'card-box-nox': { id: 'box_NOx', kind: 'kpi-box' as const },
    }
    const result = transformAst(ast, map)
    const card = result.ast.children[0]
    expect(card.attributes['data-role']).toBe('card-nox')
    expect(card.attributes.id).toBe('metric_NOx')
    const box = card.children[0]
    expect(box.attributes['data-role']).toBe('card-box-nox')
  })

  it('kpi-value-remove kind는 element 제거 + KPI_ANCHORS 산출', () => {
    // 값 path가 (10, 20)에서 (40, 60) 영역
    const ast = el('svg', {}, [
      el('g', { id: 'metric_NOx' }, [
        el('path', { id: '26.5', d: 'M 10 20 L 40 20 L 40 60 L 10 60 Z' }),
      ]),
    ])
    const map = {
      'card-nox': { id: 'metric_NOx', kind: 'kpi-card' as const },
      'kpi-value-nox': { id: '26.5', kind: 'kpi-value-remove' as const },
    }
    const result = transformAst(ast, map)
    const card = result.ast.children[0]
    // path 자식이 제거됨
    expect(card.children.length).toBe(0)
    // anchor 산출 — y는 bbox.y + bbox.height
    expect(result.kpiAnchors.nox).toBeDefined()
    expect(result.kpiAnchors.nox!.x).toBe(10)
    expect(result.kpiAnchors.nox!.y).toBe(60)
    expect(result.kpiAnchors.nox!.textAnchor).toBe('start')
  })

  it('flow-group/cascade-step/flame-anchor도 data-role 부여', () => {
    const ast = el('svg', {}, [
      el('g', { id: 'flow_fuel_pink' }),
      el('g', { id: 'BOX_NQKR3_MONITOR' }),
      el('path', { id: 'COMBUSTOR' }),
    ])
    const map = {
      'flow-fuel':   { id: 'flow_fuel_pink',     kind: 'flow-group' as const },
      'cascade-1':   { id: 'BOX_NQKR3_MONITOR',  kind: 'cascade-step' as const },
      'combustor':   { id: 'COMBUSTOR',          kind: 'flame-anchor' as const },
    }
    const result = transformAst(ast, map)
    expect(result.ast.children[0].attributes['data-role']).toBe('flow-fuel')
    expect(result.ast.children[1].attributes['data-role']).toBe('cascade-1')
    expect(result.ast.children[2].attributes['data-role']).toBe('combustor')
  })

  it('collectIds는 변환 전 모든 element id를 수집 (kpi-value-remove 대상 포함)', () => {
    const ast = el('svg', {}, [
      el('path', { id: 'a' }),
      el('path', { id: 'b' }),
      el('g', { id: 'c' }, [el('path', { id: 'd' })]),
    ])
    const ids = collectIds(ast)
    expect(ids.has('a')).toBe(true)
    expect(ids.has('b')).toBe(true)
    expect(ids.has('c')).toBe(true)
    expect(ids.has('d')).toBe(true)
  })

  it('lambda role은 kpiAnchors.lambda로 산출 (역매핑 표준화)', () => {
    const ast = el('svg', {}, [
      el('path', { id: '1.10', d: 'M 0 0 L 10 0 L 10 5 L 0 5 Z' }),
    ])
    const map = { 'kpi-value-lambda': { id: '1.10', kind: 'kpi-value-remove' as const } }
    const result = transformAst(ast, map)
    expect(result.kpiAnchors.lambda).toBeDefined()
  })
})
