import { useCallback, useEffect, useState, type ChangeEvent } from 'react'
import { useOutletContext } from 'react-router-dom'
import { HmiSchematic } from '../features/dashboard/HmiSchematic/HmiSchematic'
import {
  CONTROL_VARIABLE_KEYS,
  type ConsoleMetrics,
  type MetricPoint,
  type RealtimeStreamPayload,
  type VariableConfigUpdate,
  type VariableKey,
  variableSeed,
} from '../features/dashboard/mockConsole'
import { useConsoleState, type StreamStatus } from '../features/dashboard/useConsoleState'
import { useThresholds, type Thresholds } from '../features/dashboard/useThresholds'
import type { AppOutletContext } from '../app/App'

const controlVariableOrder: VariableKey[] = CONTROL_VARIABLE_KEYS
// 정격값(rated) — `digital_twin/simulation/config.py`의 InitialOutput / FeatureConfig 기준.
// 운영 임계(caution/danger)는 useThresholds로 백엔드에서 받아온다.
const NOX_RATED = 20
const EXHAUST_RATED = 580
const LAMBDA_RATED = 1.1
const EFFICIENCY_RATED = 0.89

export function ServicePage() {
  const { mode, settingsOpen, closeSettings, reportStreamStatus } = useOutletContext<AppOutletContext>()
  const {
    state,
    status,
    setActiveVar,
    stepActiveVar,
    resetControls,
    resetOverride,
    setMode: notifyBackendMode,
    updateActiveVariableConfig,
    restoreActiveVariableDefaults,
  } = useConsoleState(mode)
  const thresholds = useThresholds()
  const [draftConfig, setDraftConfig] = useState<VariableConfigUpdate | null>(null)
  // realtime 모드는 Kafka 기반 5분 NOx 예측 표시 — 제어 조작은 잠근다.
  const isRealtimeMode = mode === 'realtime'

  const activeVariable = state.variables[state.activeVar]
  const resolvedDraftConfig = draftConfig ?? {
    min: activeVariable.min,
    max: activeVariable.max,
    step: activeVariable.step,
  }
  const displayedNox = mode === 'sim' ? state.metrics.nox : state.metrics.predictedNox
  const streamLabel = streamStatusLabel(status)
  const noxStatus = displayedNox > thresholds.noxLimit ? '위험' : streamLabel.text
  const controlCards = controlVariableOrder.map((key) => state.variables[key])
  const noxValues = state.history.length > 0 ? state.history.map((point) => point.nox) : [displayedNox]
  // 효율은 정격 이상이면 항상 정상. 미만일 때만 caution/danger 임계로 색 판정.
  const efficiency = state.metrics.efficiency
  const noxHeadroom = thresholds.noxLimit - displayedNox
  const noxHeadroomTone = headroomTone(noxHeadroom, 12, 5)
  const efficiencyHeadroomTone = efficiencyTone(efficiency, thresholds)
  const noxRange = getRange(noxValues)
  const tableRows = buildOutputTableRows({
    displayedNox,
    metrics: state.metrics,
    history: state.history,
    thresholds,
  })
  const handleCloseSettings = useCallback(() => {
    setDraftConfig(null)
    closeSettings()
  }, [closeSettings])

  useEffect(() => {
    reportStreamStatus(status)
  }, [reportStreamStatus, status])

  // App.tsx의 mode 토글이 변경되면 backend에 알린다 — 첫 마운트 sim 호출은 idempotent.
  useEffect(() => {
    notifyBackendMode(mode)
  }, [mode, notifyBackendMode])

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
              status={noxStatus}
              emphatic
            />
            <KpiCard
              title="배기온도 (TTXM)"
              value={state.metrics.exhaust}
              unit="°C"
              status={exhaustStatus(state.metrics.exhaust, thresholds)}
              digits={1}
              emphatic
            />
            <KpiCard
              title="발전 효율"
              value={efficiency * 100}
              unit="%"
              status={efficiencyKpiStatus(efficiency, thresholds)}
              digits={1}
              emphatic
            />
            <KpiCard
              title="공기비 (λ)"
              value={state.metrics.lambda}
              unit=""
              status={lambdaStatus(state.metrics.lambda, thresholds)}
              digits={2}
              emphatic
            />
          </div>

          <div className="kpi-row kpi-row-secondary">
            {controlCards.map((variable) => (
              <KpiCardMini
                key={variable.key}
                title={variable.label}
                value={variable.value}
                unit={variable.unit}
                digits={variable.digits}
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
              <HmiSchematic
                {...state.variables}
                nox={displayedNox}
                ttxm={state.metrics.exhaust}
                lambda={state.metrics.lambda}
                power={state.metrics.power}
                history={state.history}
              />
            </div>
          </section>

          <div className="chart-row">
            <section className="panel chart-card">
              <header className="chart-header">
                <div>
                  <div className="chart-title">NOx 시계열</div>
                  <div className="chart-subtitle">ppm · 최근 60s</div>
                </div>
                <span className={`stream-badge ${streamLabel.tone}`}>{streamLabel.text}</span>
              </header>
              <div className="chart-body">
                <NoxChart history={state.history} current={displayedNox} noxLimit={thresholds.noxLimit} />
              </div>
            </section>

            <section className="panel chart-card">
              <header className="chart-header">
                <div>
                  <div className="chart-title">배기온도 / 공기비 (λ)</div>
                  <div className="chart-subtitle">정규화 · 최근 60s</div>
                </div>
                <div className="chart-legend mono">
                  <span className="legend-exhaust">배기온도</span>
                  <span className="legend-lambda">공기비</span>
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
                  <th>기준치</th>
                  <th>편차</th>
                  <th>최근 60s 변동폭</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                {tableRows.map((row) => (
                  <tr key={row.name}>
                    <td className="label-cell">{row.name}</td>
                    <td>
                      {row.currentText}
                      <span className="cell-unit">{row.unit}</span>
                    </td>
                    <td className="muted-cell">
                      {row.ratedText}
                      <span className="cell-unit">{row.unit}</span>
                    </td>
                    <td className={`deviation-cell ${row.deviationTone}`}>{row.deviationText}</td>
                    <td className="muted-cell">{row.rangeText}</td>
                    <td>
                      <span className={statusClass(row.status)}>{row.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>

        <aside className="sidebar">
          {isRealtimeMode ? (
            <ForecastCard
              forecast={state.forecast}
              noxLimit={thresholds.noxLimit}
            />
          ) : (
            <>
              <div className="sidebar-section">
                <div className="sidebar-title">제어 변수 선택</div>
                <select
                  className="control-select mono"
                  value={state.activeVar}
                  onChange={(event) => setActiveVar(event.target.value as VariableKey)}
                >
                  {controlVariableOrder.map((key) => (
                    <option key={key} value={key}>
                      {state.variables[key].label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="sidebar-section">
                <div className="sidebar-title">조작 패널</div>
                <div className="control-box">
                  <div className="control-label">현재 조작 중:</div>
                  <div className="control-name">{activeVariable.label}</div>
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
                  <button
                    type="button"
                    className="icon-button"
                    onClick={() => {
                      resetOverride()
                      resetControls()
                    }}
                    aria-label="초기화"
                  >
                    <ResetIcon />
                  </button>
                </div>
              </div>
            </>
          )}

          <div className="sidebar-section telemetry">
            <div className="sidebar-title">운영 요약</div>
            <div className="summary-highlight">
              <div className="summary-label">NOx 임계 여유</div>
              <div className={`summary-value ${noxHeadroomTone}`}>
                {formatHeadroom(noxHeadroom, 1)}
                <span className="summary-unit">ppm</span>
              </div>
            </div>
            <div className="summary-highlight">
              <div className="summary-label">발전 효율 임계 여유</div>
              <div className={`summary-value ${efficiencyHeadroomTone}`}>
                {formatEfficiencyHeadroom(efficiency, thresholds)}
                <span className="summary-unit">%p</span>
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
                label="현재 발전 효율"
                minLabel="현재"
                minValue={(efficiency * 100).toFixed(1)}
                maxLabel="정격"
                maxValue={(EFFICIENCY_RATED * 100).toFixed(1)}
                unit="%"
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
                      {state.variables[key].label}
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

function ForecastCard({
  forecast,
  noxLimit,
}: {
  forecast: RealtimeStreamPayload['forecast']
  noxLimit: number
}) {
  if (forecast === null) {
    return (
      <section className="kpi-card kpi-card-primary forecast-card">
        <div className="kpi-header">
          <div className="kpi-name">5분 후 NOx 예측</div>
          <span className="status-pill status-normal">대기</span>
        </div>
        <div className="kpi-value-row">
          <div className="kpi-value">--</div>
          <div className="kpi-subtitle">예측 모델 준비 중...</div>
        </div>
      </section>
    )
  }

  const exceeded = forecast.threshold_exceeded
  const [integer, decimal = '0'] = forecast.predicted_nox.toFixed(1).split('.')
  const targetKst = new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(forecast.target_time))

  return (
    <section
      className={
        exceeded
          ? 'kpi-card kpi-card-primary caution-border forecast-card'
          : 'kpi-card kpi-card-primary forecast-card'
      }
    >
      <div className="kpi-header">
        <div className="kpi-name">5분 후 NOx 예측</div>
        <span className={exceeded ? 'status-pill status-danger' : 'status-pill status-normal'}>
          {exceeded ? '위험' : '정상'}
        </span>
      </div>
      <div className="kpi-value-row">
        <div className={exceeded ? 'kpi-value kpi-value-large caution-text' : 'kpi-value kpi-value-large'}>
          {integer}
          <span className="kpi-decimal">.{decimal}</span>
        </div>
        <div className="kpi-subtitle">ppm</div>
      </div>
      {exceeded ? (
        <div className="forecast-warning mono">
          ⚠ 임계 초과 (허용 {noxLimit.toFixed(1)} ppm)
        </div>
      ) : (
        <div className="forecast-headroom mono">
          여유 {(noxLimit - forecast.predicted_nox).toFixed(1)} ppm
        </div>
      )}
      <div className="forecast-target mono">target: {targetKst} (KST)</div>
    </section>
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
  status,
  emphatic,
  caution,
  digits = 1,
}: {
  title: string
  value: number
  unit?: string
  status: string
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
      </div>
    </section>
  )
}

function KpiCardMini({
  title,
  value,
  unit,
  digits = 1,
}: {
  title: string
  value: number
  unit: string
  digits?: number
}) {
  const [integer, decimal = '0'] = value.toFixed(digits).split('.')

  return (
    <section className="kpi-card kpi-card-mini">
      <div className="kpi-mini-header">
        <div className="kpi-mini-name">{title}</div>
        <span className={statusClass('제어')}>제어</span>
      </div>
      <div className="kpi-mini-value-row">
        <div className="kpi-mini-value">
          {integer}
          <span className="kpi-mini-decimal">.{decimal}</span>
        </div>
        <div className="kpi-mini-unit">{unit}</div>
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

function NoxChart({
  history,
  current,
  noxLimit,
}: {
  history: MetricPoint[]
  current: number
  noxLimit: number
}) {
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
  const thresholdInRange = noxLimit <= max
  const line = buildLinePath(values, min, max, width, height)
  const area = `${line} L ${width} ${height} L 0 ${height} Z`
  const thresholdY = thresholdInRange ? scaleY(noxLimit, min, max, height) : thresholdPinnedY
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
        {noxLimit} ppm
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
  const lambdaValues = history.map((point) => point.lambda)
  const exhaustValues = history.map((point) => point.exhaust)
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
      <text x="2" y="12" className="svg-label" fill="#3B82F6">
        λ {lambdaRange.max.toFixed(2)}
      </text>
      <text x="6" y={bottomLabelY} className="svg-label" fill="#3B82F6">
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

// 임계 여유 표기: 정상은 부호 없이 조용하게, 임계 초과(음수)만 "초과 N"으로 강조.
function formatHeadroom(value: number, digits: number) {
  if (value < 0) return `초과 ${Math.abs(value).toFixed(digits)}`
  return value.toFixed(digits)
}

type OutputTableRow = {
  name: string
  unit: string
  currentText: string
  ratedText: string
  deviationText: string
  deviationTone: string
  rangeText: string
  status: string
}

// 동적 출력값 4종 — 정격값은 DT InitialOutput/FeatureConfig SoT, 임계는 백엔드 thresholds.
// CO는 학습 타겟에서 제외됐고 백엔드 WS도 보내지 않아 표에서 제외, MultiChart 합성식만 유지.
function buildOutputTableRows(args: {
  displayedNox: number
  metrics: ConsoleMetrics
  history: MetricPoint[]
  thresholds: Thresholds
}): OutputTableRow[] {
  const { displayedNox, metrics, history, thresholds } = args
  const noxRange = history.length > 0
    ? getRange(history.map((p) => p.nox))
    : { min: displayedNox, max: displayedNox }
  const exhaustRange = history.length > 0
    ? getRange(history.map((p) => p.exhaust))
    : { min: metrics.exhaust, max: metrics.exhaust }
  const lambdaRange = history.length > 0
    ? getRange(history.map((p) => p.lambda))
    : { min: metrics.lambda, max: metrics.lambda }
  const efficiencyRangePct = history.length > 0
    ? getRange(history.map((p) => p.efficiency * 100))
    : { min: metrics.efficiency * 100, max: metrics.efficiency * 100 }

  return [
    {
      name: 'NOx',
      unit: 'ppm',
      currentText: displayedNox.toFixed(1),
      ratedText: NOX_RATED.toFixed(1),
      ...formatDeviation(displayedNox - NOX_RATED, 1, 5, 10),
      rangeText: `${noxRange.min.toFixed(1)} ~ ${noxRange.max.toFixed(1)}`,
      status: displayedNox > thresholds.noxLimit ? '위험' : '정상',
    },
    {
      name: '배기온도 (TTXM)',
      unit: '°C',
      currentText: metrics.exhaust.toFixed(1),
      ratedText: EXHAUST_RATED.toFixed(1),
      ...formatDeviation(metrics.exhaust - EXHAUST_RATED, 1, 15, 30),
      rangeText: `${exhaustRange.min.toFixed(1)} ~ ${exhaustRange.max.toFixed(1)}`,
      status: exhaustStatus(metrics.exhaust, thresholds),
    },
    {
      name: '발전 효율 (η)',
      unit: '%',
      currentText: (metrics.efficiency * 100).toFixed(1),
      ratedText: (EFFICIENCY_RATED * 100).toFixed(1),
      ...formatDeviation((metrics.efficiency - EFFICIENCY_RATED) * 100, 1, 2, 5),
      rangeText: `${efficiencyRangePct.min.toFixed(1)} ~ ${efficiencyRangePct.max.toFixed(1)}`,
      status: efficiencyTableStatus(metrics.efficiency, thresholds),
    },
    {
      name: '공기비 (λ)',
      unit: '',
      currentText: metrics.lambda.toFixed(2),
      ratedText: LAMBDA_RATED.toFixed(2),
      ...formatDeviation(metrics.lambda - LAMBDA_RATED, 2, 0.05, 0.1),
      rangeText: `${lambdaRange.min.toFixed(2)} ~ ${lambdaRange.max.toFixed(2)}`,
      status: lambdaStatus(metrics.lambda, thresholds),
    },
  ]
}

function formatDeviation(
  delta: number,
  digits: number,
  cautionAbs: number,
  dangerAbs: number,
): { deviationText: string; deviationTone: string } {
  const abs = Math.abs(delta)
  const sign = delta >= 0 ? '+' : '−'
  const text = `${sign}${abs.toFixed(digits)}`
  const tone =
    abs >= dangerAbs ? 'deviation-danger'
    : abs >= cautionAbs ? 'deviation-caution'
    : 'deviation-normal'
  return { deviationText: text, deviationTone: tone }
}

// 효율은 정격(0.89) 이상이면 항상 정상 — 미만일 때만 caution/danger 임계 사용.
function efficiencyKpiStatus(efficiency: number, t: Thresholds): string {
  if (efficiency < t.efficiencyDanger) return '위험'
  if (efficiency < t.efficiencyCaution) return '주의'
  return '정상'
}

function efficiencyTableStatus(efficiency: number, t: Thresholds): string {
  return efficiencyKpiStatus(efficiency, t)
}

function efficiencyTone(efficiency: number, t: Thresholds): string {
  if (efficiency < t.efficiencyDanger) return 'summary-value-danger'
  if (efficiency < t.efficiencyCaution) return 'summary-value-caution'
  return 'summary-value-safe'
}

function formatEfficiencyHeadroom(efficiency: number, t: Thresholds): string {
  // 정격 이상이면 그냥 "정상 운전" 표시. caution 미만일 때만 부족분(%p) 표시.
  if (efficiency >= t.efficiencyCaution) {
    return ((efficiency - t.efficiencyCaution) * 100).toFixed(1)
  }
  return `부족 ${((t.efficiencyCaution - efficiency) * 100).toFixed(1)}`
}

function exhaustStatus(value: number, t: Thresholds): string {
  if (value >= t.exhaustDangerC) return '위험'
  if (value >= t.exhaustCautionC) return '주의'
  return '정상'
}

function lambdaStatus(value: number, t: Thresholds): string {
  if (value <= t.lambdaDangerLo || value >= t.lambdaDangerHi) return '위험'
  if (value <= t.lambdaCautionLo || value >= t.lambdaCautionHi) return '주의'
  return '정상'
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

