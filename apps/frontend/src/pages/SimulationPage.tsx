const heroStats = [
  { value: '10', label: '제어 변수' },
  { value: '5', label: '출력 변수' },
  { value: '0.2', label: 'step dt', unit: 's' },
  { value: '8', label: 'step 단계' },
]

const inputRows: Array<[string, string, string]> = [
  ['합성가스', 'syngas_flow', '합성가스 유량'],
  ['합성가스', 'syngas_srv', 'SRV 밸브 개도'],
  ['합성가스', 'syngas_gcv_1 · _1a · _2', 'GCV 밸브 3종 개도'],
  ['희석질소', 'n2_flow', 'N₂ 주입 유량'],
  ['희석질소', 'n2_valve_1', 'N₂ 제어밸브 개도'],
  ['희석질소', 'n2_offset', '연료 대비 N₂ 오프셋'],
  ['공기', 'igv_opening', '입구 가이드 베인 개도'],
  ['공기', 'ibh_valve', 'IBH 가열 제어밸브 개도'],
]

const outputRows: Array<[string, string, string]> = [
  ['NOx', 'ppm', 'Zeldovich ODE + ML 앙상블 블렌딩'],
  ['TTXM (배기온도)', '°C', 'ML 회귀 + 1차 lag'],
  ['DWATT (발전량)', 'MW', 'ML 회귀 + 1차 lag'],
  ['λ (공기비)', '—', 'syngas · n2 · IGV 즉시 계산'],
  ['η (효율)', '—', 'DWATT / (syngas_flow × LHV) 후처리'],
]

const stepCards: Array<[string, string, string]> = [
  ['① 제어 입력 lag', 'INPUT LAG', 'target → current 점진 수렴 (10개 변수 각각)'],
  ['② 공기비 λ 계산', 'INSTANT', 'syngas · n2_offset · IGV로 즉시 산출 (lag 없음)'],
  ['③ ML 정상상태 추론', 'ML', 'Ridge·LGB 앙상블이 NOx · TTXM · DWATT 회귀'],
  ['④ 배기온도 lag', 'THERMAL', 'TTXM이 열관성(τ=10s)으로 천천히 수렴'],
  ['⑤ Zeldovich ODE 적분', 'PHYSICS', 'Arrhenius 반응속도로 NOx 생성률 누적'],
  ['⑥ NOx 블렌딩', 'BLEND', 'ML lag 결과와 ODE 적분 결과의 가중합'],
  ['⑦ 발전량 · 효율 산출', 'DERIVED', 'DWATT lag + 효율 후처리'],
  ['⑧ 임계 비교', 'GUARD', 'NOx 경고 플래그 갱신'],
]

const stateRows: Array<[string, string]> = [
  ['target', '사용자가 방금 누른 운전 목표'],
  ['current', 'lag을 거쳐 실제 운전점으로 수렴한 입력'],
  ['output_target', 'ML이 예측한 정상상태 출력'],
  ['output', 'lag·ODE를 거쳐 화면에 표시되는 최종 출력'],
]

const baseline = [
  { key: 'syngas_flow', value: '43.0 kg/s' },
  { key: 'IGV', value: '63.0 %' },
  { key: 'n2_flow', value: '29.0' },
  { key: 'n2_offset', value: '−10.0' },
  { key: 'NOx', value: '29.0 ppm' },
  { key: 'TTXM', value: '627.5 °C' },
  { key: 'DWATT', value: '164.0 MW' },
  { key: 'λ', value: '1.93' },
]

export function SimulationPage() {
  return (
    <main className="content-page sim-page">
      <div className="content-inner">
        <section className="content-section split-hero">
          <div>
            <div className="section-label">SIMULATION</div>
            <h1 className="hero-title">
              물리식과 데이터,
              <br />
              두 갈래의 계산이 한 step에서 만난다.
            </h1>
            <p className="hero-copy">
              NOxO 시뮬레이션은 합성가스 발전소 연소계를 그대로 재현하는 stateful 엔진입니다. 운영자가 제어 변수를
              조작하면 매 0.2초마다 8단계 step이 실행되어, NOx·배기온도·발전량이 새 정상상태로 수렴해 갑니다.
            </p>
          </div>
          <div className="sim-hero-stats">
            {heroStats.map((s) => (
              <div key={s.label} className="sim-hero-stat">
                <div className="sim-hero-stat-value">
                  {s.value}
                  {s.unit ? <span className="sim-hero-stat-unit">{s.unit}</span> : null}
                </div>
                <div className="sim-hero-stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">INPUT</div>
          <h2 className="section-title">운영자가 조작하는 10개의 변수</h2>
          <p className="body-copy">
            시뮬레이션의 입력은 IGCC 가스터빈 G1의 운전 파라미터 10개입니다. 합성가스 라인·희석질소 라인·IGV·IBH 등
            실제 운전 화면의 제어 변수와 1:1로 매핑되어 있습니다.
          </p>
          <table className="data-table panel">
            <thead>
              <tr>
                <th>계통</th>
                <th>변수</th>
                <th>의미</th>
              </tr>
            </thead>
            <tbody>
              {inputRows.map(([line, name, meaning]) => (
                <tr key={name}>
                  <td className="label-cell">{line}</td>
                  <td className="mono">{name}</td>
                  <td className="description-cell">{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="content-section">
          <div className="section-label">OUTPUT</div>
          <h2 className="section-title">시뮬레이션이 산출하는 5개의 변수</h2>
          <p className="body-copy">
            한 step이 끝나면 5개의 값이 갱신됩니다. NOx·배기온도·발전량은 ML 모델이 직접 회귀하고, 공기비 λ와 발전
            효율은 후처리 수식으로 산출되는 파생값입니다.
          </p>
          <table className="data-table panel">
            <thead>
              <tr>
                <th>변수</th>
                <th>단위</th>
                <th>산출 방식</th>
              </tr>
            </thead>
            <tbody>
              {outputRows.map(([name, unit, source]) => (
                <tr key={name}>
                  <td className="label-cell">{name}</td>
                  <td className="mono">{unit}</td>
                  <td className="description-cell">{source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="content-section">
          <div className="section-label">ARCHITECTURE</div>
          <h2 className="section-title">한 step에서 일어나는 8단계</h2>
          <p className="body-copy">
            한 step 안에서 물리 기반 모델과 데이터 기반 모델이 동시에 풀립니다. 운영자의 목표값(target)은 1차 lag을
            거쳐 실제 운전점(current)으로 천천히 수렴하고, 그 사이 ML 모델이 정상상태 출력을 회귀합니다.
          </p>
          <div className="sim-lag-card">
            <div className="section-label">1차 지연 응답</div>
            <div className="sim-lag-formula mono">y(t + dt) = y∞ + (y(t) − y∞) · exp(−dt / τ)</div>
            <p className="sim-lag-note">
              모든 동적 변수에는 1차 지연 식이 적용됩니다. 변수별 시간 상수 τ는 합성가스 유량 1.0s, IGV 2.0s, NOx
              5.0s, 발전량 8.5s, 배기온도 10.0s로, 각자의 응답 속도가 다릅니다.
            </p>
          </div>
          <div className="sim-step-grid">
            {stepCards.map(([title, badge, body]) => (
              <article key={title} className="sim-step-card">
                <div className="sim-step-badge">{badge}</div>
                <div className="sim-step-title">{title}</div>
                <p className="sim-step-body">{body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="content-section">
          <div className="section-label">STATE</div>
          <h2 className="section-title">상태는 4단으로 분리된다</h2>
          <p className="body-copy">
            시뮬레이션이 조작 즉시 반응처럼 보이지 않게 하려면, 사용자가 누른 값과 실제 운전점을 분리해야 합니다.
            NOxO는 입력·출력 각각을 target과 current로 나눠 4단 구조로 관리합니다.
          </p>
          <table className="data-table panel">
            <thead>
              <tr>
                <th>단계</th>
                <th>의미</th>
              </tr>
            </thead>
            <tbody>
              {stateRows.map(([stage, meaning]) => (
                <tr key={stage}>
                  <td className="label-cell mono">{stage}</td>
                  <td className="description-cell">{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="content-section">
          <div className="section-label">MODEL</div>
          <h2 className="section-title">Physics + Data, 하나의 NOx</h2>
          <div className="sim-model-grid">
            <article className="sim-model-card">
              <div className="section-label">PHYSICS · Zeldovich ODE</div>
              <p className="body-copy">
                Thermal NOx의 지배 메커니즘인 확장 Zeldovich 반응을 Arrhenius 형태 1식으로 근사 적분합니다.
                배기온도·O₂·N₂ 농도를 입력으로 NOx 생성률을 계산합니다.
              </p>
              <pre className="sim-model-formula">{`d[NO]/dt ≈ 2 · k(T) · [O][N₂]
k(T) = A · exp(−Eₐ / RT)
A = 1.8×10⁸,  Eₐ = 318 kJ/mol`}</pre>
            </article>
            <article className="sim-model-card">
              <div className="section-label">DATA · Ridge + LightGBM</div>
              <p className="body-copy">
                1분 집계 학습 데이터로 246개 피처에서 3개 타깃(NOx·TTXM·DWATT) 다중 회귀. Ridge 0.95 + LGB 0.05
                비중으로 앙상블해, 정상상태 회귀 기준 NOx R² 0.994 수준을 달성했습니다.
              </p>
              <div className="sim-model-metrics">
                <div>
                  <span className="sim-model-metric-value">0.994</span>
                  <span className="sim-model-metric-label">NOx R²</span>
                </div>
                <div>
                  <span className="sim-model-metric-value">246</span>
                  <span className="sim-model-metric-label">피처 수</span>
                </div>
                <div>
                  <span className="sim-model-metric-value">1 min</span>
                  <span className="sim-model-metric-label">학습 단위</span>
                </div>
              </div>
            </article>
          </div>
          <article className="sim-blend-card">
            <div className="section-label">BLEND · 두 결과의 가중합</div>
            <p className="body-copy">
              매 step ML lag 결과와 Zeldovich ODE 누적치는 blend_ratio로 가중 합산되어 최종 NOx가 결정됩니다.
              데이터 학습으로 얻은 정확도 위에 물리식의 외삽 안정성을 덧붙이는 구조입니다.
            </p>
            <pre className="sim-model-formula">{`NOx_final = (1 − blend) · NOx_ML_lag  +  blend · NOx_Zeldovich`}</pre>
          </article>
        </section>

        <section className="content-section">
          <div className="section-label">BASELINE</div>
          <h2 className="section-title">정상 운전점</h2>
          <p className="body-copy">
            시뮬레이션은 학습 CSV의 정상 운전 구간(DWATT &gt; 50 MW, 86,401행) median 값을 기준 운전점으로
            출발합니다.
          </p>
          <div className="sim-baseline-grid">
            {baseline.map((b) => (
              <div key={b.key} className="sim-baseline-chip">
                <div className="sim-baseline-key">{b.key}</div>
                <div className="sim-baseline-value">{b.value}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  )
}
