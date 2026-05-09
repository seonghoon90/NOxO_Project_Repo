// 빌드 entry. CLI로 실행하면 schematic.source.svg를 읽어 산출물 2개를 쓴다.
//   tsx scripts/buildHmiSvg.ts
// 함수 buildHmiSvg()는 라이브러리로도 호출 가능 (테스트용).

import { promises as fs } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse, stringify } from 'svgson'
import { optimize } from 'svgo'
import { ROLE_MAP } from './buildHmiSvg/ROLE_MAP'
import { validateRoles } from './buildHmiSvg/validateRoles'
import { transformAst, collectIds, type KpiAnchor, type KpiAnchorKey } from './buildHmiSvg/transformAst'
import { emitRolesTs } from './buildHmiSvg/emitRolesTs'
import { BuildValidationError } from './buildHmiSvg/BuildValidationError'
import type { RoleEntry } from './buildHmiSvg/roleEntry'

export interface BuildArgs {
  sourcePath: string
  roleMap?: Readonly<Record<string, Readonly<RoleEntry>>>
}

export interface BuildResult {
  svg: string
  rolesTs: string
  kpiAnchors: Partial<Record<KpiAnchorKey, KpiAnchor>>
}

export async function buildHmiSvg(args: BuildArgs): Promise<BuildResult> {
  const map = args.roleMap ?? ROLE_MAP
  const raw = await fs.readFile(args.sourcePath, 'utf-8')
  const ast = await parse(raw)

  // [1] 변환 전 원본 id 수집
  const originalIds = collectIds(ast)

  // [2] 검증 (transformAst가 path 파싱 등으로 throw하기 전에 명확한 에러 우선)
  validateRoles(originalIds, map)

  // [3] AST 변형 + bbox 추출
  const transformed = transformAst(ast, map)

  // [4] svgo 최적화
  const intermediate = stringify(transformed.ast)
  const optimized = optimize(intermediate, {
    multipass: false,
    plugins: [
      {
        name: 'preset-default',
        params: {
          overrides: {
            cleanupIds: false,
            removeUnknownsAndDefaults: { keepDataAttrs: true },
          },
        },
      },
      // preset-default 에 속하지 않으므로 별도 비활성화
      { name: 'removeViewBox', active: false },
    ],
  })

  // [5] viewBox는 source SVG 크기로 고정 (1316×540)
  const rolesTs = emitRolesTs({
    roleMap: map,
    kpiAnchors: transformed.kpiAnchors,
    viewBox: { width: 1316, height: 540 },
  })

  return { svg: optimized.data, rolesTs, kpiAnchors: transformed.kpiAnchors }
}

// CLI entry — import.meta.url 비교로 직접 실행 시에만 동작
const isDirectInvoke = (() => {
  try {
    return process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])
  } catch {
    return false
  }
})()

if (isDirectInvoke) {
  const ROOT = path.resolve(fileURLToPath(import.meta.url), '..')
  const SOURCE = path.resolve(ROOT, '../src/features/dashboard/HmiSchematic/schematic.source.svg')
  const OUT_SVG = path.resolve(ROOT, '../src/features/dashboard/HmiSchematic/schematic.svg')
  const OUT_TS = path.resolve(ROOT, '../src/features/dashboard/HmiSchematic/schematic-roles.ts')

  buildHmiSvg({ sourcePath: SOURCE })
    .then(async (res) => {
      await fs.writeFile(OUT_SVG, res.svg, 'utf-8')
      await fs.writeFile(OUT_TS, res.rolesTs, 'utf-8')
      console.log(`[buildHmiSvg] wrote ${OUT_SVG}`)
      console.log(`[buildHmiSvg] wrote ${OUT_TS}`)
      console.log(`[buildHmiSvg] KPI_ANCHORS:`, res.kpiAnchors)
    })
    .catch((err) => {
      if (err instanceof BuildValidationError) {
        console.error('[buildHmiSvg] role mapping validation FAILED')
        console.error(err.toReport())
        process.exit(1)
      }
      console.error('[buildHmiSvg] unexpected error:', err)
      process.exit(2)
    })
}
