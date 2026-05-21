import hmiLive from '../assets/hmi-live.png'

export function AboutPage() {
  return (
    <main className="content-page about-page">
      <div className="content-inner">
        <section className="hero-grid">
          <div>
            <div className="section-label">NOxO PROJECT</div>
            <h1 className="hero-title">
              조작이 만든 변화를,
              <br />
              먼저 시뮬레이션으로 본다.
            </h1>
            <p className="hero-copy">
              합성가스 발전소의 NOx는 한 번의 조작에 즉시 반응하지 않습니다.
              <br />
              운영자는 지금 누르면 잠시 후 어떻게 될지를 미리 가늠해야 했고,
              <br />
              그 판단의 무게가 곧 NOx 초과 사고로 이어졌습니다.
              <br />
              NOxO는 그 빈자리를 공정 시뮬레이션으로 채워, 운영자가 결정을 내리기 전에 결과를 먼저 보게 합니다.
            </p>
          </div>
          <div className="about-logomark" aria-label="NOxO">
            <div className="about-logomark-inner">
              NOx<span>O</span>
            </div>
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">PROBLEM</div>
          <h2 className="section-title">보이지 않는 응답</h2>
          <p className="body-copy">
            IGCC 가스터빈은 합성가스를 태워 전기를 만들고, 그 과정에서 NOx가 나옵니다. 법적 허용치를 넘으면 운전이
            멈추고, 보고서가 쌓이고, 다음 분기 운영 계획이 흔들립니다. 그래서 관제실의 운영자는
            <br />
            합성가스 유량·IGV 개도·희석질소까지 10개의 제어 변수를 동시에 들여다보며 NOx를 누르고 있습니다.
          </p>
          <p className="body-copy">
            문제는 NOx가 조작 직후에 보이지 않는다는 점입니다. 변수를 바꾼 결과는 한참 뒤에야 화면에 나타나고,
            그때는 이미 손쓰기 늦은 경우가 많았습니다. 운영자에게 필요한 것은 기다림이 아니라 미리
            <br />
            보기였습니다.
          </p>
          <div className="about-timeline">
            <TimelineDiagram />
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">CORE</div>
          <h2 className="section-title">프로젝트의 중심: Stateful 시뮬레이션</h2>
          <p className="body-copy">
            NOxO의 핵심은 합성가스 발전소 연소계를 그대로 재현하는 Stateful 시뮬레이션 엔진입니다. 운영자가 10개의
            제어 변수 중 하나를 조작하면, NOx·배기온도·발전량이 함께 움직이며 새 정상상태로
            <br />
            수렴해 갑니다. 한 번의 조작이 만들어내는 전체 응답 곡선을 운영자가 그대로 관찰할 수 있습니다.
          </p>
          <p className="body-copy">
            엔진은 물리 기반 화학 반응 모델과 데이터 기반 ML 모델을 함께 사용해, 실측 공정에 가까운 거동을
            재현합니다.
          </p>
          <figure className="about-hmi-mockup">
            <img src={hmiLive} alt="NOxO HMI 콘솔" />
            <figcaption className="about-hmi-caption">
              HMI CONSOLE · 합성가스 발전소 공정 시뮬레이션 대시보드
            </figcaption>
          </figure>
        </section>

        <section className="content-section">
          <div className="section-label">FORECAST</div>
          <h2 className="section-title">5분 후 NOx도 함께 본다</h2>
          <p className="body-copy">
            시뮬레이션이 조작의 결과를 보여준다면, 5분 후 예측은 조작이 없을 때의 자연 추이를 보여줍니다. 현재
            센서 시계열을 바탕으로 5분 뒤 NOx를 미리 추정해, 운영자가 상승 위험을 사전에 감지할 수 있게
            <br />
            합니다.
          </p>
        </section>
      </div>
      <PageFooter />
    </main>
  )
}

function TimelineDiagram() {
  return (
    <svg viewBox="0 0 720 140" className="about-timeline-svg" role="img" aria-label="조작과 예측의 시간 흐름">
      <defs>
        <marker id="tl-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="rgba(59, 130, 246, 0.85)" />
        </marker>
      </defs>

      <line x1="40" y1="78" x2="680" y2="78" stroke="rgba(255,255,255,0.18)" strokeWidth="1.5" markerEnd="url(#tl-arrow)" />

      <line x1="120" y1="62" x2="120" y2="94" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />
      <line x1="320" y1="62" x2="320" y2="94" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />
      <line x1="560" y1="62" x2="560" y2="94" stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />

      <circle cx="120" cy="78" r="5" fill="rgba(255,255,255,0.35)" />
      <circle cx="320" cy="78" r="7" fill="rgba(59, 130, 246, 0.9)" />
      <circle cx="560" cy="78" r="5" fill="rgba(139, 92, 246, 0.85)" />

      <text x="120" y="118" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace" fontSize="11" fill="rgba(255,255,255,0.45)">PAST</text>
      <text x="320" y="118" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace" fontSize="11" fill="rgba(255,255,255,0.85)">NOW</text>
      <text x="560" y="118" textAnchor="middle" fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace" fontSize="11" fill="rgba(139, 92, 246, 0.85)">+5 MIN</text>

      <text x="320" y="44" textAnchor="middle" fontFamily="system-ui, sans-serif" fontSize="12" fill="rgba(59, 130, 246, 0.95)" fontWeight="600">
        조작 → 시뮬레이션으로 응답 곡선 재현
      </text>
      <text x="560" y="44" textAnchor="middle" fontFamily="system-ui, sans-serif" fontSize="12" fill="rgba(139, 92, 246, 0.95)" fontWeight="600">
        예측된 NOx
      </text>
    </svg>
  )
}

function PageFooter() {
  return (
    <footer className="page-footer">
      <span>NOxO · 합성가스 발전 NOx 시뮬레이션 · 2026-04-29</span>
      <div className="footer-links">
        <span>PRD</span>
        <span>Architecture</span>
        <span>Repo</span>
      </div>
    </footer>
  )
}
