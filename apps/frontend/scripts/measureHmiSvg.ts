// 실측 스크립트: schematic.source.svg를 svgson으로 파싱해
// id 목록 / 그룹 구조 / bbox / fill / stroke / dasharray / kpiCard 후보 / combustor 후보를 산출.
// 가정 없이 "현재 SVG에 무엇이 있는지"만 데이터로 출력한다.
//
// 실행: npx tsx apps/frontend/scripts/measureHmiSvg.ts
// 산출: apps/frontend/src/features/dashboard/HmiSchematic/schematic-measurements.json

import { promises as fs } from 'node:fs'
import path from 'node:path'
import { parse, type INode } from 'svgson'

const ROOT = path.resolve(import.meta.dirname, '..')
const SRC = path.join(ROOT, 'src/features/dashboard/HmiSchematic/schematic.source.svg')
const OUT = path.join(ROOT, 'src/features/dashboard/HmiSchematic/schematic-measurements.json')

interface BBox {
  x: number
  y: number
  width: number
  height: number
}

interface NodeInfo {
  id: string | null
  tag: string
  fill: string | null
  stroke: string | null
  strokeDasharray: string | null
  bbox: BBox | null
  parentId: string | null
  parentChain: string[] // 가장 가까운 id 가진 조상 → 루트 방향
  childCount: number
  // 텍스트성 path 식별용
  pathLength: number | null // d 속성 길이 (대략적 글리프 판정)
}

const nodes: NodeInfo[] = []

function parseNum(s: string | undefined): number | null {
  if (s == null) return null
  const n = Number(s)
  return Number.isFinite(n) ? n : null
}

// path d 속성에서 절대좌표 M/L/C/Q/H/V/Z 등을 모두 훑어 bbox 산출
// (상대좌표는 누적해야 정확하지만, 디자이너 SVG는 대부분 절대좌표라 단순 파서로 충분)
function bboxFromPathD(d: string): BBox | null {
  // 명령 + 공백/콤마 + 숫자(부호/소수 허용) 토큰화
  const tokens = d.match(/[a-zA-Z]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi)
  if (!tokens) return null
  const xs: number[] = []
  const ys: number[] = []
  let cmd: string | null = null
  let isRelative = false
  let cx = 0
  let cy = 0
  let i = 0
  while (i < tokens.length) {
    const t = tokens[i]
    if (/^[a-zA-Z]$/.test(t)) {
      cmd = t.toUpperCase()
      isRelative = t !== cmd
      i += 1
      continue
    }
    if (cmd == null) {
      i += 1
      continue
    }
    // 명령별 좌표 소비량
    const consume: { type: 'xy' | 'x' | 'y' | 'arc' | 'cubic' | 'quad'; n: number } = (() => {
      switch (cmd) {
        case 'M':
        case 'L':
        case 'T':
          return { type: 'xy', n: 2 }
        case 'H':
          return { type: 'x', n: 1 }
        case 'V':
          return { type: 'y', n: 1 }
        case 'C':
          return { type: 'cubic', n: 6 }
        case 'S':
        case 'Q':
          return { type: 'quad', n: 4 }
        case 'A':
          return { type: 'arc', n: 7 }
        case 'Z':
          return { type: 'xy', n: 0 }
        default:
          return { type: 'xy', n: 0 }
      }
    })()
    if (consume.n === 0) {
      i += 1
      continue
    }
    const args: number[] = []
    for (let k = 0; k < consume.n; k += 1) {
      const v = parseNum(tokens[i + k])
      if (v == null) {
        // 토큰 부족 시 안전 종료
        return xs.length && ys.length ? bboxOf(xs, ys) : null
      }
      args.push(v)
    }
    i += consume.n
    // 끝점/제어점 좌표 추출
    let endX = cx
    let endY = cy
    switch (consume.type) {
      case 'xy': {
        const [x, y] = args
        endX = isRelative ? cx + x : x
        endY = isRelative ? cy + y : y
        xs.push(endX)
        ys.push(endY)
        break
      }
      case 'x': {
        const [x] = args
        endX = isRelative ? cx + x : x
        xs.push(endX)
        ys.push(cy)
        break
      }
      case 'y': {
        const [y] = args
        endY = isRelative ? cy + y : y
        xs.push(cx)
        ys.push(endY)
        break
      }
      case 'cubic': {
        const [x1, y1, x2, y2, x, y] = args
        const ax = isRelative ? cx : 0
        const ay = isRelative ? cy : 0
        xs.push(ax + x1, ax + x2, ax + x)
        ys.push(ay + y1, ay + y2, ay + y)
        endX = ax + x
        endY = ay + y
        break
      }
      case 'quad': {
        const [x1, y1, x, y] = args
        const ax = isRelative ? cx : 0
        const ay = isRelative ? cy : 0
        xs.push(ax + x1, ax + x)
        ys.push(ay + y1, ay + y)
        endX = ax + x
        endY = ay + y
        break
      }
      case 'arc': {
        const [, , , , , x, y] = args
        endX = isRelative ? cx + x : x
        endY = isRelative ? cy + y : y
        xs.push(endX)
        ys.push(endY)
        break
      }
    }
    cx = endX
    cy = endY
    // M 다음의 좌표 쌍은 implicit L
    if (cmd === 'M') cmd = 'L'
    if (cmd === 'm') cmd = 'l'
  }
  if (!xs.length || !ys.length) return null
  return bboxOf(xs, ys)
}

function bboxOf(xs: number[], ys: number[]): BBox {
  const x = Math.min(...xs)
  const y = Math.min(...ys)
  return {
    x: round(x),
    y: round(y),
    width: round(Math.max(...xs) - x),
    height: round(Math.max(...ys) - y),
  }
}

function round(n: number): number {
  return Math.round(n * 100) / 100
}

function bboxFromAttrs(tag: string, a: Record<string, string>): BBox | null {
  switch (tag) {
    case 'rect': {
      const x = parseNum(a.x) ?? 0
      const y = parseNum(a.y) ?? 0
      const w = parseNum(a.width)
      const h = parseNum(a.height)
      if (w == null || h == null) return null
      return { x, y, width: w, height: h }
    }
    case 'circle': {
      const cx = parseNum(a.cx) ?? 0
      const cy = parseNum(a.cy) ?? 0
      const r = parseNum(a.r)
      if (r == null) return null
      return { x: cx - r, y: cy - r, width: r * 2, height: r * 2 }
    }
    case 'ellipse': {
      const cx = parseNum(a.cx) ?? 0
      const cy = parseNum(a.cy) ?? 0
      const rx = parseNum(a.rx)
      const ry = parseNum(a.ry)
      if (rx == null || ry == null) return null
      return { x: cx - rx, y: cy - ry, width: rx * 2, height: ry * 2 }
    }
    case 'line': {
      const x1 = parseNum(a.x1) ?? 0
      const y1 = parseNum(a.y1) ?? 0
      const x2 = parseNum(a.x2) ?? 0
      const y2 = parseNum(a.y2) ?? 0
      const x = Math.min(x1, x2)
      const y = Math.min(y1, y2)
      return { x, y, width: Math.abs(x2 - x1), height: Math.abs(y2 - y1) }
    }
    case 'polygon':
    case 'polyline': {
      const points = a.points
      if (!points) return null
      const nums = points.match(/-?\d+(?:\.\d+)?/g)
      if (!nums || nums.length < 2) return null
      const xs: number[] = []
      const ys: number[] = []
      for (let i = 0; i + 1 < nums.length; i += 2) {
        xs.push(Number(nums[i]))
        ys.push(Number(nums[i + 1]))
      }
      return bboxOf(xs, ys)
    }
    case 'path': {
      const d = a.d
      if (!d) return null
      return bboxFromPathD(d)
    }
    default:
      return null
  }
}

// 자식 bbox 합집합으로 그룹 bbox 산출
function unionBBox(boxes: BBox[]): BBox | null {
  if (!boxes.length) return null
  const xs = boxes.flatMap((b) => [b.x, b.x + b.width])
  const ys = boxes.flatMap((b) => [b.y, b.y + b.height])
  return bboxOf(xs, ys)
}

function walk(
  node: INode,
  parentId: string | null,
  parentChain: string[],
): BBox[] {
  if (node.type !== 'element') return []
  const a = node.attributes ?? {}
  const id = a.id ?? null
  const tag = node.name
  const childBoxes: BBox[] = []
  // 자식 먼저 수집
  const nextChain = id ? [id, ...parentChain] : parentChain
  for (const child of node.children ?? []) {
    const boxes = walk(child as INode, id ?? parentId, nextChain)
    childBoxes.push(...boxes)
  }
  // 본인 bbox: leaf면 attrs 기반, group이면 자식 union
  let bbox: BBox | null
  if (tag === 'g' || tag === 'svg' || tag === 'defs' || tag === 'mask' || tag === 'clipPath') {
    bbox = unionBBox(childBoxes)
  } else {
    bbox = bboxFromAttrs(tag, a)
  }
  // svg/defs/mask/clipPath/desc/title 은 노드 목록에서 제외
  const skipTags = new Set(['svg', 'defs', 'desc', 'title', 'style', 'metadata'])
  if (!skipTags.has(tag)) {
    nodes.push({
      id,
      tag,
      fill: a.fill ?? null,
      stroke: a.stroke ?? null,
      strokeDasharray: a['stroke-dasharray'] ?? null,
      bbox,
      parentId,
      parentChain,
      childCount: (node.children ?? []).filter((c) => c.type === 'element').length,
      pathLength: tag === 'path' && a.d ? a.d.length : null,
    })
  }
  // 부모로 전달할 bbox: 본인 bbox가 있으면 본인, 없으면 자식 union
  return bbox ? [bbox] : childBoxes
}

// =========================================================================
// kpiCard 후보 식별 휴리스틱
// =========================================================================
// 카드는 보통 둥근 사각형(rect 또는 path) + 내부 라벨/값 글리프(작은 path들)로 구성.
// 1) bbox.width 60~250 / height 30~120 / fill #1E1E1E 계열 또는 stroke 있는 작은 박스
// 2) 그 박스 내부에 여러 path 존재
function findKpiCardCandidates(): Array<{
  containerId: string | null
  bbox: BBox
  innerPathCount: number
  innerPathIds: Array<string | null>
  fill: string | null
  stroke: string | null
}> {
  const candidates = nodes.filter((n) => {
    if (!n.bbox) return false
    const { width, height } = n.bbox
    if (width < 60 || width > 260) return false
    if (height < 30 || height > 130) return false
    if (n.tag !== 'rect' && n.tag !== 'path' && n.tag !== 'g') return false
    return true
  })
  const result: Array<{
    containerId: string | null
    bbox: BBox
    innerPathCount: number
    innerPathIds: Array<string | null>
    fill: string | null
    stroke: string | null
  }> = []
  for (const c of candidates) {
    if (!c.bbox) continue
    const inside = nodes.filter(
      (n) =>
        n !== c &&
        n.tag === 'path' &&
        n.bbox &&
        n.bbox.x >= c.bbox!.x - 1 &&
        n.bbox.y >= c.bbox!.y - 1 &&
        n.bbox.x + n.bbox.width <= c.bbox!.x + c.bbox!.width + 1 &&
        n.bbox.y + n.bbox.height <= c.bbox!.y + c.bbox!.height + 1,
    )
    if (inside.length >= 5) {
      result.push({
        containerId: c.id,
        bbox: c.bbox,
        innerPathCount: inside.length,
        innerPathIds: inside.slice(0, 30).map((n) => n.id),
        fill: c.fill,
        stroke: c.stroke,
      })
    }
  }
  // 같은 영역 중복 제거 (가장 작은 컨테이너 우선)
  result.sort((a, b) => a.bbox.width * a.bbox.height - b.bbox.width * b.bbox.height)
  const seen: Array<{ x: number; y: number }> = []
  return result.filter((r) => {
    const dup = seen.some((s) => Math.abs(s.x - r.bbox.x) < 5 && Math.abs(s.y - r.bbox.y) < 5)
    if (dup) return false
    seen.push({ x: r.bbox.x, y: r.bbox.y })
    return true
  })
}

// =========================================================================
// flow 후보: id에 'flow' 포함되는 그룹, 또는 stroke-dasharray 있는 path
// =========================================================================
function findFlowGroups() {
  const flowGroups = nodes.filter(
    (n) => n.tag === 'g' && n.id != null && /flow/i.test(n.id),
  )
  const dashedPaths = nodes.filter((n) => n.tag === 'path' && n.strokeDasharray != null)
  return { flowGroups, dashedPaths }
}

// =========================================================================
// combustor 후보: id에 combust/flame/burner 포함, 또는 orange-ish fill
// =========================================================================
function findCombustorCandidates() {
  const byName = nodes.filter(
    (n) => n.id != null && /(combust|flame|burner|GT|gas[_-]?turbine)/i.test(n.id),
  )
  const byFill = nodes.filter((n) => {
    if (!n.fill) return false
    const f = n.fill.toLowerCase()
    return /^#(ff[89a-f]|f[89a-f][0-9a-f])/i.test(f) || f === '#ff991f' || f === '#ff8000'
  })
  return { byName: byName.map(summary), byFill: byFill.map(summary) }
}

// =========================================================================
// 라벨 후보: bbox.width/height 모두 작고 (글리프 크기), parentChain에 카드 컨테이너 포함
// =========================================================================
function findLabelGlyphs(cardBboxes: BBox[]) {
  return nodes
    .filter((n) => {
      if (n.tag !== 'path' || !n.bbox) return false
      const { width, height } = n.bbox
      if (width > 30 || height > 30) return false
      if (width < 1 || height < 1) return false
      // 어떤 카드 안에 있는지
      return cardBboxes.some(
        (c) =>
          n.bbox!.x >= c.x - 1 &&
          n.bbox!.y >= c.y - 1 &&
          n.bbox!.x + n.bbox!.width <= c.x + c.width + 1 &&
          n.bbox!.y + n.bbox!.height <= c.y + c.height + 1,
      )
    })
    .map(summary)
}

function summary(n: NodeInfo) {
  return {
    id: n.id,
    tag: n.tag,
    fill: n.fill,
    stroke: n.stroke,
    bbox: n.bbox,
    parentId: n.parentId,
    parentChain: n.parentChain.slice(0, 5),
  }
}

async function main() {
  const svg = await fs.readFile(SRC, 'utf-8')
  const tree = await parse(svg)
  walk(tree, null, [])

  const ids = nodes.filter((n) => n.id).map((n) => n.id!) as string[]
  const groups = nodes
    .filter((n) => n.tag === 'g' && n.id != null)
    .map((n) => ({
      id: n.id,
      bbox: n.bbox,
      childCount: n.childCount,
      parentId: n.parentId,
    }))

  const kpi = findKpiCardCandidates()
  const flows = findFlowGroups()
  const combustor = findCombustorCandidates()
  const labelGlyphs = findLabelGlyphs(kpi.map((k) => k.bbox))

  // 경고: 가정 어긋남 항목
  const warnings: string[] = []
  if (combustor.byName.length === 0 && combustor.byFill.length === 0) {
    warnings.push('combustor/flame: id-name 매칭도 0건, orange-fill 매칭도 0건 — flame 애니메이션 대상 없음')
  }
  if (flows.flowGroups.length === 0) {
    warnings.push('flow: id에 "flow" 포함된 그룹 0건 — flow 애니메이션 그룹 식별 실패')
  }
  if (flows.dashedPaths.length === 0) {
    warnings.push('flow: stroke-dasharray 가진 path 0건 — dash flow 애니메이션 후보 없음')
  }

  const result = {
    viewBox: { width: 1316, height: 540 },
    counts: {
      total: nodes.length,
      withId: ids.length,
      groups: groups.length,
      kpiCardCandidates: kpi.length,
      flowGroups: flows.flowGroups.length,
      dashedPaths: flows.dashedPaths.length,
      combustorByName: combustor.byName.length,
      combustorByFill: combustor.byFill.length,
      labelGlyphs: labelGlyphs.length,
    },
    ids,
    groups,
    kpiCards: kpi,
    flows: {
      groups: flows.flowGroups.map((n) => ({
        id: n.id,
        bbox: n.bbox,
        childCount: n.childCount,
      })),
      dashedPaths: flows.dashedPaths.slice(0, 30).map(summary),
    },
    combustorCandidates: combustor,
    labelGlyphs: labelGlyphs.slice(0, 60),
    warnings,
  }

  await fs.writeFile(OUT, JSON.stringify(result, null, 2), 'utf-8')
  console.log(`[measureHmiSvg] wrote ${OUT}`)
  console.log(`  total nodes: ${result.counts.total}`)
  console.log(`  withId: ${result.counts.withId}, groups: ${result.counts.groups}`)
  console.log(`  kpiCardCandidates: ${result.counts.kpiCardCandidates}`)
  console.log(`  flowGroups: ${result.counts.flowGroups}, dashedPaths: ${result.counts.dashedPaths}`)
  console.log(`  combustor byName=${result.counts.combustorByName}, byFill=${result.counts.combustorByFill}`)
  console.log(`  labelGlyphs (in cards): ${result.counts.labelGlyphs}`)
  if (warnings.length) {
    console.log('  WARNINGS:')
    for (const w of warnings) console.log(`    - ${w}`)
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
