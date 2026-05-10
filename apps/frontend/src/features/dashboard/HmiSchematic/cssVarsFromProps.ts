import type { VariableConfig } from '../mockConsole'
import { clamp, finiteOr, lerp, normalize } from './numericHelpers'

// VariableConfig를 받아 그 자체의 min/max로 0~1 정규화 비율을 산출
export type SchematicInputs = {
  syngasFlow: VariableConfig
  syngasSrv:  VariableConfig
  syngasGcv1: VariableConfig
  syngasGcv1a:VariableConfig
  syngasGcv2: VariableConfig
  n2Offset:   VariableConfig
  n2Valve1:   VariableConfig
  n2Flow:     VariableConfig
  igvOpening: VariableConfig
  ibhValve:   VariableConfig
  nox: number      // ppm
  ttxm: number     // °C
  lambda: number   // 무차원
  power: number    // MW
}

// KPI 메트릭 정규화 범위 (mockConsole에 없으므로 spec 상수)
const NOX_MAX = 50
const TTXM_MIN = 580
const TTXM_MAX = 1500
const LAMBDA_MIN = 0.9
const LAMBDA_MAX = 1.4
const POWER_MAX = 240
const SMOKE_THRESHOLD = 0.6   // NOx 비율 0.6 = 30ppm부터 가시

function ratioOf(cfg: VariableConfig): number {
  const value = finiteOr(cfg.value, cfg.min)
  return normalize(value, cfg.min, cfg.max)
}

export function cssVarsFromProps(inputs: SchematicInputs): Record<string, string | number> {
  const synR  = ratioOf(inputs.syngasFlow)
  const srvR  = ratioOf(inputs.syngasSrv)
  const g1R   = ratioOf(inputs.syngasGcv1)
  const g1aR  = ratioOf(inputs.syngasGcv1a)
  const g2R   = ratioOf(inputs.syngasGcv2)
  const n2OffsetR = ratioOf(inputs.n2Offset)
  const n2ValveR  = ratioOf(inputs.n2Valve1)
  const n2R   = ratioOf(inputs.n2Flow)
  const igvR  = ratioOf(inputs.igvOpening)
  const ibhR  = ratioOf(inputs.ibhValve)

  const ttxmR = normalize(finiteOr(inputs.ttxm, TTXM_MIN), TTXM_MIN, TTXM_MAX)
  const noxR  = normalize(finiteOr(inputs.nox, 0), 0, NOX_MAX)
  const lambdaR = normalize(finiteOr(inputs.lambda, LAMBDA_MIN), LAMBDA_MIN, LAMBDA_MAX)
  const powerR  = normalize(finiteOr(inputs.power, 0), 0, POWER_MAX)

  const smokeRatio = noxR < SMOKE_THRESHOLD
    ? 0
    : (noxR - SMOKE_THRESHOLD) / (1 - SMOKE_THRESHOLD)

  return {
    '--syn-flow':       Math.max(synR, 0.05),
    '--syn-glow':       lerp(0.25, 1.0, synR),
    '--syn-width':      lerp(2.4, 3.6, synR),
    '--valve-fsagr':    clamp(srvR,  0, 1),
    '--valve-fsag11':   clamp(g1R,   0, 1),
    '--valve-fsag11a':  clamp(g1aR,  0, 1),
    '--valve-fsag12':   clamp(g2R,   0, 1),
    '--n2-flow':        Math.max(n2R, 0.05),
    '--n2-offset':      n2OffsetR,
    '--n2-valve':       n2ValveR,
    '--air-flow':       Math.max(igvR, 0.05),
    '--csbhx-pulse':    ibhR,
    '--flame-scale':    lerp(0.85, 1.15, ttxmR),
    '--flame-opacity':  lerp(0.55, 1.0, ttxmR),
    '--flame-hue':      lerp(45, 12, ttxmR),
    '--flame-intensity': clamp(synR, 0, 1),
    '--smoke-opacity':  lerp(0, 0.85, smokeRatio),
    '--smoke-drift':    lerp(8, 3, noxR),
    '--smoke-tint':     lerp(0, 0.6, noxR),
    '--card-glow-nox':    noxR,
    '--card-glow-ttxm':   ttxmR,
    '--card-glow-lambda': lambdaR,
    '--card-glow-dwatt':  powerR,
    // combustor 가열 강도
    // 연료계 75% (분배 밸브 평균 60% + 합성가스량 15%)
    // 공기/냉각 25% (IGV 10% + N2 역가중 10% + TTXM 5%)
    ...(() => {
      const heat = clamp(
        0.60 * ((srvR + g1R + g1aR + g2R) / 4)
        + 0.15 * synR
        + 0.10 * igvR
        + 0.10 * (1 - n2R)
        + 0.05 * ttxmR,
        0, 1,
      )
      // 시각 강도는 heat^3 큐빅 곡선 — 정상(heat~0.3)은 거의 안 보이고
      // max에서만 강하게 빛나도록 비대칭화
      const intensity = heat * heat * heat
      return {
        '--combustor-heat': heat,
        '--combustor-intensity': intensity,
      }
    })(),
  }
}
