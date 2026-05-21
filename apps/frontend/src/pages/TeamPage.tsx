type Member = {
  name: string
  role: string
  lead?: boolean
  email: string
  github: string
  initials: string
}

function githubAvatar(url: string, size = 200) {
  const handle = url.replace(/^https?:\/\/github\.com\//, '').replace(/\/$/, '')
  return `https://github.com/${handle}.png?size=${size}`
}

const members: Member[] = [
  {
    name: '김희태',
    role: 'AI/ML Engineering',
    lead: true,
    email: 'heetae104@gmail.com',
    github: 'https://github.com/kimheetae0104',
    initials: 'KH',
  },
  {
    name: '신성훈',
    role: 'Data · DB Engineering',
    email: 'dotofi@naver.com',
    github: 'https://github.com/seonghoon90',
    initials: 'SH',
  },
  {
    name: '안태현',
    role: 'Full-stack · Agentic Engineering',
    email: 'rapael817@naver.com',
    github: 'https://github.com/taehyunan-99',
    initials: 'AT',
  },
  {
    name: '지태현',
    role: 'Data Analytics',
    email: 'sys9807@naver.com',
    github: 'https://github.com/Tay-hyyyyn',
    initials: 'JT',
  },
]

const roles: Array<[string, string, string]> = [
  ['AI/ML Engineering', '김희태 (팀장)', 'Ridge·LGB 앙상블, Zeldovich ODE, 5분 NOx 예측 모델'],
  ['Data · DB Engineering', '신성훈', 'sensor_data 스키마, Kafka 스트림, 학습 데이터 파이프라인'],
  ['Full-stack · Agentic Engineering', '안태현', 'React 콘솔, FastAPI 세션, WebSocket, 에이전트 환경 구축'],
  ['Data Analytics', '지태현', '운전 분포 분석, 임계 산정, 모델 성능 검증'],
]

function githubHandle(url: string) {
  return url.replace(/^https?:\/\/github\.com\//, '@')
}

export function TeamPage() {
  return (
    <main className="content-page team-page">
      <div className="content-inner">
        <section className="content-section">
          <div className="section-label">TEAM</div>
          <h1 className="section-title">이 콘솔을 만든 사람들</h1>
          <p className="body-copy">
            AI/ML, 데이터 엔지니어링, 풀스택, 데이터 분석 네 영역을 나눠 맡아 NOxO를 만들었습니다.
          </p>
          <div className="team-grid">
            {members.map((m) => (
              <article key={m.name} className="team-card">
                <div className="team-card-head">
                  <div className="avatar avatar-photo">
                    <img
                      src={githubAvatar(m.github)}
                      alt={`${m.name} GitHub avatar`}
                      loading="lazy"
                      referrerPolicy="no-referrer"
                    />
                  </div>
                  {m.lead ? <div className="team-lead-badge">팀장</div> : null}
                </div>
                <div className="member-name">{m.name}</div>
                <div className="role-badge">{m.role}</div>
                <div className="team-contact">
                  <a className="team-contact-row" href={`mailto:${m.email}`}>
                    <span className="team-contact-key">EMAIL</span>
                    <span className="team-contact-value">{m.email}</span>
                  </a>
                  <a
                    className="team-contact-row"
                    href={m.github}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <span className="team-contact-key">GITHUB</span>
                    <span className="team-contact-value mono">{githubHandle(m.github)}</span>
                  </a>
                </div>
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
    </main>
  )
}
