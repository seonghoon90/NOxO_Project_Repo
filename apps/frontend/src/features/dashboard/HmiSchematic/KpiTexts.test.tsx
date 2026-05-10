import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { KpiTexts, type KpiTextsProps } from './KpiTexts'

const FULL_PROPS: KpiTextsProps = {
  nox: 26.5, ttxm: 580, dwatt: 248.6, lambda: 1.10,
  syngas: 1500, fsagr: 76, fsag11: 45, fsag11a: 45.9, fsag12: 76,
  nicvs1: 75, nqj: 15.7, csbhx: 75, csgv: 75, nqkr3: 200,
}

function renderInSvg(props: KpiTextsProps) {
  return render(
    <svg viewBox="0 0 1316 540">
      <KpiTexts {...props} />
    </svg>,
  )
}

describe('KpiTexts', () => {
  it('14개 text 렌더 (4 KPI + 10 보조), textContent가 props 값과 일치', () => {
    const { container } = renderInSvg(FULL_PROPS)
    const texts = container.querySelectorAll('text[data-role^="kpi-text-"]')
    expect(texts.length).toBe(14)
    const map = new Map<string, string>()
    texts.forEach((t) => {
      const role = t.getAttribute('data-role')!
      map.set(role, t.textContent ?? '')
    })
    expect(map.get('kpi-text-nox')).toBe('26.5')
    expect(map.get('kpi-text-ttxm')).toBe('580.0')
    expect(map.get('kpi-text-dwatt')).toBe('248.6')
    expect(map.get('kpi-text-lambda')).toBe('1.10')
    expect(map.get('kpi-text-syngas')).toBe('1500.0')
    expect(map.get('kpi-text-nqkr3')).toBe('200.0')
  })

  it('NaN/Infinity 입력 → "--"', () => {
    const props = Object.fromEntries(
      Object.keys(FULL_PROPS).map((k) => [k, NaN]),
    ) as unknown as KpiTextsProps
    const { container } = renderInSvg(props)
    const texts = container.querySelectorAll('text[data-role^="kpi-text-"]')
    texts.forEach((t) => expect(t.textContent).toBe('--'))
  })

  it('각 text는 KPI_ANCHORS 좌표 사용 + textAnchor=start', () => {
    const { container } = renderInSvg(FULL_PROPS)
    const nox = container.querySelector('text[data-role="kpi-text-nox"]')!
    expect(nox.getAttribute('text-anchor')).toBe('start')
    expect(nox.getAttribute('x')).toMatch(/\d+(\.\d+)?/)
    expect(nox.getAttribute('y')).toMatch(/\d+(\.\d+)?/)
  })
})
