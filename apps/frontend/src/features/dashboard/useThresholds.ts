import { useEffect, useState } from 'react'
import { NOX_LIMIT as DEFAULT_NOX_LIMIT } from './mockConsole'

/**
 * 백엔드 `GET /api/threshold`에서 운영 임계 묶음을 1회 받아온다.
 *
 * 단일 진실원은 `digital_twin/simulation/config.py`의 `ThresholdConfig`.
 * 운영 중 동적 변경이 없는 상수 성격이라 polling 없이 마운트 시 1회 호출하고,
 * 백엔드 미응답 시 아래 fallback(가안 기본값)을 사용한다.
 */
export type Thresholds = {
  noxLimit: number
  efficiencyCaution: number
  efficiencyDanger: number
  exhaustCautionC: number
  exhaustDangerC: number
  lambdaCautionLo: number
  lambdaCautionHi: number
  lambdaDangerLo: number
  lambdaDangerHi: number
}

// SoT는 digital_twin/simulation/config.py::ThresholdConfig. backend 미응답 시 화면 채터링을
// 막기 위해 동일 값을 fallback으로 둔다. SoT 변경 시 함께 동기화.
const FALLBACK_THRESHOLDS: Thresholds = {
  noxLimit: DEFAULT_NOX_LIMIT,
  efficiencyCaution: 0.370,
  efficiencyDanger: 0.360,
  exhaustCautionC: 642,
  exhaustDangerC: 650,
  lambdaCautionLo: 2.0,
  lambdaCautionHi: 3.5,
  lambdaDangerLo: 1.5,
  lambdaDangerHi: 4.0,
}

type ThresholdResponse = {
  nox_ppm_limit?: number
  efficiency_caution?: number
  efficiency_danger?: number
  exhaust_caution_c?: number
  exhaust_danger_c?: number
  lambda_caution_lo?: number
  lambda_caution_hi?: number
  lambda_danger_lo?: number
  lambda_danger_hi?: number
}

export function useThresholds(): Thresholds {
  const [thresholds, setThresholds] = useState<Thresholds>(FALLBACK_THRESHOLDS)
  const enableBackend = import.meta.env.VITE_ENABLE_BACKEND_STREAM !== 'false'

  useEffect(() => {
    if (!enableBackend) return
    let cancelled = false

    void (async () => {
      try {
        const base = String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
        const response = await fetch(`${base}/api/threshold`)
        if (!response.ok) return
        const payload = (await response.json()) as ThresholdResponse
        if (cancelled) return
        setThresholds((current) => mergeThresholds(current, payload))
      } catch (error) {
        console.warn('threshold fetch failed, using fallback', error)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [enableBackend])

  return thresholds
}

function mergeThresholds(base: Thresholds, payload: ThresholdResponse): Thresholds {
  return {
    noxLimit: pickNumber(payload.nox_ppm_limit, base.noxLimit),
    efficiencyCaution: pickNumber(payload.efficiency_caution, base.efficiencyCaution),
    efficiencyDanger: pickNumber(payload.efficiency_danger, base.efficiencyDanger),
    exhaustCautionC: pickNumber(payload.exhaust_caution_c, base.exhaustCautionC),
    exhaustDangerC: pickNumber(payload.exhaust_danger_c, base.exhaustDangerC),
    lambdaCautionLo: pickNumber(payload.lambda_caution_lo, base.lambdaCautionLo),
    lambdaCautionHi: pickNumber(payload.lambda_caution_hi, base.lambdaCautionHi),
    lambdaDangerLo: pickNumber(payload.lambda_danger_lo, base.lambdaDangerLo),
    lambdaDangerHi: pickNumber(payload.lambda_danger_hi, base.lambdaDangerHi),
  }
}

function pickNumber(value: number | undefined, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}
