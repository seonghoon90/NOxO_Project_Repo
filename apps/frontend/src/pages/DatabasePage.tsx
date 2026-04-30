/**
 * DB 스키마 페이지.
 *
 * 본 페이지는 BACKEND_ARCHITECTURE §6 「데이터 저장 전략」의 [DB 협의 필요] 가안을
 * 시각화한다. 현재 백엔드는 PostgreSQL 연결만 준비되어 있고 실제 repository / Alembic
 * 마이그레이션은 구현되지 않았다 (Phase 2 예정). 따라서 아래 표는 협의 후 변경 가능한
 * 설계 초안이며, 실제 운영 통계가 아니다.
 */

/**
 * 식별자 표기 원칙:
 * - 제어 변수는 raw 태그(`IGCC.CC.G1.*`)가 진실 공급원이다. 영속화 컬럼명은
 *   raw 태그를 보존하거나 백엔드 API 필드명(`syngas_flow`, `n2_offset`,
 *   `igv_opening`)에 맞춘다. 프론트 내부 키(`syngas`/`n2`/`load`)는 사용하지 않는다.
 * - mode 값은 현재 프론트가 보내는 `'sim' | 'pred'` 문자열을 그대로 따른다.
 * - 출력 변수는 백엔드 stream 필드명(`nox`, `co`, `exhaust_temp`, `lambda`, `power`)을 따른다.
 */
const erdTables = [
  {
    name: 'sessions',
    note: '가안 — [DB 협의 필요]',
    columns: [
      ['id', 'uuid', 'PK', '세션 식별자'],
      ['started_at', 'timestamptz', '', '세션 시작 시각'],
      ['ended_at', 'timestamptz?', 'nullable', '세션 종료 시각'],
      ['mode', 'text', '', "'sim' | 'pred' (frontend Mode와 일치)"],
    ],
  },
  {
    name: 'control_inputs',
    note: '가안 — [DB 협의 필요]',
    columns: [
      ['id', 'bigint', 'PK', '자동 증가 식별자'],
      ['session_id', 'uuid', 'FK', 'sessions.id 참조'],
      ['t_offset', 'numeric', '', '세션 시작 후 경과 초'],
      ['tag', 'text', '', "raw 태그 (예: 'IGCC.CC.G1.ca_fqsg_cl')"],
      ['value', 'numeric', '', '주입된 제어값'],
      ['created_at', 'timestamptz', '', '기록 시각'],
    ],
  },
  {
    name: 'stream_snapshots',
    note: '가안 — [DB 협의 필요]',
    columns: [
      ['id', 'bigint', 'PK', '자동 증가'],
      ['session_id', 'uuid', 'FK', 'sessions.id 참조'],
      ['t', 'numeric', '', '세션 기준 경과 초'],
      ['syngas_flow', 'numeric', '', 'IGCC.CC.G1.ca_fqsg_cl'],
      ['n2_offset', 'numeric', '', 'IGCC.CC.G1.NQKR3_MONITOR'],
      ['igv_opening', 'numeric', '', 'IGCC.CC.G1.csgv'],
      ['nox', 'numeric', '', 'NOx (ppm)'],
      ['co', 'numeric', '', 'CO (ppm)'],
      ['exhaust_temp', 'numeric', '', '배기온도 (°C) — IGCC.CC.G1.TTXM'],
      ['lambda', 'numeric', '', '공기비 (-)'],
      ['power', 'numeric', '', 'IGCC.CC.G1.DWATT (MW)'],
      ['warning', 'boolean', '', 'NOx 임계 초과 여부'],
      ['ts', 'timestamptz', '', '스냅샷 절대 시각'],
    ],
  },
  {
    name: 'predictions',
    note: '가안 — [DB 협의 필요]',
    columns: [
      ['id', 'bigint', 'PK', '자동 증가'],
      ['session_id', 'uuid', 'FK', 'sessions.id 참조 (단발 예측은 nullable)'],
      ['target_minutes', 'integer', '', '예측 대상 미래 분 수 (POST /api/prediction)'],
      ['predicted_nox', 'numeric', '', '예측 NOx 값 (ppm)'],
      ['threshold_value', 'numeric', '', '임계치 (ppm)'],
      ['threshold_exceeded', 'boolean', '', '예측값이 임계치 초과 여부'],
      ['target_time', 'timestamptz', '', '예측 대상 절대 시각'],
      ['created_at', 'timestamptz', '', '예측 요청 시각'],
    ],
  },
]

export function DatabasePage() {
  return (
    <main className="content-page">
      <div className="content-inner db-inner">
        <div className="section-label">DATABASE</div>
        <h1 className="section-title">데이터 모델 (가안)</h1>
        <p className="body-copy">
          시뮬 세션과 운전 스냅샷을 저장하기 위한 핵심 테이블의 <strong>설계 초안</strong>이다.
          실제 컬럼명·타입·인덱스·보존 정책은 DB 팀과 협의 후 확정한다.
        </p>

        <section
          className="panel"
          style={{
            padding: '14px 18px',
            margin: '12px 0 24px',
            borderColor: 'rgba(245, 158, 11, 0.45)',
            background: 'rgba(245, 158, 11, 0.08)',
          }}
        >
          <strong>구현 상태</strong> — 본 스키마는 아직 구현되지 않았다.
          백엔드는 PostgreSQL 연결만 준비되어 있고 SQLAlchemy 모델·Alembic 마이그레이션은
          Phase 2에서 도입 예정이다. 현재 시뮬 세션 상태는 in-memory에만 보관되며,
          서버 재시작 시 유실된다 (BACKEND_ARCHITECTURE §6 명시).
        </section>

        <section className="erd-container">
          <div className="erd-wrap">
            <svg className="erd-svg" viewBox="0 0 900 456">
              <line x1="220" y1="140" x2="340" y2="100" className="erd-link" />
              <line x1="220" y1="150" x2="340" y2="210" className="erd-link" />
              <line x1="220" y1="160" x2="340" y2="340" className="erd-link" />
            </svg>
            <TableNode left={10} top={100} width={230} title="sessions" rows={['id', 'started_at', 'ended_at', 'mode']} />
            <TableNode
              left={340}
              top={30}
              width={240}
              title="control_inputs"
              rows={['id', 'session_id', 't_offset', 'tag', 'value', 'created_at']}
            />
            <TableNode
              left={340}
              top={180}
              width={290}
              title="stream_snapshots"
              rows={[
                'id',
                'session_id',
                't',
                'syngas_flow, n2_offset, igv_opening',
                'nox, co, exhaust_temp, lambda',
                'power',
                'warning',
                'ts',
              ]}
            />
            <TableNode
              left={340}
              top={400}
              width={260}
              title="predictions"
              rows={['id', 'session_id', 'target_minutes', 'predicted_nox', 'threshold_exceeded', 'target_time', 'created_at']}
            />
          </div>
        </section>

        <section className="content-section">
          <h2 className="section-title">테이블 명세 (협의 전)</h2>
          <div className="spec-grid">
            {erdTables.map((table) => (
              <article key={table.name} className="panel spec-card">
                <header className="spec-header">
                  <div className="spec-title">{table.name}</div>
                  <span className="mono spec-count">{table.note}</span>
                </header>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>컬럼</th>
                      <th>타입</th>
                      <th>제약</th>
                      <th>설명</th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.columns.map(([name, type, constraint, description]) => (
                      <tr key={`${table.name}-${name}`}>
                        <td className="label-cell">{name}</td>
                        <td>{type}</td>
                        <td className="muted-cell">{constraint}</td>
                        <td className="description-cell">{description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </article>
            ))}
          </div>
        </section>
      </div>
      <PageFooter />
    </main>
  )
}

function TableNode({
  left,
  top,
  width,
  title,
  rows,
}: {
  left: number
  top: number
  width: number
  title: string
  rows: string[]
}) {
  return (
    <div className="table-node" style={{ left, top, width }}>
      <div className="table-node-header">{title}</div>
      {rows.map((row) => (
        <div key={row} className="table-node-row">
          <span className="mono">{row}</span>
        </div>
      ))}
    </div>
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
