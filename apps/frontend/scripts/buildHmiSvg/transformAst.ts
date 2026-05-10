import type { INode } from 'svgson'
import { pathBBox } from './pathBBox'
import type { RoleEntry } from './roleEntry'

export interface KpiAnchor {
  x: number
  y: number
  textAnchor: 'start'
}

export type KpiAnchorKey =
  | 'nox' | 'ttxm' | 'dwatt' | 'lambda'
  | 'syngas' | 'fsagr' | 'fsag11' | 'fsag11a' | 'fsag12'
  | 'nicvs1' | 'nqj' | 'csbhx' | 'csgv' | 'nqkr3'
  | 'legend-fuel' | 'legend-n2' | 'legend-air'

export interface TransformResult {
  ast: INode
  kpiAnchors: Partial<Record<KpiAnchorKey, KpiAnchor>>
}

// 'kpi-value-nox' → 'nox'
function roleToAnchorKey(role: string): KpiAnchorKey | null {
  const m = role.match(/^kpi-value-(nox|ttxm|dwatt|lambda|syngas|fsagr|fsag11|fsag11a|fsag12|nicvs1|nqj|csbhx|csgv|nqkr3|legend-fuel|legend-n2|legend-air)$/)
  return m ? (m[1] as KpiAnchorKey) : null
}

// AST의 모든 element id를 수집. transformAst와는 별도로 호출돼
// validateRoles가 변환 전 원본 id 집합으로 검증할 수 있게 함.
export function collectIds(node: INode): Set<string> {
  const into = new Set<string>()
  walk(node)
  return into

  function walk(n: INode): void {
    if (n.type !== 'element') return
    const id = n.attributes?.id
    if (id) into.add(id)
    for (const child of n.children ?? []) {
      walk(child)
    }
  }
}

/**
 * AST를 in-place로 변형해 data-role 부여 + kpi-value-remove element 제거 + KPI_ANCHORS 산출.
 * 주의: rootInput은 호출 후 변형된 상태로 남는다 (deep-clone 안 함).
 */
export function transformAst(
  rootInput: INode,
  roleMap: Readonly<Record<string, Readonly<RoleEntry>>>,
): TransformResult {
  // id → role 인덱스 + remove 대상 인덱스
  const idToRole = new Map<string, string>()
  const removeIds = new Map<string, string>() // id → role
  for (const [role, entry] of Object.entries(roleMap)) {
    if (entry.kind === 'kpi-value-remove') {
      removeIds.set(entry.id, role)
    } else {
      idToRole.set(entry.id, role)
    }
  }

  const kpiAnchors: Partial<Record<KpiAnchorKey, KpiAnchor>> = {}

  // AST 변형 (in-place: data-role 부여 + remove 자식 필터링)
  function visit(node: INode): INode {
    if (node.type !== 'element') return node
    const id = node.attributes?.id
    if (id) {
      const role = idToRole.get(id)
      if (role) {
        node.attributes = { ...node.attributes, 'data-role': role }
      }
    }
    // 자식 중 remove 대상이 있으면 anchor 추출 후 제거
    if (node.children && node.children.length > 0) {
      const survivors: INode[] = []
      for (const child of node.children) {
        if (child.type === 'element' && child.attributes?.id) {
          const removeRole = removeIds.get(child.attributes.id)
          if (removeRole) {
            const anchorKey = roleToAnchorKey(removeRole)
            const d = child.attributes.d
            if (anchorKey && d) {
              const bbox = pathBBox(d)
              kpiAnchors[anchorKey] = {
                x: bbox.x,
                y: bbox.y + bbox.height,
                textAnchor: 'start',
              }
            }
            continue // 제거
          }
        }
        survivors.push(visit(child))
      }
      node.children = survivors
    }
    return node
  }

  // rootInput 자체가 kpi-value-remove 대상일 수도 있어 visit가 children 루프에서 처리할 수 있게 fakeRoot로 한 단계 감쌈.
  // fakeRoot의 name='__root__'은 디버그용이고 id가 없어 removeIds/idToRole 어느 쪽에도 매칭되지 않음.
  const fakeRoot: INode = {
    name: '__root__',
    type: 'element',
    value: '',
    attributes: {},
    children: [rootInput],
  }
  visit(fakeRoot)

  // svg 최상위 첫 자식이 #1E1E1E 전체 배경(rect 또는 svgo 변환 후 path)이면 제거
  if (rootInput.children && rootInput.children.length > 0) {
    const first = rootInput.children[0]
    if (
      first.type === 'element' &&
      (first.name === 'rect' || first.name === 'path') &&
      first.attributes?.fill?.toLowerCase() === '#1e1e1e'
    ) {
      rootInput.children.shift()
    }
  }
  // rootInput이 remove 대상이면 children이 비어 폴백으로 원본을 반환 — 실 빌드에서는 발생 X
  const ast = fakeRoot.children[0] ?? rootInput

  return { ast, kpiAnchors }
}
