import type { INode } from 'svgson'
import { pathBBox } from './pathBBox'

export interface KpiAnchor {
  x: number
  y: number
  textAnchor: 'start'
}

export type KpiAnchorKey = 'nox' | 'ttxm' | 'dwatt' | 'lambda'

export interface TransformResult {
  ast: INode
  kpiAnchors: Partial<Record<KpiAnchorKey, KpiAnchor>>
}

interface RoleEntry {
  id: string
  kind: string
}

// 'kpi-value-nox' → 'nox'
function roleToAnchorKey(role: string): KpiAnchorKey | null {
  const m = role.match(/^kpi-value-(nox|ttxm|dwatt|lambda)$/)
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

  // root 자신도 remove 대상일 수 있으므로 root children에서 처리
  // visit은 자식 레벨에서 remove 처리 — root-level path 제거는 래퍼로 처리
  const fakeRoot: INode = {
    name: '__root__',
    type: 'element',
    value: '',
    attributes: {},
    children: [rootInput],
  }
  visit(fakeRoot)
  const ast = fakeRoot.children[0] ?? rootInput

  return { ast, kpiAnchors }
}
