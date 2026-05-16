import { describe, expect, it } from 'vitest'

import { isForecastReady, type RealtimeStreamPayload } from './mockConsole'

type Forecast = RealtimeStreamPayload['forecast']

const validForecast: NonNullable<Forecast> = {
  predicted_nox: 31.2,
  predicted_nox_15pct: 26.68,
  target_time: '2026-05-12T07:35:15.123Z',
  threshold_value: 30.0,
  threshold_exceeded: false,
}

describe('isForecastReady', () => {
  it('정상 예측값 + warning 없음 → ready', () => {
    expect(isForecastReady(validForecast, null)).toBe(true)
  })

  it('forecast === null → not ready (backend warmup/stale 명시 null)', () => {
    expect(isForecastReady(null, null)).toBe(false)
  })

  it('warning 존재 → not ready (forecast 값이 있어도 보류)', () => {
    expect(isForecastReady(validForecast, 'forecast warmup')).toBe(false)
  })

  it('predicted_nox_15pct 음수 → not ready (OOD 외삽 -24 차단)', () => {
    const negative = { ...validForecast, predicted_nox_15pct: -24.3 }
    expect(isForecastReady(negative, null)).toBe(false)
  })

  it('predicted_nox_15pct 부재 시 predicted_nox로 폴백 — 폴백값 음수면 not ready', () => {
    const fallbackNegative: NonNullable<Forecast> = {
      ...validForecast,
      predicted_nox: -5.0,
      predicted_nox_15pct: undefined,
    }
    expect(isForecastReady(fallbackNegative, null)).toBe(false)
  })

  it('predicted_nox_15pct 부재 + predicted_nox 양수 → ready', () => {
    const fallbackPositive: NonNullable<Forecast> = {
      ...validForecast,
      predicted_nox: 18.5,
      predicted_nox_15pct: undefined,
    }
    expect(isForecastReady(fallbackPositive, null)).toBe(true)
  })

  it('값 0 → ready (음수만 차단, 경계값 0은 유효)', () => {
    const zero = { ...validForecast, predicted_nox_15pct: 0 }
    expect(isForecastReady(zero, null)).toBe(true)
  })

  it('비유한값(NaN) → not ready', () => {
    const nan = { ...validForecast, predicted_nox_15pct: Number.NaN }
    expect(isForecastReady(nan, null)).toBe(false)
  })
})
