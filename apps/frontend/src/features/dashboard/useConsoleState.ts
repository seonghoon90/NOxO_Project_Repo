import { useCallback, useEffect, useRef, useState } from 'react'
import {
  appendHistory,
  applyVariableStep,
  CONTROL_VARIABLE_KEYS,
  createStateFromPayload,
  createStateFromSnapshot,
  createInitialConsoleState,
  deriveMetrics,
  safeParseRealtimePayload,
  type BackendConsoleSnapshot,
  type ConsoleState,
  type Mode,
  type VariableConfigUpdate,
  type VariableKey,
  variableSeed,
} from './mockConsole'

/**
 * 백엔드 stream 연결 상태.
 *
 * - `live`         : WebSocket 정상 수신 중
 * - `connecting`   : 최초 핸드셰이크 진행 중
 * - `reconnecting` : 일시적 끊김 후 backoff 재시도 중 (마지막 snapshot 표시)
 * - `disconnected` : 재시도 모두 실패 — 화면은 마지막 실데이터 유지, mock 합성 안 함
 * - `restarting`   : 사용자 명시적 서버 재시작(POST /api/reset) 진행 중 — health 폴링 + 새 세션 부트스트랩
 * - `mock`         : 백엔드 자체 비활성 (`VITE_ENABLE_BACKEND_STREAM=false`) — 명시적 mock
 */
export type StreamStatus =
  | 'live'
  | 'connecting'
  | 'reconnecting'
  | 'disconnected'
  | 'restarting'
  | 'mock'

export type RestartOutcome =
  | { kind: 'ok' }
  | { kind: 'invalid-password'; message: string }
  | { kind: 'unavailable'; message: string }
  | { kind: 'error'; message: string }

const RECONNECT_DELAYS_MS = [1000, 2000, 4000] // exponential backoff 최대 3회
const NORMAL_CLOSE_CODES = new Set([1000]) // 명시적 stop / 정상 종료
const ACTIVE_SESSION_STORAGE_KEY = 'noxo.activeSessionId'

// 서버 재시작(POST /api/reset) 후 컨테이너 부팅 대기.
// 백엔드가 200을 즉시 반환 후 ~1~2초 내 죽고 ~10~20초 후 부활하므로
// 초기 지연 + 최대 ~30초 폴링이면 충분히 커버.
const RESTART_INITIAL_DELAY_MS = 1500
const RESTART_POLL_INTERVAL_MS = 1000
const RESTART_POLL_MAX_MS = 30000

export function useConsoleState(mode: Mode) {
  const tickRef = useRef(0)
  const sessionIdRef = useRef<string | null>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const mockTimerRef = useRef<number | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const reconnectAttemptRef = useRef(0)
  const expectedCloseRef = useRef(false)
  // 순환 참조(connectStream ↔ scheduleReconnect) 회피용 ref. 본 모듈 외부 노출 X.
  const scheduleReconnectRef = useRef<(sid: string) => void>(() => {})

  const enableBackend = import.meta.env.VITE_ENABLE_BACKEND_STREAM !== 'false'
  const [state, setState] = useState<ConsoleState>(() =>
    createInitialConsoleState(!enableBackend),
  )
  const [status, setStatus] = useState<StreamStatus>(
    enableBackend ? 'connecting' : 'mock',
  )

  const stopMockLoop = useCallback(() => {
    if (mockTimerRef.current !== null) {
      window.clearInterval(mockTimerRef.current)
      mockTimerRef.current = null
    }
  }, [])

  const startMockLoop = useCallback(() => {
    stopMockLoop()
    setStatus('mock')
    // mock 모드는 항상 sim 모드 + override=false로 작동 — realtime 토글은 backend 연동 전제.
    setState((current) =>
      current.history.length > 0 ? current : createInitialConsoleState(true),
    )
    mockTimerRef.current = window.setInterval(() => {
      tickRef.current += 1
      setState((current) => {
        const metrics = deriveMetrics(current.variables, 'sim', tickRef.current)
        return {
          ...current,
          metrics,
          history: appendHistory(current.history, metrics, tickRef.current),
        }
      })
    }, 1000)
  }, [stopMockLoop])

  const cancelReconnect = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  /**
   * sid 기준으로 WebSocket 연결을 (재)시도한다.
   *
   * onerror/onclose 시 즉시 mock으로 떨어지지 않고:
   *   1. snapshot API로 마지막 상태 복원
   *   2. exponential backoff (RECONNECT_DELAYS_MS) 로 재시도
   *   3. 모두 실패 시 status='disconnected' (mock 합성 X)
   *
   * `expectedCloseRef`가 true면 정상 종료 — 재연결하지 않는다.
   */
  const connectStream = useCallback(
    (sid: string, isReconnect = false) => {
      if (socketRef.current) {
        expectedCloseRef.current = true
        socketRef.current.close()
        socketRef.current = null
      }
      expectedCloseRef.current = false
      setStatus(isReconnect ? 'reconnecting' : 'connecting')

      const socket = new WebSocket(buildWsUrl(sid))
      socketRef.current = socket

      socket.onopen = () => {
        reconnectAttemptRef.current = 0
        setStatus('live')
      }

      socket.onmessage = (event) => {
        tickRef.current += 1
        const payload = safeParseRealtimePayload(event.data)
        if (!payload) return

        setState((current) => {
          const next = createStateFromPayload(payload, current)
          return {
            ...next,
            history: appendHistory(next.history, next.metrics, payload.tick),
          }
        })
      }

      socket.onerror = () => {
        // onclose가 뒤이어 발생하므로 여기서는 표시만.
        if (!expectedCloseRef.current) {
          setStatus((prev) => (prev === 'live' ? 'reconnecting' : prev))
        }
      }

      socket.onclose = (event) => {
        socketRef.current = null
        if (expectedCloseRef.current) return
        if (NORMAL_CLOSE_CODES.has(event.code)) return
        scheduleReconnectRef.current(sid)
      }
    },
    [],
  )

  /**
   * snapshot 재호출 + 재연결 시도. backoff 한도 초과 시 'disconnected'로 정착.
   */
  const scheduleReconnect = useCallback(
    (sid: string) => {
      const attempt = reconnectAttemptRef.current
      if (attempt >= RECONNECT_DELAYS_MS.length) {
        setStatus('disconnected')
        return
      }

      const delay = RECONNECT_DELAYS_MS[attempt]
      reconnectAttemptRef.current = attempt + 1
      setStatus('reconnecting')

      cancelReconnect()
      reconnectTimerRef.current = window.setTimeout(async () => {
        reconnectTimerRef.current = null
        // 재연결 직후 snapshot으로 세션 생존 여부 판정 (FRONTEND §7).
        const result = await fetchSnapshot(sid)
        if (result.kind === 'gone') {
          // backend reload/재시작으로 세션 소실 → 같은 sid 재연결은 영원히
          // 404. 새 세션을 만들어 그 sid로 연결한다 (죽은 세션 무한 루프 차단).
          try {
            const session = await startSession()
            sessionIdRef.current = session.sid
            setStoredSessionId(session.sid)
            reconnectAttemptRef.current = 0
            if (session.snapshot) {
              setState((current) =>
                createStateFromSnapshot(session.snapshot!, current),
              )
            }
            connectStream(session.sid, true)
          } catch (err) {
            console.error('session recreate after loss failed', err)
            setStatus('disconnected')
          }
          return
        }
        if (result.kind === 'ok') {
          setState((current) =>
            createStateFromSnapshot(result.snapshot, current),
          )
        }
        connectStream(sid, true)
      }, delay)
    },
    [cancelReconnect, connectStream],
  )

  // ref에 최신 scheduleReconnect 노출 — connectStream의 onclose에서 참조.
  useEffect(() => {
    scheduleReconnectRef.current = scheduleReconnect
  }, [scheduleReconnect])

  useEffect(() => {
    if (!enableBackend) return

    const handlePageHide = () => {
      const sid = sessionIdRef.current
      if (sid) {
        stopSessionOnUnload(sid)
      }
    }

    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [enableBackend])

  const disconnectStream = useCallback(() => {
    cancelReconnect()
    expectedCloseRef.current = true
    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
  }, [cancelReconnect])

  useEffect(() => {
    if (!enableBackend) {
      // mock 모드는 컴포넌트 마운트 시점에 시작. setState in effect 룰을 회피하기 위해
      // 다음 macrotask로 미뤄 첫 번째 commit이 끝난 뒤 mock loop을 띄운다.
      const handle = window.setTimeout(() => startMockLoop(), 0)
      return () => {
        window.clearTimeout(handle)
        disconnectStream()
        stopMockLoop()
      }
    }

    let cancelled = false

    async function connectBackend() {
      try {
        const session = await startSession()
        if (cancelled) {
          await stopSession(session.sid)
          return
        }
        sessionIdRef.current = session.sid
        setStoredSessionId(session.sid)
        reconnectAttemptRef.current = 0
        if (session.snapshot) {
          setState((current) => createStateFromSnapshot(session.snapshot!, current))
        }
        connectStream(session.sid)
      } catch (error) {
        // 세션 부트스트랩 자체가 실패한 경우에만 명시적 mock fallback.
        // (백엔드 자체가 응답 불가 → mock 합성이 정직한 표시)
        console.error('Backend session bootstrap failed, falling back to mock.', error)
        startMockLoop()
      }
    }

    void connectBackend()

    return () => {
      cancelled = true
      const sid = sessionIdRef.current
      sessionIdRef.current = null
      clearStoredSessionId(sid)
      disconnectStream()
      stopMockLoop()
      if (sid) {
        void stopSession(sid)
      }
    }
    // 의도: mode 전환은 POST /api/session/{sid}/mode로 처리한다(setMode 액션).
    // mode를 deps에 두면 토글마다 세션이 재생성되어 status가 live→connecting→live로 깜빡이고
    // 누적된 시계열도 리셋되므로 의존성에서 제외한다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [connectStream, disconnectStream, enableBackend, startMockLoop, stopMockLoop])

  // 액션 함수들은 매 렌더 새 참조가 되면 ServicePage의 useEffect[mode, notifyBackendMode]가
  // 매 tick 발화되어 /mode 무한 호출 + /control 누락이 발생한다. useCallback + stateRef로
  // stable identity 유지. state.variables가 필요한 액션은 stateRef를 통해 최신값 접근.
  const stateRef = useRef(state)
  useEffect(() => {
    stateRef.current = state
  }, [state])

  const setActiveVar = useCallback((activeVar: VariableKey) => {
    setState((current) => ({ ...current, activeVar }))
  }, [])

  const updateActiveVariableConfig = useCallback((update: VariableConfigUpdate) => {
    setState((current) => {
      const active = current.variables[current.activeVar]
      // 백엔드 DEFAULT_CONTROL_BOUNDS와 동일한 seed 한계가 절대 상한.
      // 이 콘솔의 모달은 운영자 개인 가드레일 — 백엔드 한계를 넘어설 수 없다.
      const seed = variableSeed[current.activeVar]
      const lo = Math.max(seed.min, Math.min(update.min, update.max))
      const hi = Math.min(seed.max, Math.max(update.min, update.max))
      const nextMin = Math.min(lo, hi)
      const nextMax = Math.max(lo, hi)
      const nextValue = roundForDigits(
        Math.min(nextMax, Math.max(nextMin, active.value)),
        active.digits,
      )

      return {
        ...current,
        variables: {
          ...current.variables,
          [current.activeVar]: {
            ...active,
            min: roundForDigits(nextMin, active.digits),
            max: roundForDigits(nextMax, active.digits),
            step: roundForDigits(Math.max(update.step, 0), active.digits),
            value: nextValue,
          },
        },
      }
    })
  }, [])

  const restoreActiveVariableDefaults = useCallback(() => {
    setState((current) => ({
      ...current,
      variables: {
        ...current.variables,
        [current.activeVar]: {
          ...current.variables[current.activeVar],
          min: variableSeed[current.activeVar].min,
          max: variableSeed[current.activeVar].max,
          step: variableSeed[current.activeVar].step,
        },
      },
    }))
  }, [])

  const toggleOverlay = useCallback(() => {
    setState((current) => ({
      ...current,
      overlayVisible: !current.overlayVisible,
    }))
  }, [])

  const resetControls = useCallback(() => {
    tickRef.current += 1
    if (enableBackend && sessionIdRef.current) {
      const nextVariables = resetVariableValues(stateRef.current.variables)
      void sendControl(sessionIdRef.current, nextVariables)
      setState((current) => ({ ...current, variables: nextVariables }))
      return
    }
    setState((current) => resetConsoleState(current, mode, tickRef.current))
  }, [enableBackend, mode])

  const stepActiveVar = useCallback((direction: 1 | -1) => {
    tickRef.current += 1
    // backend 연결 모드: variables만 즉시 갱신 + control POST.
    // metrics는 다음 WS payload(override 적용된 값)로 갱신되므로 mock 합성 불가.
    // mock 모드: applyVariableStep이 deriveMetrics로 합성된 값 채움.
    if (enableBackend && sessionIdRef.current) {
      const snapshot = stateRef.current
      const active = snapshot.variables[snapshot.activeVar]
      const nextValue = roundForDigits(
        Math.min(
          active.max,
          Math.max(active.min, active.value + active.step * direction),
        ),
        active.digits,
      )
      const nextVariables = {
        ...snapshot.variables,
        [snapshot.activeVar]: { ...active, value: nextValue },
      }
      void sendControl(sessionIdRef.current, nextVariables)
      setState((current) => ({ ...current, variables: nextVariables }))
      return
    }
    setState((current) =>
      applyVariableStep(current, direction, mode, tickRef.current),
    )
  }, [enableBackend, mode])

  const setMode = useCallback((nextMode: Mode) => {
    const sid = sessionIdRef.current
    if (sid && enableBackend) {
      void changeMode(sid, nextMode)
    }
  }, [enableBackend])

  const resetOverride = useCallback(() => {
    const sid = sessionIdRef.current
    if (sid && enableBackend) {
      void resetOverrideRequest(sid)
    }
  }, [enableBackend])

  // POST /api/reset → 백엔드/Kafka producer 컨테이너 동시 재시작.
  // password 필수 — 백엔드 RESET_PASSWORD env와 비교.
  // 응답 200이면 기존 WS 끊고 health 폴링 → 새 sid 발급 → WS 재연결.
  // 401(불일치) / 503(미설정/비-Docker) / 기타는 호출자에 메시지로 전달.
  const restartSession = useCallback(async (password: string): Promise<RestartOutcome> => {
    if (!enableBackend) {
      return {
        kind: 'unavailable',
        message: 'mock 모드에서는 서버 재시작을 사용할 수 없습니다.',
      }
    }
    if (!password) {
      return {
        kind: 'invalid-password',
        message: '비밀번호를 입력하세요.',
      }
    }

    let response: Response
    try {
      response = await fetch(`${apiBaseUrl()}/api/reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
    } catch (error) {
      console.warn('reset request failed', error)
      return {
        kind: 'error',
        message: '서버 재시작 요청을 보내지 못했습니다.',
      }
    }

    if (!response.ok) {
      const message = await extractRestartErrorMessage(response)
      if (response.status === 401) {
        return { kind: 'invalid-password', message: '비밀번호가 일치하지 않습니다.' }
      }
      return response.status === 503
        ? { kind: 'unavailable', message }
        : { kind: 'error', message }
    }

    // 이후 자동 재연결을 막고 깔끔하게 끊는다 — 새 sid 발급 전에 옛 sid로 reconnect되면 404.
    const previousSid = sessionIdRef.current
    sessionIdRef.current = null
    cancelReconnect()
    reconnectAttemptRef.current = 0
    expectedCloseRef.current = true
    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }
    clearStoredSessionId(previousSid)
    setStatus('restarting')

    // 백엔드가 죽고 다시 살아날 때까지 대기.
    await sleep(RESTART_INITIAL_DELAY_MS)
    const ready = await pollBackendHealth()
    if (!ready) {
      setStatus('disconnected')
      return {
        kind: 'error',
        message: '서버 응답 대기 시간이 초과되었습니다. 잠시 후 다시 시도하세요.',
      }
    }

    try {
      const session = await startSession()
      sessionIdRef.current = session.sid
      setStoredSessionId(session.sid)
      reconnectAttemptRef.current = 0
      if (session.snapshot) {
        setState((current) => createStateFromSnapshot(session.snapshot!, current))
      }
      connectStream(session.sid)
      return { kind: 'ok' }
    } catch (error) {
      console.error('post-restart session bootstrap failed', error)
      setStatus('disconnected')
      return {
        kind: 'error',
        message: '재시작 후 세션 재구성에 실패했습니다.',
      }
    }
  }, [cancelReconnect, connectStream, enableBackend])

  return {
    state,
    status,
    setActiveVar,
    updateActiveVariableConfig,
    restoreActiveVariableDefaults,
    toggleOverlay,
    resetControls,
    stepActiveVar,
    setMode,
    resetOverride,
    restartSession,
  }
}

async function startSession() {
  const staleSid = getStoredSessionId()
  if (staleSid) {
    await stopSession(staleSid)
    clearStoredSessionId(staleSid)
  }

  // 세션은 항상 sim 모드로 시작 — 사용자가 realtime 토글하면 POST /api/session/{sid}/mode로 전환.
  const initialCondition = buildControlTagPayload((key) => variableSeed[key].base)

  const response = await fetch(`${apiBaseUrl()}/api/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      initial_condition: initialCondition,
    }),
  })
  if (!response.ok) throw new Error(`session start failed: ${response.status}`)
  const payload = (await response.json()) as { sid?: string; snapshot?: BackendConsoleSnapshot }
  if (!payload.sid) throw new Error('session id missing')
  return {
    sid: payload.sid,
    snapshot: payload.snapshot,
  }
}

// 'gone' = backend가 세션을 모름(404). reload/재시작으로 in-memory 세션이
// 소실된 상태 → 같은 sid 재연결은 무의미하므로 새 세션을 만들어야 한다.
type SnapshotResult =
  | { kind: 'ok'; snapshot: BackendConsoleSnapshot }
  | { kind: 'gone' }
  | { kind: 'error' }

async function fetchSnapshot(sid: string): Promise<SnapshotResult> {
  try {
    const response = await fetch(`${apiBaseUrl()}/api/session/${sid}/snapshot`)
    if (response.status === 404) return { kind: 'gone' }
    if (!response.ok) return { kind: 'error' }
    return {
      kind: 'ok',
      snapshot: (await response.json()) as BackendConsoleSnapshot,
    }
  } catch {
    return { kind: 'error' }
  }
}

function resetVariableValues(variables: ConsoleState['variables']): ConsoleState['variables'] {
  return CONTROL_VARIABLE_KEYS.reduce<ConsoleState['variables']>((acc, key) => {
    acc[key] = {
      ...variables[key],
      value: variableSeed[key].base,
    }
    return acc
  }, structuredClone(variables))
}

function resetConsoleState(current: ConsoleState, mode: Mode, tick: number): ConsoleState {
  const variables = resetVariableValues(current.variables)
  const metrics = deriveMetrics(variables, mode, tick)

  return {
    ...current,
    variables,
    metrics,
    history: appendHistory(current.history, metrics, tick),
  }
}

async function sendControl(
  sid: string,
  variables: ConsoleState['variables'],
) {
  // 백엔드 ControlPayload는 10개 변수 모두 required (apps/backend/app/schemas/session.py).
  const payload = buildControlTagPayload((key) => variables[key].value)

  await fetch(`${apiBaseUrl()}/api/session/${sid}/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

async function changeMode(sid: string, mode: Mode): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/session/${sid}/mode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  })
  if (!response.ok) throw new Error(`set mode failed: ${response.status}`)
}

async function resetOverrideRequest(sid: string): Promise<void> {
  await fetch(`${apiBaseUrl()}/api/session/${sid}/reset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function extractRestartErrorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string; message?: string }
    if (typeof body.detail === 'string' && body.detail.length > 0) return body.detail
    if (typeof body.message === 'string' && body.message.length > 0) return body.message
  } catch {
    // JSON 아님 — fallback 메시지로 떨어진다
  }
  return response.status === 503
    ? '현재 환경에서는 서버 재시작이 지원되지 않습니다.'
    : `서버 재시작 요청이 실패했습니다 (HTTP ${response.status}).`
}

// GET /api/health 200을 받을 때까지 일정 간격으로 폴링.
// AbortController로 단일 시도 타임아웃을 짧게 잡아 — 백엔드가 죽어 있는 동안 fetch가 길게 걸리지 않게.
async function pollBackendHealth(): Promise<boolean> {
  const deadline = Date.now() + RESTART_POLL_MAX_MS
  while (Date.now() < deadline) {
    try {
      const controller = new AbortController()
      const timer = window.setTimeout(() => controller.abort(), 1500)
      const response = await fetch(`${apiBaseUrl()}/api/health`, {
        signal: controller.signal,
      })
      window.clearTimeout(timer)
      if (response.ok) return true
    } catch {
      // 컨테이너 부팅 중 — 다음 폴링까지 대기
    }
    await sleep(RESTART_POLL_INTERVAL_MS)
  }
  return false
}

function buildControlTagPayload(
  pickValue: (key: VariableKey) => number,
): Record<string, number> {
  return CONTROL_VARIABLE_KEYS.reduce<Record<string, number>>((acc, key) => {
    acc[variableSeed[key].rawName] = pickValue(key)
    return acc
  }, {})
}

async function stopSession(sid: string) {
  try {
    await fetch(`${apiBaseUrl()}/api/session/${sid}/stop`, {
      method: 'POST',
      keepalive: true,
    })
  } catch (error) {
    console.warn('session stop failed', error)
  }
}

function stopSessionOnUnload(sid: string) {
  if (typeof navigator.sendBeacon !== 'function') return
  navigator.sendBeacon(`${apiBaseUrl()}/api/session/${sid}/stop`)
}

function getStoredSessionId() {
  return window.sessionStorage.getItem(ACTIVE_SESSION_STORAGE_KEY)
}

function setStoredSessionId(sid: string) {
  window.sessionStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sid)
}

function clearStoredSessionId(sid?: string | null) {
  const current = getStoredSessionId()
  if (!sid || current === sid) {
    window.sessionStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY)
  }
}

function apiBaseUrl() {
  return String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')
}

function buildWsUrl(sid: string) {
  const httpBase = apiBaseUrl()
  const wsBase = httpBase
    ? httpBase.startsWith('https://')
      ? httpBase.replace('https://', 'wss://')
      : httpBase.replace('http://', 'ws://')
    : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
  return `${wsBase}/api/session/${sid}/stream`
}

function roundForDigits(value: number, digits: number) {
  const factor = 10 ** digits
  return Math.round(value * factor) / factor
}
