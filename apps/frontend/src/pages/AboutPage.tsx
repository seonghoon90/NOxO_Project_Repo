const goals = [
  {
    title: 'Stateful 시뮬레이션',
    body: '운영자의 매 조작이 이전 상태에 누적되어 시간 상수 τ에 따라 응답하는 시뮬레이션을 제공합니다.',
  },
  {
    title: '미래 NOx 예측',
    body: '현재까지의 운전 시퀀스를 학습한 모델로 5분 후 NOx와 허용치 초과 여부를 함께 보여줍니다.',
  },
  {
    title: '산업용 운영자 톤',
    body: 'Grafana와 SCADA 사이의 밀도 높은 다크 콘솔 톤으로 장시간 모니터링에 맞췄습니다.',
  },
]

const flows = [
  '운영자 조작',
  'Digital Twin 시뮬 루프',
  'WebSocket 스트림',
  '프론트 대시보드',
  '미래 예측 모델',
]

export function AboutPage() {
  return (
    <main className="content-page">
      <div className="content-inner">
        <section className="hero-grid">
          <div>
            <div className="section-label">NOxO PROJECT</div>
            <h1 className="hero-title">합성가스 발전 NOx, 실시간으로 관측하고 예측한다.</h1>
            <p className="hero-copy">
              운영자가 변수 하나를 바꾸면, 시간 상수 τ 만큼 늦게 다른 공정 변수가 응답합니다. NOxO는 그 응답을
              디지털 트윈으로 재현하고, 미래 NOx를 예측합니다.
            </p>
          </div>
          <div className="mini-plant-card">
            <MiniPlant />
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">PROBLEM</div>
          <h2 className="section-title">왜 NOx인가</h2>
          <p className="body-copy">
            합성가스 발전은 환경 규제의 정점인 NOx 배출량 통제가 핵심입니다. 허용 기준을 초과하면 운전 중단과 법적
            제재가 뒤따르기 때문에 운영자는 매 순간 NOx 수치를 주시해야 합니다.
          </p>
          <p className="body-copy">
            운전 변수는 즉각 반응하지 않습니다. 시간 상수 τ 때문에 운영자는 지금 조작이 몇 초 뒤에 어떻게 반영될지
            머릿속으로 계산해야 하고, 이 인지 부담이 오조작으로 이어집니다.
          </p>
        </section>

        <section className="content-section">
          <div className="section-label">GOALS</div>
          <h2 className="section-title">이 프로젝트가 해결하려는 것</h2>
          <div className="goal-grid">
            {goals.map((goal) => (
              <article key={goal.title} className="goal-card">
                <div className="goal-title">{goal.title}</div>
                <p className="goal-body">{goal.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">SYSTEM</div>
          <h2 className="section-title">데이터 흐름</h2>
          <p className="body-copy">운영자 조작 → 디지털 트윈 시뮬 루프 → WebSocket 스트림 → 프론트 대시보드 → 예측 모델.</p>
          <div className="flow-strip">
            {flows.map((flow, index) => (
              <div key={flow} className="flow-node">
                <span>{flow}</span>
                {index < flows.length - 1 ? <span className="flow-arrow">→</span> : null}
              </div>
            ))}
          </div>
        </section>
      </div>
      <PageFooter />
    </main>
  )
}

function MiniPlant() {
  return (
    <svg viewBox="0 0 440 160" className="mini-plant-svg">
      <line x1="78" y1="80" x2="112" y2="80" className="plant-link" />
      <line x1="192" y1="80" x2="226" y2="80" className="plant-link" />
      <line x1="276" y1="80" x2="310" y2="80" className="plant-link" />
      <line x1="154" y1="118" x2="154" y2="105" className="plant-link-secondary" />
      <rect x="18" y="68" width="60" height="24" rx="5" className="plant-node" />
      <text x="48" y="83" textAnchor="middle" className="plant-text secondary">
        연료 공급
      </text>
      <rect x="114" y="60" width="78" height="40" rx="5" className="plant-node active" />
      <text x="153" y="78" textAnchor="middle" className="plant-text active">
        합성가스
      </text>
      <text x="153" y="90" textAnchor="middle" className="plant-text active">
        반응기
      </text>
      <circle cx="251" cy="80" r="25" className="plant-node" />
      <text x="251" y="77" textAnchor="middle" className="plant-text secondary">
        가스
      </text>
      <text x="251" y="88" textAnchor="middle" className="plant-text secondary">
        터빈
      </text>
      <rect x="312" y="68" width="60" height="24" rx="5" className="plant-node" />
      <text x="342" y="83" textAnchor="middle" className="plant-text secondary">
        배기 라인
      </text>
    </svg>
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
