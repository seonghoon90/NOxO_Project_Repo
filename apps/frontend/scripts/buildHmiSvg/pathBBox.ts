export interface BBox {
  x: number
  y: number
  width: number
  height: number
}

// erasableSyntaxOnly: true에서는 parameter property(`public readonly x`) 사용 불가.
// 명시 필드 + constructor 대입 형태로 작성.
export class UnsupportedPathCommandError extends Error {
  readonly command: string

  constructor(command: string) {
    super(`Unsupported SVG path command: ${command}. Supported: M, L, H, V, C, Z (case-insensitive)`)
    this.name = 'UnsupportedPathCommandError'
    this.command = command
  }
}

const SUPPORTED = new Set(['M', 'L', 'H', 'V', 'C', 'Z'])

interface CommandSpec {
  argCount: number
}

const SPEC: Record<string, CommandSpec> = {
  M: { argCount: 2 },
  L: { argCount: 2 },
  H: { argCount: 1 },
  V: { argCount: 1 },
  C: { argCount: 6 },
  Z: { argCount: 0 },
}

function tokenize(d: string): string[] {
  // 명령 글자(a-zA-Z) 또는 부호/지수 포함 숫자
  const matches = d.match(/[a-zA-Z]|-?\d+(?:\.\d+)?(?:e[-+]?\d+)?/gi)
  return matches ?? []
}

export function pathBBox(d: string): BBox {
  const tokens = tokenize(d)
  if (tokens.length === 0) throw new Error('Empty path d')

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
      const upper = t.toUpperCase()
      if (!SUPPORTED.has(upper)) throw new UnsupportedPathCommandError(t)
      cmd = upper
      isRelative = t !== upper
      i += 1
      // M 다음 implicit L 처리를 위해 별도 변수 불필요 — 동일 cmd 유지
      continue
    }
    if (cmd == null) throw new Error(`Path d starts with non-command: ${t}`)

    if (cmd === 'Z') {
      // Z는 인자 없음. 현재 좌표 그대로
      continue
    }

    const spec = SPEC[cmd]
    const args: number[] = []
    for (let k = 0; k < spec.argCount; k += 1) {
      const v = Number(tokens[i + k])
      if (!Number.isFinite(v)) throw new Error(`Invalid number in path d: ${tokens[i + k]}`)
      args.push(v)
    }
    i += spec.argCount

    let endX = cx
    let endY = cy
    switch (cmd) {
      case 'M':
      case 'L': {
        const [x, y] = args
        endX = isRelative ? cx + x : x
        endY = isRelative ? cy + y : y
        xs.push(endX)
        ys.push(endY)
        // M 다음의 좌표 쌍은 implicit L
        if (cmd === 'M') cmd = 'L'
        break
      }
      case 'H': {
        const [x] = args
        endX = isRelative ? cx + x : x
        xs.push(endX)
        ys.push(cy)
        break
      }
      case 'V': {
        const [y] = args
        endY = isRelative ? cy + y : y
        xs.push(cx)
        ys.push(endY)
        break
      }
      case 'C': {
        const [x1, y1, x2, y2, x, y] = args
        const ax = isRelative ? cx : 0
        const ay = isRelative ? cy : 0
        xs.push(ax + x1, ax + x2, ax + x)
        ys.push(ay + y1, ay + y2, ay + y)
        endX = ax + x
        endY = ay + y
        break
      }
    }
    cx = endX
    cy = endY
  }

  if (xs.length === 0 || ys.length === 0) throw new Error('Path d has no point data')

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  return {
    x: minX,
    y: minY,
    width: maxX - minX,
    height: maxY - minY,
  }
}
