const tauRows = [
  ['NOx', '2.4 s', '화염 내 질소산화물 생성 반응 속도', '빠름'],
  ['CO', '1.8 s', '불완전 연소 CO 생성·소멸 반응 속도', '빠름'],
  ['화염온도', '5.2 s', '연소기 열용량에 의한 온도 관성', '중간'],
  ['λ (공기비)', '0.9 s', '연료-공기 혼합 시간', '매우 빠름'],
  ['효율', '8.5 s', '터빈 열역학적 균형에 의한 지연', '느림'],
]

const loopSteps = [
  ['① 조작 수신', '운영자가 ▲▼ 버튼으로 제어 변수를 변경하면 control_steps에 기록되고 다음 tick에 반영됩니다.'],
  ['② τ 응답 계산', '1차 지연 모델로 각 결과 변수가 목표값으로 수렴합니다. 변수별 τ가 서로 다른 응답 속도를 결정합니다.'],
  ['③ 스트림 발행', '갱신된 상태를 WebSocket으로 브로드캐스트하고 stream_snapshots에 저장합니다.'],
]

export function DigitalTwinPage() {
  return (
    <main className="content-page">
      <div className="content-inner">
        <section className="content-section split-hero">
          <div>
            <div className="section-label">DIGITAL TWIN</div>
            <h1 className="hero-title">합성가스 발전 공정의 물리 기반 디지털 트윈</h1>
            <p className="hero-copy">
              실제 발전소의 운전 거동을 수식으로 재현한 시뮬레이션 엔진입니다. 제어 변수를 조작하면 시간 상수 τ에
              따라 NOx, CO, 화염온도, 효율이 순차적으로 변화합니다.
            </p>
          </div>
          <div className="formula-card">
            <div className="section-label">1차 지연 응답 수식</div>
            <div className="mono formula-text">y(t) = y∞ + (y0 − y∞) · e−t/τ</div>
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">PROCESS</div>
          <h2 className="section-title">공정 구조</h2>
          <div className="process-grid">
            <ProcessCard
              title="① 연료 공급"
              subtitle="Syngas Supply"
              body="합성가스 유량과 희석질소 유량을 제어 변수로 입력하고 부하율로 전체 스케일을 조정합니다."
            />
            <ProcessCard
              title="② 합성가스 반응기"
              subtitle="Syngas Reactor"
              body="연료와 N2가 혼합·연소되고 공기비 λ와 화염온도가 결정됩니다. NOx 생성의 핵심 지점입니다."
              active
            />
            <ProcessCard
              title="③ 가스터빈"
              subtitle="Gas Turbine"
              body="연소 가스로 터빈을 구동해 발전 효율을 만듭니다. 부하율과 연료량이 효율에 영향을 줍니다."
            />
            <ProcessCard
              title="④ 배기 라인"
              subtitle="Exhaust"
              body="연소 후 배기가스가 배출되고 NOx와 CO 농도가 최종 측정되어 환경 규제 대상이 됩니다."
            />
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">TIME CONSTANT τ</div>
          <h2 className="section-title">시간 상수 응답 모델</h2>
          <table className="data-table panel">
            <thead>
              <tr>
                <th>결과 변수</th>
                <th>시간 상수 τ</th>
                <th>물리적 의미</th>
                <th>응답 특성</th>
              </tr>
            </thead>
            <tbody>
              {tauRows.map(([name, tau, meaning, response]) => (
                <tr key={name}>
                  <td className="label-cell">{name}</td>
                  <td>{tau}</td>
                  <td className="description-cell">{meaning}</td>
                  <td className="muted-cell">{response}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="content-section">
          <div className="section-label">SIM LOOP</div>
          <h2 className="section-title">시뮬레이션 루프 구조</h2>
          <div className="goal-grid">
            {loopSteps.map(([title, body]) => (
              <article key={title} className="goal-card">
                <div className="goal-title">{title}</div>
                <p className="goal-body">{body}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
      <PageFooter />
    </main>
  )
}

function ProcessCard({
  title,
  subtitle,
  body,
  active,
}: {
  title: string
  subtitle: string
  body: string
  active?: boolean
}) {
  return (
    <article className={active ? 'process-card active' : 'process-card'}>
      <div className="process-label">{title}</div>
      <div className="process-title">{subtitle}</div>
      <p className="goal-body">{body}</p>
    </article>
  )
}

function PageFooter() {
  return (
    <footer className="page-footer">
      <span>NOxO · 합성가스 발전 NOx 디지털 트윈 · 2026-04-29</span>
      <div className="footer-links">
        <span>PRD</span>
        <span>Architecture</span>
        <span>Repo</span>
      </div>
    </footer>
  )
}
