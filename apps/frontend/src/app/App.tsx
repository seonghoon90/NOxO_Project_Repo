import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import type { StreamStatus } from '../features/dashboard/useConsoleState'

type AppMode = 'sim' | 'pred'

export type AppOutletContext = {
  mode: AppMode
  settingsOpen: boolean
  openSettings: () => void
  closeSettings: () => void
  reportStreamStatus: (status: StreamStatus) => void
}

const navItems = [
  { to: '/', label: '서비스 (메인)' },
  { to: '/about', label: '프로젝트 소개' },
  { to: '/database', label: 'DB 구조' },
  { to: '/digital-twin', label: 'Digital Twin' },
  { to: '/team', label: '팀원 소개' },
]

function formatClock(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  const tenth = String(date.getMilliseconds()).padStart(3, '0')[0]
  return `${pad(date.getHours())}시 ${pad(date.getMinutes())}분 ${pad(
    date.getSeconds(),
  )}.${tenth}초`
}

export function App() {
  const location = useLocation()
  const [mode, setMode] = useState<AppMode>('sim')
  const [clock, setClock] = useState(() => formatClock(new Date()))
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('mock')
  const isServicePage = location.pathname === '/'
  const visibleSettingsOpen = isServicePage && settingsOpen
  const streamLabel = streamStatusLabel(streamStatus)

  useEffect(() => {
    const timer = window.setInterval(() => {
      setClock(formatClock(new Date()))
    }, 100)

    return () => window.clearInterval(timer)
  }, [])

  const outletContext = useMemo<AppOutletContext>(
    () => ({
      mode,
      settingsOpen: visibleSettingsOpen,
      openSettings: () => {
        if (isServicePage) {
          setSettingsOpen(true)
        }
      },
      closeSettings: () => setSettingsOpen(false),
      reportStreamStatus: setStreamStatus,
    }),
    [isServicePage, mode, visibleSettingsOpen],
  )

  return (
    <div className="app-shell">
      <header className="top-nav">
        <NavLink to="/" className="logo">
          NOx<span>O</span>
        </NavLink>
        <nav className="top-tabs" aria-label="주요 탭">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                isActive ? 'top-tab active' : 'top-tab'
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        {isServicePage ? (
          <div className="nav-right">
            <div className="mode-toggle" role="tablist" aria-label="모드 전환">
              <button
                type="button"
                className={mode === 'sim' ? 'mode-opt active' : 'mode-opt'}
                onClick={() => setMode('sim')}
              >
                시뮬 모드
              </button>
              <button
                type="button"
                className={mode === 'pred' ? 'mode-opt active' : 'mode-opt'}
                onClick={() => setMode('pred')}
              >
                실시간 예측 모드
              </button>
            </div>
            <div className={`pill-live ${streamLabel.tone}`}>
              <span className="dot" />
              {streamLabel.text}
            </div>
            <button
              type="button"
              className={visibleSettingsOpen ? 'icon-button active' : 'icon-button'}
              aria-label="설정"
              onClick={() => setSettingsOpen(true)}
            >
              <GearIcon />
            </button>
            <div className="nav-clock mono">{clock}</div>
          </div>
        ) : null}
      </header>

      <Outlet context={outletContext} />
    </div>
  )
}

function streamStatusLabel(status: StreamStatus): { text: string; tone: string } {
  switch (status) {
    case 'live':
      return { text: 'LIVE', tone: 'live' }
    case 'connecting':
      return { text: 'CONNECTING', tone: 'caution' }
    case 'reconnecting':
      return { text: 'RECONNECTING', tone: 'caution' }
    case 'disconnected':
      return { text: 'OFFLINE', tone: 'alert' }
    case 'mock':
      return { text: 'TEST', tone: 'normal' }
  }
}

function GearIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 8.5a3.5 3.5 0 1 0 0 7a3.5 3.5 0 0 0 0-7Zm8 4a7.5 7.5 0 0 0-.12-1.31l1.88-1.46l-1.88-3.26l-2.27.64a8.2 8.2 0 0 0-2.25-1.3L15 3h-6l-.36 2.81a8.2 8.2 0 0 0-2.25 1.3l-2.27-.64l-1.88 3.26l1.88 1.46A7.5 7.5 0 0 0 4 12.5c0 .44.04.88.12 1.31l-1.88 1.46l1.88 3.26l2.27-.64c.69.54 1.45.97 2.25 1.3L9 22h6l.36-2.81c.8-.33 1.56-.76 2.25-1.3l2.27.64l1.88-3.26l-1.88-1.46c.08-.43.12-.87.12-1.31Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
