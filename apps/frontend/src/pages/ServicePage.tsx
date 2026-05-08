import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import hmiConceptC from '../assets/hmi-concept-c.png'
import {
  CONTROL_VARIABLE_KEYS,
  NOX_LIMIT,
  POWER_RAW_NAME,
  PRIMARY_VARIABLE_KEYS,
  type MetricPoint,
  type VariableConfig,
  type VariableConfigUpdate,
  type VariableKey,
  variableSeed,
} from '../features/dashboard/mockConsole'
import { useConsoleState, type StreamStatus } from '../features/dashboard/useConsoleState'
import type { AppOutletContext } from '../app/App'

const controlVariableOrder: VariableKey[] = CONTROL_VARIABLE_KEYS
const overviewVariableOrder: VariableKey[] = PRIMARY_VARIABLE_KEYS
const POWER_LIMIT = 240

export function ServicePage() {
  const { mode, settingsOpen, closeSettings, reportStreamStatus } = useOutletContext<AppOutletContext>()
  const {
    state,
    status,
    setActiveVar,
    stepActiveVar,
    resetControls,
    updateActiveVariableConfig,
    restoreActiveVariableDefaults,
  } = useConsoleState(mode)
  const [draftConfig, setDraftConfig] = useState<VariableConfigUpdate | null>(null)

  const activeVariable = state.variables[state.activeVar]
  const resolvedDraftConfig = draftConfig ?? {
    min: activeVariable.min,
    max: activeVariable.max,
    step: activeVariable.step,
  }
  const displayedNox = mode === 'sim' ? state.metrics.nox : state.metrics.predictedNox
  const streamLabel = streamStatusLabel(status)
  const noxStatus = displayedNox > NOX_LIMIT ? '위험' : streamLabel.text
  const controlCards = overviewVariableOrder.map((key) => state.variables[key])
  const noxValues = state.history.length > 0 ? state.history.map((point) => point.nox) : [displayedNox]
  const powerValues = state.history.length > 0 ? state.history.map((point) => point.power) : [state.metrics.power]
  const noxHeadroom = NOX_LIMIT - displayedNox
  const powerHeadroom = state.metrics.power - POWER_LIMIT
  const noxHeadroomTone = headroomTone(noxHeadroom, 12, 5)
  const powerHeadroomTone = headroomTone(powerHeadroom, 12, 5)
  const noxRange = getRange(noxValues)
  const powerRange = getRange(powerValues)
  const tableRows = [
    ['NOx', displayedNox.toFixed(1), 'ppm', NOX_LIMIT.toFixed(1), '5.0s', displayedNox > NOX_LIMIT ? '위험' : '정상'],
    ['발전량', state.metrics.power.toFixed(1), 'MW', '248.6', '8.5s', state.metrics.power < 240 ? '주의' : '정상'],
    ['일산화탄소 (CO)', state.metrics.co.toFixed(1), 'ppm', '200.0', '1.8s', '정상'],
    ['배기온도', state.metrics.exhaust.toFixed(1), '°C', '580.0', '10.0s', state.metrics.exhaust > 600 ? '주의' : '정상'],
    ['공기비 (λ)', state.metrics.lambda.toFixed(2), '-', '1.10', '0.9s', '정상'],
  ]
  const handleCloseSettings = useCallback(() => {
    setDraftConfig(null)
    closeSettings()
  }, [closeSettings])

  useEffect(() => {
    reportStreamStatus(status)
  }, [reportStreamStatus, status])

  useEffect(() => {
    if (!settingsOpen) return
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleCloseSettings()
      }
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [handleCloseSettings, settingsOpen])

  return (
    <main className="service-page">
      <section className="main-body">
        <div className="left-column">
          <div className="kpi-row">
            <KpiCard
              title="NOx"
              value={displayedNox}
              unit="ppm"
              subtitle={`허용치 ${NOX_LIMIT} ppm`}
              status={noxStatus}
              emphatic
            />
            <KpiCard
              title="발전량"
              value={state.metrics.power}
              unit="MW"
              subtitle={POWER_RAW_NAME}
              status="정상"
              emphatic
            />
            {controlCards.map((variable) => (
              <KpiCard
                key={variable.key}
                title={variable.label}
                value={variable.value}
                unit={variable.unit}
                status="제어"
                digits={variable.digits}
                subtitle={variable.rawName}
              />
            ))}
          </div>

          <section className="panel plant-card">
            <header className="panel-header">
              <div className="panel-header-left">
                <span className="panel-title">공정 모니터링</span>
              </div>
            </header>
            <div className="plant-body" style={{ height: 500 }}>
              <HmiMonitor
                controls={state.variables}
                nox={displayedNox}
                exhaust={state.metrics.exhaust}
                lambda={state.metrics.lambda}
                power={state.metrics.power}
              />
            </div>
          </section>

          <div className="chart-row">
            <section className="panel chart-card nox-glow">
              <header className="chart-header">
                <div>
                  <div className="chart-title">NOx 시계열</div>
                  <div className="chart-subtitle">ppm · 최근 60s</div>
                </div>
                <span className={`stream-badge ${streamLabel.tone}`}>{streamLabel.text}</span>
              </header>
              <div className="chart-body">
                <NoxChart history={state.history} current={displayedNox} />
              </div>
            </section>

            <section className="panel chart-card">
              <header className="chart-header">
                <div>
                  <div className="chart-title">일산화탄소 (CO) / 공기비 (λ) / 배기온도</div>
                  <div className="chart-subtitle">정규화 · 최근 60s</div>
                </div>
                <div className="chart-legend mono">
                  <span className="legend-co">일산화탄소</span>
                  <span className="legend-lambda">공기비</span>
                  <span className="legend-exhaust">배기온도</span>
                </div>
              </header>
              <div className="chart-body">
                <MultiChart history={state.history} />
              </div>
            </section>
          </div>

          <section className="panel table-card">
            <table className="data-table">
              <thead>
                <tr>
                  <th>변수명</th>
                  <th>현재값</th>
                  <th>단위</th>
                  <th>타겟값</th>
                  <th>시간상수 τ</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map(([name, value, unit, target, tau, status]) => (
                  <tr key={name}>
                    <td className="label-cell">{name}</td>
                    <td>{value}</td>
                    <td className="muted-cell">{unit}</td>
                    <td className="muted-cell">{target}</td>
                    <td className="muted-cell">{tau}</td>
                    <td>
                      <span className={statusClass(status)}>{status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-title">제어 변수 선택</div>
            <div className="chip-row">
              {controlVariableOrder.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={state.activeVar === key ? 'chip active' : 'chip'}
                  onClick={() => setActiveVar(key)}
                >
                  {state.variables[key].shortLabel}
                </button>
              ))}
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">조작 패널</div>
            <div className="control-box">
              <div className="control-label">현재 조작 중:</div>
              <div className="control-name">{activeVariable.label}</div>
              <div className="control-meta mono">{activeVariable.rawName}</div>
              <div className="control-value mono">
                {formatValue(activeVariable.value, activeVariable.digits)}
                <span className="control-unit">{activeVariable.unit}</span>
              </div>
              <div className="control-base mono">
                기준치 {formatValue(activeVariable.base, activeVariable.digits)} {activeVariable.unit}
              </div>
            </div>
            <div className="stepper-row">
              <div className="stepper">
                <button
                  type="button"
                  className="step-button"
                  onClick={() => stepActiveVar(-1)}
                  disabled={activeVariable.value <= activeVariable.min}
                  aria-label="감소"
                >
                  <ArrowDownIcon />
                </button>
                <div className="step-mid mono">±{formatValue(activeVariable.step, activeVariable.digits)}</div>
                <button
                  type="button"
                  className="step-button"
                  onClick={() => stepActiveVar(1)}
                  disabled={activeVariable.value >= activeVariable.max}
                  aria-label="증가"
                >
                  <ArrowUpIcon />
                </button>
              </div>
              <button type="button" className="icon-button" onClick={resetControls} aria-label="초기화">
                <ResetIcon />
              </button>
            </div>
          </div>

          <div className="sidebar-section telemetry">
            <div className="sidebar-title">운영 요약</div>
            <div className="summary-highlight">
              <div className="summary-label">NOx 임계 여유</div>
              <div className={`summary-value ${noxHeadroomTone}`}>
                {noxHeadroom >= 0 ? `+${noxHeadroom.toFixed(1)}` : `${noxHeadroom.toFixed(1)}`}
                <span className="summary-unit">ppm</span>
              </div>
            </div>
            <div className="summary-highlight">
              <div className="summary-label">발전량 임계 여유</div>
              <div className={`summary-value ${powerHeadroomTone}`}>
                {powerHeadroom >= 0 ? `+${powerHeadroom.toFixed(1)}` : `${powerHeadroom.toFixed(1)}`}
                <span className="summary-unit">MW</span>
              </div>
            </div>
            <div className="telemetry-divider" />
            <div className="summary-grid">
              <SummaryRangeMetric
                label="최근 60초 NOx"
                minLabel="최솟값"
                minValue={noxRange.min.toFixed(1)}
                maxLabel="최댓값"
                maxValue={noxRange.max.toFixed(1)}
                unit="ppm"
              />
              <SummaryRangeMetric
                label="최근 60초 발전량"
                minLabel="최솟값"
                minValue={powerRange.min.toFixed(1)}
                maxLabel="최댓값"
                maxValue={powerRange.max.toFixed(1)}
                unit="MW"
              />
            </div>
          </div>
        </aside>
      </section>

      {settingsOpen ? (
        <div className="modal-backdrop" onClick={handleCloseSettings}>
          <section
            className="settings-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="settings-modal-header">
              <div>
                <div id="settings-modal-title" className="settings-modal-title">
                  {activeVariable.label} 조작 가드레일
                </div>
                <div className="settings-modal-subtitle mono">{activeVariable.rawName}</div>
                <div className="settings-modal-hint">
                  이 콘솔의 ▲▼ 조작 범위만 좁힙니다. 운영 한계({variableSeed[activeVariable.key].min}~{variableSeed[activeVariable.key].max} {activeVariable.unit}) 자체는 변경되지 않습니다.
                </div>
              </div>
              <button type="button" className="icon-button" onClick={handleCloseSettings} aria-label="닫기">
                <CloseIcon />
              </button>
            </div>

            <div className="settings-form">
              <div className="settings-variable-picker">
                <div className="settings-field-label">입력 변수 선택</div>
                <div className="settings-chip-row">
                  {controlVariableOrder.map((key) => (
                    <button
                      key={`settings-${key}`}
                      type="button"
                      className={state.activeVar === key ? 'chip active' : 'chip'}
                      onClick={() => {
                        setActiveVar(key)
                        setDraftConfig(null)
                      }}
                    >
                      {state.variables[key].shortLabel}
                    </button>
                  ))}
                </div>
              </div>
              <SettingField
                label="상한"
                unit={activeVariable.unit}
                value={resolvedDraftConfig.max}
                digits={activeVariable.digits}
                min={variableSeed[activeVariable.key].min}
                max={variableSeed[activeVariable.key].max}
                onChange={(value) =>
                  setDraftConfig((current) => ({ ...(current ?? resolvedDraftConfig), max: value }))
                }
              />
              <SettingField
                label="하한"
                unit={activeVariable.unit}
                value={resolvedDraftConfig.min}
                digits={activeVariable.digits}
                min={variableSeed[activeVariable.key].min}
                max={variableSeed[activeVariable.key].max}
                onChange={(value) =>
                  setDraftConfig((current) => ({ ...(current ?? resolvedDraftConfig), min: value }))
                }
              />
              <SettingField
                label="step"
                unit={activeVariable.unit}
                value={resolvedDraftConfig.step}
                digits={activeVariable.digits}
                onChange={(value) =>
                  setDraftConfig((current) => ({ ...(current ?? resolvedDraftConfig), step: value }))
                }
              />
            </div>

            <div className="settings-modal-actions">
              <button
                type="button"
                className="button-secondary"
                onClick={() => {
                  const defaults = variableSeed[activeVariable.key]
                  restoreActiveVariableDefaults()
                  setDraftConfig({
                    min: defaults.min,
                    max: defaults.max,
                    step: defaults.step,
                  })
                }}
              >
                기본값 복원
              </button>
              <button
                type="button"
                className="button-primary"
                onClick={() => {
                  updateActiveVariableConfig(draftConfig ?? resolvedDraftConfig)
                  handleCloseSettings()
                }}
              >
                적용
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </main>
  )
}

function SettingField({
  label,
  unit,
  value,
  digits,
  min,
  max,
  onChange,
}: {
  label: string
  unit: string
  value: number
  digits: number
  min?: number
  max?: number
  onChange: (value: number) => void
}) {
  return (
    <label className="settings-field">
      <span className="settings-field-label">{label}</span>
      <div className="settings-input-row">
        <input
          className="settings-input mono"
          type="number"
          step={digits === 0 ? 1 : Number(`0.${'0'.repeat(Math.max(digits - 1, 0))}1`)}
          min={min}
          max={max}
          value={value}
          onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(Number(event.target.value))}
        />
        <span className="settings-field-unit">{unit}</span>
      </div>
    </label>
  )
}

function KpiCard({
  title,
  value,
  unit,
  status,
  subtitle,
  emphatic,
  caution,
  digits = 1,
}: {
  title: string
  value: number
  unit: string
  status: string
  subtitle?: string
  emphatic?: boolean
  caution?: boolean
  digits?: number
}) {
  const [integer, decimal = '0'] = value.toFixed(digits).split('.')

  return (
    <section className={emphatic ? 'kpi-card kpi-card-primary' : caution ? 'kpi-card caution-border' : 'kpi-card'}>
      <div className="kpi-header">
        <div className="kpi-name">{title}</div>
        <span className={statusClass(status)}>{status}</span>
      </div>
      <div className="kpi-value-row">
        <div className={caution ? 'kpi-value caution-text' : emphatic ? 'kpi-value kpi-value-large' : 'kpi-value'}>
          {integer}
          <span className="kpi-decimal">.{decimal}</span>
        </div>
        <div className="kpi-subtitle">{subtitle ?? unit}</div>
      </div>
    </section>
  )
}

function SummaryRangeMetric({
  label,
  minLabel,
  minValue,
  maxLabel,
  maxValue,
  unit,
}: {
  label: string
  minLabel: string
  minValue: string
  maxLabel: string
  maxValue: string
  unit: string
}) {
  return (
    <div className="summary-range-metric">
      <div className="summary-metric-label">{label}</div>
      <div className="summary-range-row">
        <span className="summary-range-label">{minLabel}</span>
        <span className="summary-metric-value">
          {minValue}
          <span className="summary-metric-unit">{unit}</span>
        </span>
      </div>
      <div className="summary-range-row">
        <span className="summary-range-label">{maxLabel}</span>
        <span className="summary-metric-value">
          {maxValue}
          <span className="summary-metric-unit">{unit}</span>
        </span>
      </div>
    </div>
  )
}

function NoxChart({ history, current }: { history: MetricPoint[]; current: number }) {
  const width = 560
  const height = 170
  const bottomLabelY = height - 12
  const thresholdPinnedY = 22
  if (history.length < 2) {
    return <ChartPlaceholder width={width} height={height} />
  }
  const values = history.map((point) => point.nox)
  const focusedRange = createRange(values, 0.28, 1.2)
  const max = focusedRange.max
  const min = focusedRange.min
  const thresholdInRange = NOX_LIMIT <= max
  const line = buildLinePath(values, min, max, width, height)
  const area = `${line} L ${width} ${height} L 0 ${height} Z`
  const thresholdY = thresholdInRange ? scaleY(NOX_LIMIT, min, max, height) : thresholdPinnedY
  const currentY = scaleY(current, min, max, height)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <defs>
        <linearGradient id="noxArea" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line
        x1="0"
        y1={thresholdY}
        x2={width}
        y2={thresholdY}
        stroke="#EF4444"
        strokeOpacity="0.42"
        strokeDasharray="5 4"
        strokeWidth="1"
      />
      <text x="8" y={thresholdY - 6} className="svg-label svg-alert">
        {NOX_LIMIT} ppm
      </text>
      <path d={area} fill="url(#noxArea)" />
      <path d={line} fill="none" stroke="#3B82F6" strokeWidth="2" strokeLinecap="round" />
      <circle cx={width} cy={currentY} r="3.2" fill="#3B82F6" />
      <text x={width - 8} y={currentY - 10} textAnchor="end" className="svg-label svg-accent">
        {current.toFixed(1)}
      </text>
      <text x="8" y={bottomLabelY} className="svg-label">
        -60s
      </text>
      <text x={width - 8} y={bottomLabelY} textAnchor="end" className="svg-label">
        now
      </text>
    </svg>
  )
}

function MultiChart({ history }: { history: MetricPoint[] }) {
  const width = 560
  const height = 170
  const bottomLabelY = height - 12
  const padding = { top: 14, right: 48, bottom: 22, left: 48 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  if (history.length < 2) {
    return <ChartPlaceholder width={width} height={height} />
  }
  const coValues = history.map((point) => point.co)
  const lambdaValues = history.map((point) => point.lambda)
  const exhaustValues = history.map((point) => point.exhaust)
  const coRange = createRange(coValues, 0.12, 0.6)
  const lambdaRange = createRange(lambdaValues, 0.18, 0.02)
  const exhaustRange = createRange(exhaustValues, 0.08, 1.2)

  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {[0, 0.5, 1].map((ratio) => {
        const y = padding.top + plotHeight * ratio
        return (
          <line
            key={ratio}
            x1={padding.left}
            y1={y}
            x2={width - padding.right}
            y2={y}
            stroke="rgba(148, 163, 184, 0.14)"
            strokeDasharray="4 4"
            strokeWidth="1"
          />
        )
      })}
      <path
        d={buildSeriesPath(coValues, coRange.min, coRange.max, padding.left, padding.top, plotWidth, plotHeight)}
        fill="none"
        stroke="#10B981"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d={buildSeriesPath(lambdaValues, lambdaRange.min, lambdaRange.max, padding.left, padding.top, plotWidth, plotHeight)}
        fill="none"
        stroke="#3B82F6"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d={buildSeriesPath(exhaustValues, exhaustRange.min, exhaustRange.max, padding.left, padding.top, plotWidth, plotHeight)}
        fill="none"
        stroke="#F59E0B"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <text x="2" y="12" className="svg-label" fill="#10B981">
        {coRange.max.toFixed(1)} ppm
      </text>
      <text x="6" y={bottomLabelY} className="svg-label" fill="#10B981">
        {coRange.min.toFixed(1)} ppm
      </text>
      <text x={width / 2} y="12" textAnchor="middle" className="svg-label" fill="#3B82F6">
        λ {lambdaRange.max.toFixed(2)}
      </text>
      <text x={width / 2} y={bottomLabelY} textAnchor="middle" className="svg-label" fill="#3B82F6">
        λ {lambdaRange.min.toFixed(2)}
      </text>
      <text x={width - 2} y="12" textAnchor="end" className="svg-label" fill="#F59E0B">
        {exhaustRange.max.toFixed(1)} °C
      </text>
      <text x={width - 6} y={bottomLabelY} textAnchor="end" className="svg-label" fill="#F59E0B">
        {exhaustRange.min.toFixed(1)} °C
      </text>
      <text x={padding.left} y={bottomLabelY} className="svg-label">
        -60s
      </text>
      <text x={width - padding.right} y={bottomLabelY} textAnchor="end" className="svg-label">
        now
      </text>
    </svg>
  )
}

function ChartPlaceholder({ width, height }: { width: number; height: number }) {
  return (
    <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      <text
        x={width / 2}
        y={height / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        className="svg-label"
      >
        warming up — 데이터 수집 중
      </text>
    </svg>
  )
}

function buildLinePath(values: number[], min: number, max: number, width: number, height: number) {
  return values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width
      const y = scaleY(value, min, max, height)
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function buildSeriesPath(
  values: number[],
  min: number,
  max: number,
  left: number,
  top: number,
  width: number,
  height: number,
) {
  return values
    .map((value, index) => {
      const x = left + (index / (values.length - 1)) * width
      const y = top + scaleY(value, min, max, height)
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function createRange(values: number[], paddingRatio: number, minimumPadding: number) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = Math.max(max - min, minimumPadding)
  const pad = spread * paddingRatio

  return {
    min: min - pad,
    max: max + pad,
  }
}

function scaleY(value: number, min: number, max: number, height: number) {
  const range = max - min || 1
  return height - ((value - min) / range) * (height * 0.78) - height * 0.08
}

function formatValue(value: number, digits: number) {
  return value.toFixed(digits)
}

function getRange(values: number[]) {
  return {
    min: Math.min(...values),
    max: Math.max(...values),
  }
}

function headroomTone(value: number, cautionThreshold: number, dangerThreshold: number) {
  if (value <= dangerThreshold) return 'summary-value-danger'
  if (value <= cautionThreshold) return 'summary-value-caution'
  return 'summary-value-safe'
}

function statusClass(status: string) {
  if (status === '위험') return 'status-dot alert'
  if (status === '주의') return 'status-dot caution'
  if (status === '제어') return 'status-dot control'
  return 'status-dot normal'
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

function ArrowDownIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 6v12m0 0l-4-4m4 4l4-4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function ArrowUpIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 18V6m0 0l-4 4m4-4l4 4" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

function ResetIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M4 12a8 8 0 1 0 2.34-5.66L4 8.67M4 4v4.67h4.67"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  )
}

type HmiProps = {
  controls: Record<VariableKey, VariableConfig>
  nox: number
  exhaust: number
  lambda: number
  power: number
}

function HmiMonitor(_: HmiProps) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0',
        overflow: 'hidden',
        background:
          'radial-gradient(circle at top, rgba(59,130,246,0.08), transparent 28%), linear-gradient(180deg, #0b1118 0%, #081018 100%)',
      }}
    >
      <img
        src={hmiConceptC}
        alt="컨셉 보드 C안 기반 공정 모니터링 도면"
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          objectFit: 'fill',
        }}
      />
    </div>
  )
}
