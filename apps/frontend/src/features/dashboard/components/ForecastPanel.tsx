import type { Mode, RealtimeStreamPayload } from '../mockConsole'

type Forecast = NonNullable<RealtimeStreamPayload['forecast']>

interface ForecastPanelProps {
  mode: Mode
  forecast: Forecast | null
}

export function ForecastPanel({ mode, forecast }: ForecastPanelProps) {
  if (mode !== 'realtime') return null
  if (forecast === null) {
    return (
      <div className="forecast-panel">
        <div className="forecast-title">5분 후 NOx 예측</div>
        <div className="forecast-empty">예측 모델 준비 중...</div>
      </div>
    )
  }

  const targetKst = new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(forecast.target_time))

  return (
    <div className={forecast.threshold_exceeded ? 'forecast-panel warning' : 'forecast-panel'}>
      <div className="forecast-title">5분 후 NOx 예측</div>
      <div className="forecast-value">{forecast.predicted_nox.toFixed(2)} ppm</div>
      {forecast.threshold_exceeded && (
        <div className="forecast-warning">
          ⚠ 임계 초과 (threshold {forecast.threshold_value.toFixed(1)} ppm)
        </div>
      )}
      <div className="forecast-target">target: {targetKst} (KST)</div>
    </div>
  )
}
