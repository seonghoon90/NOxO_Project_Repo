import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ForecastPanel } from './ForecastPanel'

describe('ForecastPanel', () => {
  it('renders nothing in sim mode', () => {
    const { container } = render(<ForecastPanel mode="sim" forecast={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('shows preparing state when forecast is null in realtime', () => {
    render(<ForecastPanel mode="realtime" forecast={null} />)
    expect(screen.getByText(/예측 모델 준비 중/)).toBeInTheDocument()
  })

  it('shows predicted value and warning when threshold exceeded', () => {
    render(
      <ForecastPanel
        mode="realtime"
        forecast={{
          predicted_nox: 32.5,
          target_time: '2026-05-12T07:35:00.000Z',
          threshold_value: 30.0,
          threshold_exceeded: true,
        }}
      />,
    )
    expect(screen.getByText(/32\.50 ppm/)).toBeInTheDocument()
    expect(screen.getByText(/임계 초과/)).toBeInTheDocument()
  })

  it('does not show warning when within threshold', () => {
    render(
      <ForecastPanel
        mode="realtime"
        forecast={{
          predicted_nox: 25.0,
          target_time: '2026-05-12T07:35:00.000Z',
          threshold_value: 30.0,
          threshold_exceeded: false,
        }}
      />,
    )
    expect(screen.queryByText(/임계 초과/)).not.toBeInTheDocument()
  })
})
