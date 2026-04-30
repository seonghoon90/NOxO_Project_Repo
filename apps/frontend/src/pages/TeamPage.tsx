const members = [
  ['안태현', 'FRONTEND', 'React 기반 운영자 콘솔과 실시간 스트리밍 UI를 담당합니다.', 'AT'],
  ['팀원 B', 'BACKEND', 'FastAPI, WebSocket, 세션과 스냅샷 영속 계층을 담당합니다.', 'B'],
  ['팀원 C', 'DIGITAL TWIN', '물리 기반 시뮬 루프와 시간 상수 τ 모델링을 담당합니다.', 'C'],
  ['팀원 D', 'DATA / ML', '운전 시퀀스 학습과 미래 NOx 예측 모델을 담당합니다.', 'D'],
]

const roles = [
  ['프론트엔드', '안태현', '메인 대시보드, 시계열 차트, 도면 오버레이'],
  ['백엔드', '팀원 B', 'API, WebSocket 게이트웨이, 세션 영속'],
  ['디지털 트윈', '팀원 C', '시뮬 루프, τ 기반 응답 함수'],
  ['데이터·ML', '팀원 D', '학습 파이프라인, 예측 서비스'],
]

export function TeamPage() {
  return (
    <main className="content-page">
      <div className="content-inner">
        <section className="content-section">
          <div className="section-label">TEAM</div>
          <h1 className="section-title">이 콘솔을 만든 사람들</h1>
          <p className="body-copy">프론트엔드, 백엔드, 디지털 트윈, 데이터 분석 네 영역을 나눠 맡았습니다.</p>
          <div className="team-grid">
            {members.map(([name, role, body, initials]) => (
              <article key={name} className="team-card">
                <div className="avatar">{initials}</div>
                <div className="member-name">{name}</div>
                <div className="role-badge">{role}</div>
                <p className="goal-body">{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="content-section">
          <h2 className="section-title">역할 분담</h2>
          <table className="data-table panel">
            <thead>
              <tr>
                <th>영역</th>
                <th>담당</th>
                <th>주요 산출물</th>
              </tr>
            </thead>
            <tbody>
              {roles.map(([area, owner, deliverable]) => (
                <tr key={area}>
                  <td className="label-cell">{area}</td>
                  <td>{owner}</td>
                  <td className="description-cell">{deliverable}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <PageFooter />
    </main>
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
