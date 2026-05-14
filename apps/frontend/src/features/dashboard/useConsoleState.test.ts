import { describe, expect, it } from 'vitest'
import {
  createInitialConsoleState,
  createStateFromPayload,
  safeParseRealtimePayload,
  type RealtimeStreamPayload,
} from './mockConsole'

const samplePayload: RealtimeStreamPayload = {
  v: 1,
  sid: 'abc',
  tick: 5,
  ts: '2026-05-12T07:30:15.123Z',
  mode: 'realtime',
  override_active: false,
  current: {
    controls: {
      syngas_flow: 100.5,
      igv_opening: 80.2,
      n2_offset: 5.1,
      n2_valve_1: 42.0,
      syngas_srv: 60.3,
      syngas_gcv_1: 55.1,
      syngas_gcv_1a: 54.8,
      syngas_gcv_2: 53.9,
      ibh_valve: 30.0,
      n2_flow: 25.5,
    },
    outputs: {
      nox: 28.5,
      nox_15pct: 24.36,
      exhaust_temp: 580.0,
      power: 165.2,
      lambda_: 2.1,
      efficiency: 0.42,
    },
  },
  kafka_latest: null,
  forecast: {
    predicted_nox: 31.2,
    predicted_nox_15pct: 26.68,
    target_time: '2026-05-12T07:35:15.123Z',
    threshold_value: 30.0,
    threshold_exceeded: true,
  },
  warning: null,
}

describe('safeParseRealtimePayload', () => {
  it('parses valid v1 payload', () => {
    const raw = JSON.stringify(samplePayload)
    const parsed = safeParseRealtimePayload(raw)
    expect(parsed?.mode).toBe('realtime')
    expect(parsed?.forecast?.predicted_nox).toBe(31.2)
  })

  it('returns null for invalid JSON', () => {
    expect(safeParseRealtimePayload('not json')).toBeNull()
  })

  it('returns null for non-v1 payload', () => {
    const raw = JSON.stringify({ ...samplePayload, v: 99 })
    expect(safeParseRealtimePayload(raw)).toBeNull()
  })
})

describe('createStateFromPayload', () => {
  it('maps outputs to metrics', () => {
    const initial = createInitialConsoleState(false)
    const next = createStateFromPayload(samplePayload, initial)
    expect(next.metrics.nox).toBe(28.5)
    expect(next.metrics.nox15pct).toBe(24.36)
    expect(next.metrics.predictedNox).toBe(26.68)
    expect(next.forecast?.predicted_nox).toBe(31.2)
    expect(next.forecast?.predicted_nox_15pct).toBe(26.68)
  })

  it('falls back predictedNox to outputs.nox_15pct when forecast is null', () => {
    const sim: RealtimeStreamPayload = {
      ...samplePayload,
      mode: 'sim',
      forecast: null,
    }
    const next = createStateFromPayload(sim, createInitialConsoleState(false))
    expect(next.metrics.predictedNox).toBe(24.36)
    expect(next.forecast).toBeNull()
  })

  it('preserves override_active flag', () => {
    const payload: RealtimeStreamPayload = {
      ...samplePayload,
      mode: 'sim',
      override_active: true,
      forecast: null,
    }
    const next = createStateFromPayload(payload, createInitialConsoleState(false))
    expect(next.overrideActive).toBe(true)
  })
})
