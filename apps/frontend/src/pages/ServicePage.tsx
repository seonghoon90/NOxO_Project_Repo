import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  NOX_LIMIT,
  POWER_RAW_NAME,
  type MetricPoint,
  type VariableConfigUpdate,
  type VariableKey,
  variableSeed,
} from '../features/dashboard/mockConsole'
import { useConsoleState, type StreamStatus } from '../features/dashboard/useConsoleState'
import type { AppOutletContext } from '../app/App'

const variableOrder: VariableKey[] = ['syngas', 'n2', 'load']
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
  const controlCards = variableOrder.map((key) => state.variables[key])
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
                sg={state.variables.syngas.value}
                n2={state.variables.n2.value}
                igv={state.variables.load.value}
                nox={displayedNox}
                co={state.metrics.co}
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
              {variableOrder.map((key) => (
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
                  {variableOrder.map((key) => (
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

// ── NOxO 디자인 토큰 ──────────────────────────────────────
const C = {
  bg:      '#0b0f14',
  surf:    '#11161d',
  surf2:   '#161d26',
  surf3:   '#1c242f',
  line:    'rgba(255,255,255,0.10)',
  lineS:   'rgba(255,255,255,0.18)',
  t2:      'rgba(255,255,255,0.58)',
  t3:      'rgba(255,255,255,0.28)',
  blue:    '#3b82f6',
  blueBg:  'rgba(59,130,246,0.09)',
  green:   '#10b981',
  greenBg: 'rgba(16,185,129,0.08)',
  amber:   '#f59e0b',
  red:     '#ef4444',
} as const

type HmiProps = {
  sg: number; n2: number; igv: number
  nox: number; co: number; exhaust: number; lambda: number; power: number
}

function HmiMonitor({ sg, n2, igv, nox, co, exhaust, lambda, power }: HmiProps) {
  const eff      = Math.min(99, Math.max(60, (89 * power) / 248.6)).toFixed(1)
  const noxColor = nox > 50 ? C.red : C.blue
  const M = "'JetBrains Mono',monospace"

  return (
    <svg
      viewBox="0 0 1456 640"
      width="100%" height="100%"
      style={{ display: 'block', background: C.bg }}
      preserveAspectRatio="xMidYMid meet"
    >
      <defs>
        <linearGradient id="hPink"  x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#f472b6"/>
          <stop offset="40%"  stopColor="#ec4899"/>
          <stop offset="100%" stopColor="#9d174d"/>
        </linearGradient>
        <linearGradient id="hOlive" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#a3e635"/>
          <stop offset="40%"  stopColor="#84cc16"/>
          <stop offset="100%" stopColor="#3f6212"/>
        </linearGradient>
        <linearGradient id="hAmber" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#fbbf24"/>
          <stop offset="40%"  stopColor="#f59e0b"/>
          <stop offset="100%" stopColor="#78350f"/>
        </linearGradient>
        <linearGradient id="hBlue"  x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stopColor="#60a5fa"/>
          <stop offset="50%"  stopColor="#3b82f6"/>
          <stop offset="100%" stopColor="#1d4ed8"/>
        </linearGradient>
        <linearGradient id="hTurb"  x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#1e293b"/>
          <stop offset="60%"  stopColor="#0f172a"/>
          <stop offset="100%" stopColor="#0a1120"/>
        </linearGradient>
        <radialGradient id="hCan" cx="35%" cy="35%">
          <stop offset="0%"   stopColor="#fbbf24"/>
          <stop offset="45%"  stopColor="#ef4444"/>
          <stop offset="100%" stopColor="#7f1d1d"/>
        </radialGradient>
      </defs>

      <rect width="1456" height="640" fill={C.bg}/>

      {/* LEFT PANELS */}
      <rect x="14" y="8" width="126" height="100" fill={C.surf2} stroke={C.line} strokeWidth="1" rx="4"/>
      <text x="77" y="23" fontSize="9" fontWeight="600" textAnchor="middle" fill={C.t3} letterSpacing="0.08em">PURGE TIMER</text>
      <rect x="20" y="28" width="114" height="18" rx="3" fill={C.bg} stroke={C.line}/>
      <text x="77" y="41" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily={M}>26373.0</text>
      <text x="77" y="58" fontSize="9" fontWeight="600" textAnchor="middle" fill={C.t3} letterSpacing="0.06em">RE PURGE</text>
      <rect x="20" y="62" width="114" height="18" rx="3" fill={C.bg} stroke={C.line}/>
      <text x="77" y="75" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily={M}>11.3</text>

      <rect x="155" y="8" width="122" height="98" fill={C.surf2} stroke={C.lineS} strokeWidth="1" rx="4"/>
      <text x="216" y="22" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.1em">SYNGAS</text>
      <circle cx="168" cy="34" r="5" fill={C.green} opacity=".7"/>
      <circle cx="168" cy="50" r="5" fill={C.green} opacity=".7"/>
      <circle cx="168" cy="66" r="5" fill={C.amber} opacity=".6"/>
      <text x="216" y="38" fontSize="11" fontWeight="700" fill={C.blue} fontFamily={M}>{sg.toFixed(1)}</text>
      <text x="249" y="38" fontSize="8" fill={C.t3}>raw</text>
      <text x="216" y="54" fontSize="10" fontWeight="600" fill={C.t2}>184.4</text>
      <text x="249" y="54" fontSize="8" fill={C.t3}>°C</text>
      <text x="216" y="70" fontSize="10" fontWeight="600" fill={C.t2}>44.7</text>
      <text x="249" y="70" fontSize="8" fill={C.t3}>kg/s</text>
      <text x="216" y="84" fontSize="8" fill={C.t3}>9086.5 kg/m³</text>
      <text x="216" y="98" fontSize="8" fontWeight="600" fill={C.green}>GC Normal</text>

      <rect x="155" y="185" width="122" height="72" fill={C.surf2} stroke={C.line} strokeWidth="1" rx="4"/>
      <text x="216" y="199" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.08em">N2 INJECT</text>
      <text x="216" y="215" fontSize="11" fontWeight="700" fill={C.blue} fontFamily={M}>{n2.toFixed(1)}</text>
      <text x="262" y="215" fontSize="8" fill={C.t3}>raw</text>
      <text x="216" y="230" fontSize="10" fontWeight="600" fill={C.t2}>36.0</text>
      <text x="249" y="230" fontSize="8" fill={C.t3}>°C</text>
      <text x="216" y="245" fontSize="10" fontWeight="600" fill={C.t2}>0.3</text>
      <text x="244" y="245" fontSize="8" fill={C.t3}>kg/s</text>

      <rect x="14" y="190" width="134" height="118" fill={C.surf2} stroke={C.line} strokeWidth="1" rx="4"/>
      <text x="81" y="204" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.08em">FUEL SPLIT</text>
      {([ ['FSR','69.0','%'],['N2 FSR','0.0','%'],['SG FSR','69.0','%'],
           ['FX1','100.0','%'],['SIM','128.4','s'],['Eff',eff,'%'] ] as [string,string,string][])
        .map(([label, val, unit], i) => (
        <g key={label}>
          <text x="22" y={218+i*15} fontSize="8" fill={C.t3}>{label}</text>
          <text x="82" y={218+i*15} fontSize="10" fontWeight="600"
            fill={label==='Eff'?C.green:C.blue} fontFamily={M}>{val}</text>
          <text x="112" y={218+i*15} fontSize="8" fill={C.t3}>{unit}</text>
        </g>
      ))}

      {/* SYNGAS 메인 배관 */}
      <rect x="273" y="102" width="440" height="12" fill="url(#hPink)" rx="2"/>
      <rect x="273" y="103" width="440" height="4" fill="#f9a8d4" opacity=".25"/>
      <g transform="translate(305,98)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <line x1="10" y1="0" x2="10" y2="-7" stroke="#064e3b" strokeWidth="1.5"/>
        <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5"/>
        <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.t3}>VS4-11</text>
      </g>
      <g transform="translate(380,98)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <line x1="10" y1="0" x2="10" y2="-7" stroke="#064e3b" strokeWidth="1.5"/>
        <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5"/>
        <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.t3}>VSR-11</text>
      </g>
      <circle cx="470" cy="108" r="8" fill={C.surf3} stroke={C.lineS} strokeWidth="1"/>
      <rect x="446" y="78" width="82" height="22" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="487" y="88" fontSize="7" fontWeight="700" textAnchor="middle" fill={C.t3}>FPSG2</text>
      <text x="487" y="97" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>27.0 kg/cm²</text>
      <line x1="487" y1="100" x2="470" y2="108" stroke={C.line} strokeWidth="1"/>
      <g transform="translate(548,98)">
        <polygon points="0,0 20,10 0,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <text x="10" y="-3" fontSize="7" textAnchor="middle" fill={C.t3}>VGC-11A</text>
      </g>
      <rect x="526" y="124" width="72" height="24" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="562" y="134" fontSize="7" textAnchor="middle" fill={C.t3}>DM 45.9 %</text>
      <text x="562" y="144" fontSize="7" textAnchor="middle" fill={C.t3}>FB 45.9 %</text>
      <rect x="600" y="55" width="12" height="60" fill="url(#hPink)"/>
      <rect x="600" y="55" width="220" height="12" fill="url(#hPink)"/>
      <rect x="808" y="55" width="12" height="60" fill="url(#hPink)"/>
      <rect x="713" y="102" width="107" height="12" fill="url(#hPink)"/>
      <g transform="translate(596,60) rotate(90)">
        <polygon points="0,0 16,8 0,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <polygon points="16,0 0,8 16,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
      </g>
      <rect x="556" y="35" width="70" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="591" y="45" fontSize="7" textAnchor="middle" fill={C.t3}>VGC-11</text>
      <text x="591" y="53" fontSize="7" textAnchor="middle" fill={C.blue} fontFamily={M}>DM 76.0%</text>
      <g transform="translate(804,60) rotate(90)">
        <polygon points="0,0 16,8 0,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <polygon points="16,0 0,8 16,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
      </g>
      <rect x="812" y="35" width="58" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="841" y="45" fontSize="7" textAnchor="middle" fill={C.t3}>VGC-12</text>
      <circle cx="760" cy="108" r="8" fill={C.surf3} stroke={C.lineS} strokeWidth="1"/>
      <rect x="730" y="122" width="80" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="770" y="131" fontSize="7" textAnchor="middle" fill={C.t3}>FPG 3</text>
      <text x="770" y="139" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>15.7 kg/cm²</text>
      <circle cx="870" cy="108" r="9" fill={C.surf3} stroke={C.lineS} strokeWidth="1"/>
      <text x="870" y="112" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>10</text>

      {/* N2 배관 */}
      <rect x="273" y="222" width="440" height="12" fill="url(#hOlive)" rx="2"/>
      <rect x="273" y="223" width="440" height="4" fill="#bef264" opacity=".2"/>
      <g transform="translate(305,218)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <line x1="10" y1="0" x2="10" y2="-7" stroke="#064e3b" strokeWidth="1.5"/>
        <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5"/>
        <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.t3}>VS4-1</text>
      </g>
      <g transform="translate(380,218)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <line x1="10" y1="0" x2="10" y2="-7" stroke="#064e3b" strokeWidth="1.5"/>
        <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5"/>
        <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.t3}>VSR-1</text>
      </g>
      <circle cx="466" cy="228" r="8" fill={C.surf3} stroke={C.lineS} strokeWidth="1"/>
      <rect x="440" y="242" width="68" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="474" y="251" fontSize="7" textAnchor="middle" fill={C.t3}>FPG2</text>
      <text x="474" y="259" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>0.0 kg/cm²</text>
      <g transform="translate(516,218)">
        <polygon points="0,0 20,10 0,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2"/>
        <text x="10" y="-3" fontSize="7" textAnchor="middle" fill={C.t3}>VGC-1</text>
      </g>
      <rect x="500" y="242" width="72" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="536" y="251" fontSize="7" textAnchor="middle" fill={C.t3}>DM -25.0%</text>
      <text x="536" y="259" fontSize="7" textAnchor="middle" fill={C.t3}>FB  0.1%</text>

      {/* 인렛 덕트 + IGV */}
      <rect x="580" y="200" width="78" height="180" fill={C.surf3} stroke={C.line} strokeWidth="1" rx="2"/>
      {([
        [230,12,'INLET','53.0 mmH₂O'],
        [260,13,null,'30.1 °C'],
        [290,14,null,'755.2 mmHg'],
      ] as [number,number,string|null,string][]).map(([cy,n,label,val])=>(
        <g key={n}>
          <circle cx="600" cy={cy} r="9" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
          <text x="600" y={cy+4} fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>{n}</text>
          {label&&<text x="618" y={cy-6} fontSize="7" fill={C.t3}>{label}</text>}
          <rect x="618" y={cy-2} width="82" height="13" rx="2" fill={C.surf2} stroke={C.line}/>
          <text x="659" y={cy+8} fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>{val}</text>
        </g>
      ))}
      <circle cx="630" cy="362" r="9" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
      <text x="630" y="366" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>15</text>
      <rect x="590" y="375" width="106" height="40" rx="3" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
      <text x="643" y="387" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.08em">IGV</text>
      <text x="643" y="400" fontSize="9" textAnchor="middle" fill={C.blue} fontFamily={M}>DM {igv.toFixed(1)} %</text>
      <text x="643" y="412" fontSize="9" textAnchor="middle" fill={C.blue} fontFamily={M}>FB {igv.toFixed(1)} %</text>

      {/* 가스 터빈 본체 */}
      <polygon points="660,145 1120,170 1120,500 660,520" fill="url(#hTurb)" stroke={C.lineS} strokeWidth="2"/>
      <ellipse cx="660" cy="332" rx="22" ry="188" fill="#1e293b" stroke={C.lineS} strokeWidth="2"/>
      <ellipse cx="660" cy="332" rx="16" ry="140" fill="#1a2332" stroke={C.line} strokeWidth="1.5"/>
      <ellipse cx="660" cy="332" rx="10" ry="90"  fill="#162030" stroke={C.line} strokeWidth="1"/>
      <ellipse cx="660" cy="332" rx="5"  ry="44"  fill="#1c2a3a" stroke={C.line} strokeWidth="1"/>
      {[740,820,910,1010].map(x=>(
        <line key={x} x1={x} y1="151" x2={x} y2="513"
          stroke={C.lineS} strokeWidth="1" strokeDasharray="5,4" opacity=".5"/>
      ))}
      {([[700,175],[770,155],[860,132],[960,108],[1060,85]] as [number,number][]).map(([cx,ry],i)=>(
        <ellipse key={i} cx={cx} cy="332" rx={14-i*1.2} ry={ry}
          fill="#162030" stroke={C.lineS} strokeWidth="1" opacity={0.7-i*0.06}/>
      ))}
      <rect x="660" y="322" width="460" height="20" rx="4" fill="#1a2332" stroke={C.lineS} strokeWidth="1.5"/>
      <rect x="660" y="326" width="460" height="12" rx="3" fill="#1e2d42"/>
      {([[740,175,'A'],[740,246,'B'],[740,418,'C'],[740,488,'D']] as [number,number,string][]).map(([cx,cy,l])=>(
        <g key={l}>
          <ellipse cx={cx} cy={cy} rx="38" ry="24" fill="url(#hCan)" stroke="#7f1d1d" strokeWidth="1.5"/>
          <text x={cx} y={cy+5} fontSize="12" fontWeight="700" textAnchor="middle" fill="#fff" opacity=".9">{l}</text>
          <rect x={cx-16} y={cy} width="30" height="18" fill="#7f1d1d" stroke="#6b1515" strokeWidth="1"/>
        </g>
      ))}
      <circle cx="870" cy="195" r="9" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
      <text x="870" y="199" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>16</text>
      <rect x="840" y="170" width="80" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="880" y="179" fontSize="7" textAnchor="middle" fill={C.t3}>CPD</text>
      <text x="880" y="188" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>13.1 kg/cm²</text>
      <circle cx="920" cy="380" r="9" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
      <text x="920" y="384" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>17</text>
      <rect x="930" y="370" width="74" height="20" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="967" y="379" fontSize="7" textAnchor="middle" fill={C.t3}>CTD</text>
      <text x="967" y="388" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.amber} fontFamily={M}>391.5 °C</text>
      <rect x="800" y="530" width="104" height="24" rx="4" fill={C.blueBg} stroke="rgba(59,130,246,0.35)" strokeWidth="1"/>
      <text x="852" y="546" fontSize="13" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily={M}>λ = {lambda.toFixed(2)}</text>

      {/* CBV */}
      {([[185,'CBV#1 CLSD'],[207,'CBV#3 CLSD'],[445,'CBV#4 CLSD'],[467,'CBV#2 CLSD']] as [number,string][]).map(([y,l])=>(
        <g key={l}>
          <rect x="1126" y={y} width="78" height="16" rx="3" fill={C.greenBg} stroke="rgba(16,185,129,0.3)" strokeWidth="1"/>
          <text x="1165" y={y+11} fontSize="8" textAnchor="middle" fill={C.green} fontFamily={M}>{l}</text>
        </g>
      ))}

      {/* 오른쪽 수치 패널 */}
      <rect x="1214" y="8" width="230" height="490" fill={C.surf2} stroke={C.line} strokeWidth="1" rx="4"/>
      <text x="1329" y="24" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.1em">PROCESS DATA</text>
      <line x1="1216" y1="30" x2="1440" y2="30" stroke={C.line} strokeWidth="1"/>
      {([
        ['IGV',    igv.toFixed(1),     '°',    C.blue],
        ['NOx',    nox.toFixed(1),     'ppm',  noxColor],
        ['CO',     co.toFixed(1),      'ppm',  C.blue],
        ['Exh.',   exhaust.toFixed(1), '°C',   C.amber],
        ['λ',      lambda.toFixed(2),  '',     C.blue],
        ['Eff.',   eff,                '%',    C.green],
        ['Power',  power.toFixed(1),   'MW',   C.blue],
        ['SYNGAS', sg.toFixed(1),      'raw',  C.blue],
        ['N2',     n2.toFixed(1),      'raw',  C.blue],
        ['Speed',  '100.0',            '%',    C.blue],
        ['RPM',    '3600',             'rpm',  C.blue],
        ['Vib',    '6.7',              'mm/s', C.amber],
      ] as [string,string,string,string][]).map(([label,val,unit,clr],i)=>(
        <g key={label}>
          <text x="1222" y={48+i*36} fontSize="8" fill={C.t3}>{label}</text>
          <text x="1222" y={64+i*36} fontSize="14" fontWeight="700" fill={clr} fontFamily={M}>{val}</text>
          {unit&&<text x={1222+val.length*8+4} y={64+i*36} fontSize="9" fill={C.t3}>{unit}</text>}
          <line x1="1216" y1={72+i*36} x2="1440" y2={72+i*36} stroke={C.line} strokeWidth="1"/>
        </g>
      ))}

      {/* NPNJ2 */}
      <rect x="1050" y="80" width="66" height="22" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="1083" y="90" fontSize="7" textAnchor="middle" fill={C.t3}>NPNJ2</text>
      <text x="1083" y="99" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily={M}>16.0 kg/cm²</text>
      <rect x="1083" y="102" width="8" height="88" fill="url(#hBlue)" rx="2"/>
      <g transform="translate(1078,128)">
        <polygon points="0,0 16,8 0,16" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="16,0 0,8 16,16" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <text x="8" y="-3" fontSize="7" textAnchor="middle" fill={C.t3}>VS7-1</text>
      </g>

      {/* N2 하단 배관 */}
      <rect x="155" y="558" width="122" height="66" fill={C.surf2} stroke={C.line} strokeWidth="1" rx="4"/>
      <text x="216" y="572" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.t3} letterSpacing="0.08em">N2 DILUT</text>
      <text x="216" y="588" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily={M}>{n2.toFixed(1)}</text>
      <text x="216" y="602" fontSize="8" textAnchor="middle" fill={C.t3}>32.4 °C</text>
      <text x="216" y="614" fontSize="8" textAnchor="middle" fill={C.t3}>0.3 kg/s</text>
      <rect x="273" y="575" width="520" height="12" fill="url(#hAmber)" rx="2"/>
      <rect x="273" y="576" width="520" height="4" fill="#fde68a" opacity=".2"/>
      <g transform="translate(440,571)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <text x="10" y="-3" fontSize="8" textAnchor="middle" fill={C.t3}>VS3-1</text>
      </g>
      <g transform="translate(620,571)">
        <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2"/>
        <text x="10" y="-3" fontSize="8" textAnchor="middle" fill={C.t3}>VA4-1</text>
      </g>
      <rect x="710" y="450" width="12" height="137" fill="url(#hAmber)" rx="2"/>
      <circle cx="716" cy="468" r="9" fill={C.surf2} stroke={C.lineS} strokeWidth="1"/>
      <text x="716" y="472" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.t2}>18</text>
      <rect x="680" y="478" width="106" height="28" rx="3" fill={C.surf2} stroke={C.line}/>
      <text x="733" y="490" fontSize="7" textAnchor="middle" fill={C.t3}>IBH  DM -25.0%</text>
      <text x="733" y="500" fontSize="7" textAnchor="middle" fill={C.t3}>FB  0.2%</text>
    </svg>
  )
}
