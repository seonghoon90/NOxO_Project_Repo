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

export function ServicePage() {
  const { mode, settingsOpen, closeSettings, reportStreamStatus } = useOutletContext<AppOutletContext>()
  const {
    state,
    status,
    setActiveVar,
    stepActiveVar,
    resetControls,
    toggleOverlay,
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
  const tableRows = [
    ['NOx', displayedNox.toFixed(1), 'ppm', NOX_LIMIT.toFixed(1), '5.0s', displayedNox > NOX_LIMIT ? '위험' : '정상'],
    ['발전량', state.metrics.power.toFixed(1), 'MW', '248.6', '8.5s', state.metrics.power < 240 ? '주의' : '정상'],
    ['CO', state.metrics.co.toFixed(1), 'ppm', '200.0', '1.8s', '정상'],
    ['화염온도', state.metrics.flame.toFixed(1), 'K', '1450.0', '10.0s', state.metrics.flame > 1500 ? '주의' : '정상'],
    ['λ', state.metrics.lambda.toFixed(2), '-', '1.10', '0.9s', '정상'],
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
              <button
                type="button"
                className={state.overlayVisible ? 'overlay-toggle' : 'overlay-toggle off'}
                onClick={toggleOverlay}
              >
                <EyeIcon />
                오버레이 표시
              </button>
            </header>
            <div className="plant-body">
              <div className="plant-frame" />
              <div className="plant-hint mono">도면 이미지 자리 (plant-diagram.svg)</div>
              <PlantDiagram n2Label={state.variables.n2.shortLabel} />
              {state.overlayVisible ? (
                <div className="overlay-layer">
                  <div className="overlay-anchor top-left">
                    <OverlayMetric
                      label={state.variables.syngas.shortLabel}
                      value={`${formatValue(state.variables.syngas.value, state.variables.syngas.digits)} ${state.variables.syngas.unit}`}
                    />
                  </div>
                  <div className="overlay-anchor top-mid">
                    <OverlayMetric label="λ" value={state.metrics.lambda.toFixed(2)} />
                  </div>
                  <div className="overlay-anchor top-right-left">
                    <OverlayMetric label="화염온도" value={`${state.metrics.flame.toFixed(1)} K`} caution />
                  </div>
                  <div className="overlay-anchor top-right">
                    <OverlayMetric label="CO" value={`${state.metrics.co.toFixed(1)} ppm`} />
                  </div>
                  <div className="overlay-anchor right-mid">
                    <OverlayMetric label="NOx" value={`${displayedNox.toFixed(1)} ppm`} primary />
                  </div>
                  <div className="overlay-anchor bottom-left">
                    <OverlayMetric
                      label={state.variables.n2.shortLabel}
                      value={`${formatValue(state.variables.n2.value, state.variables.n2.digits)} ${state.variables.n2.unit}`}
                    />
                  </div>
                  <div className="overlay-anchor bottom-mid-left">
                    <OverlayMetric
                      label={state.variables.load.shortLabel}
                      value={`${formatValue(state.variables.load.value, state.variables.load.digits)} ${state.variables.load.unit}`}
                    />
                  </div>
                  <div className="overlay-anchor bottom-mid-right">
                    <OverlayMetric label="발전량" value={`${state.metrics.power.toFixed(1)} MW`} />
                  </div>
                </div>
              ) : null}
            </div>
          </section>

          <div className="chart-row">
            <section className="panel chart-card nox-glow">
              <header className="chart-header">
                <div>
                  <div className="chart-title">NOx 시계열</div>
                  <div className="chart-subtitle">ppm · 최근 60s</div>
                </div>
                <span className={`status-dot ${streamLabel.tone}`}>{streamLabel.text}</span>
              </header>
              <div className="chart-body">
                <NoxChart history={state.history} current={displayedNox} />
              </div>
            </section>

            <section className="panel chart-card">
              <header className="chart-header">
                <div>
                  <div className="chart-title">CO / λ / 화염온도</div>
                  <div className="chart-subtitle">정규화 · 최근 60s</div>
                </div>
                <div className="chart-legend mono">
                  <span className="legend-co">CO</span>
                  <span className="legend-lambda">λ</span>
                  <span className="legend-flame">화염</span>
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
            <div className="sidebar-title">멀티 변수 패널</div>
            <TelemetryRow
              label={state.variables.syngas.label}
              value={formatValue(state.variables.syngas.value, state.variables.syngas.digits)}
              unit={state.variables.syngas.unit}
            />
            <TelemetryRow
              label={state.variables.n2.label}
              value={formatValue(state.variables.n2.value, state.variables.n2.digits)}
              unit={state.variables.n2.unit}
            />
            <TelemetryRow
              label={state.variables.load.label}
              value={formatValue(state.variables.load.value, state.variables.load.digits)}
              unit={state.variables.load.unit}
            />
            <div className="telemetry-divider" />
            <TelemetryRow label="NOx" value={displayedNox.toFixed(1)} unit="ppm" />
            <TelemetryRow label="발전량" value={state.metrics.power.toFixed(1)} unit="MW" />
            <TelemetryRow label="CO" value={state.metrics.co.toFixed(1)} unit="ppm" />
            <TelemetryRow label="화염온도" value={state.metrics.flame.toFixed(1)} unit="K" caution />
            <TelemetryRow label="λ" value={state.metrics.lambda.toFixed(2)} unit="-" />
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

function TelemetryRow({
  label,
  value,
  unit,
  caution,
}: {
  label: string
  value: number | string
  unit: string
  caution?: boolean
}) {
  return (
    <div className="telemetry-row">
      <span className="telemetry-name">{label}</span>
      <span>
        <span className={caution ? 'telemetry-value caution-text' : 'telemetry-value'}>{value}</span>
        <span className="telemetry-unit">{unit}</span>
      </span>
    </div>
  )
}

function NoxChart({ history, current }: { history: MetricPoint[]; current: number }) {
  const width = 560
  const height = 170
  const bottomLabelY = height - 12
  if (history.length < 2) {
    return <ChartPlaceholder width={width} height={height} />
  }
  const values = history.map((point) => point.nox)
  const max = Math.max(NOX_LIMIT * 1.1, ...values) * 1.03
  const min = Math.min(...values) - 8
  const line = buildLinePath(values, min, max, width, height)
  const area = `${line} L ${width} ${height} L 0 ${height} Z`
  const thresholdY = scaleY(NOX_LIMIT, min, max, height)
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
  const flameValues = history.map((point) => point.flame)
  const coRange = createRange(coValues, 0.12, 0.6)
  const lambdaRange = createRange(lambdaValues, 0.18, 0.02)
  const flameRange = createRange(flameValues, 0.08, 1.2)

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
        d={buildSeriesPath(flameValues, flameRange.min, flameRange.max, padding.left, padding.top, plotWidth, plotHeight)}
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
        {flameRange.max.toFixed(1)} K
      </text>
      <text x={width - 6} y={bottomLabelY} textAnchor="end" className="svg-label" fill="#F59E0B">
        {flameRange.min.toFixed(1)} K
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

function PlantDiagram({ n2Label }: { n2Label: string }) {
  return (
    <svg className="plant-svg" viewBox="0 0 900 330" preserveAspectRatio="xMidYMid meet">
      <rect x="68" y="146" width="110" height="38" rx="7" className="plant-node" />
      <text x="123" y="169" textAnchor="middle" className="plant-text">
        연료 공급
      </text>
      <rect x="248" y="131" width="170" height="68" rx="8" className="plant-node active" />
      <text x="333" y="160" textAnchor="middle" className="plant-text active">
        합성가스
      </text>
      <text x="333" y="178" textAnchor="middle" className="plant-text active">
        반응기
      </text>
      <circle cx="520" cy="165" r="46" className="plant-node" />
      <text x="520" y="162" textAnchor="middle" className="plant-text">
        가스
      </text>
      <text x="520" y="176" textAnchor="middle" className="plant-text">
        터빈
      </text>
      <rect x="652" y="146" width="116" height="38" rx="7" className="plant-node" />
      <text x="710" y="169" textAnchor="middle" className="plant-text">
        배기 라인
      </text>
      <rect x="272" y="276" width="122" height="28" rx="5" className="plant-node secondary" />
      <text x="333" y="293" textAnchor="middle" className="plant-text secondary">
        {n2Label}
      </text>
    </svg>
  )
}

function OverlayMetric({
  label,
  value,
  caution,
  primary,
}: {
  label: string
  value: string
  caution?: boolean
  primary?: boolean
}) {
  const className = primary ? 'overlay-metric primary' : caution ? 'overlay-metric caution' : 'overlay-metric'

  return (
    <div className={className}>
      <div className="overlay-metric-label">{label}</div>
      <div className={caution ? 'overlay-metric-value caution-text' : primary ? 'overlay-metric-value primary-text' : 'overlay-metric-value'}>
        <span className={caution ? 'overlay-metric-dot caution' : primary ? 'overlay-metric-dot primary' : 'overlay-metric-dot'} />
        {value}
      </div>
    </div>
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

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M2.5 12s3.5-6 9.5-6s9.5 6 9.5 6s-3.5 6-9.5 6s-9.5-6-9.5-6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  )
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
