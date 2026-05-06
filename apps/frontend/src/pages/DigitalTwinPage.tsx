import { useOutletContext } from 'react-router-dom'
import { useConsoleState } from '../features/dashboard/useConsoleState'
import type { AppOutletContext } from '../app/App'

// NOxO design tokens (mirrors index.css CSS vars)
const C = {
  bg:       '#0b0f14',
  surface:  '#11161d',
  surface2: '#161d26',
  surface3: '#1c242f',
  line:     'rgba(255,255,255,0.10)',
  lineStr:  'rgba(255,255,255,0.18)',
  text:     'rgba(255,255,255,0.92)',
  text2:    'rgba(255,255,255,0.58)',
  text3:    'rgba(255,255,255,0.28)',
  blue:     '#3b82f6',
  blueBg:   'rgba(59,130,246,0.09)',
  green:    '#10b981',
  greenBg:  'rgba(16,185,129,0.08)',
  amber:    '#f59e0b',
  red:      '#ef4444',
} as const

export function DigitalTwinPage() {
  const { mode } = useOutletContext<AppOutletContext>()
  const { state } = useConsoleState(mode)

  const sg  = state.variables.syngas.value
  const n2  = state.variables.n2.value
  const igv = state.variables.load.value
  const { nox, co, exhaust, lambda, power } = state.metrics
  const efficiency = Math.min(99, Math.max(60, (89 * power) / 248.6)).toFixed(1)
  const noxColor   = nox > 50 ? C.red : C.blue

  return (
    <div style={{ width: '100%', height: 'calc(100vh - 56px)', overflow: 'hidden', background: C.bg }}>
      <svg
        viewBox="0 0 1456 816"
        width="100%"
        height="100%"
        style={{ display: 'block' }}
      >
        <defs>
          {/* 파이프 — 핑크 (SYNGAS) */}
          <linearGradient id="gPink" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#f472b6" />
            <stop offset="40%"  stopColor="#ec4899" />
            <stop offset="100%" stopColor="#9d174d" />
          </linearGradient>
          {/* 파이프 — 올리브 (N2 inject) */}
          <linearGradient id="gOlive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#a3e635" />
            <stop offset="40%"  stopColor="#84cc16" />
            <stop offset="100%" stopColor="#3f6212" />
          </linearGradient>
          {/* 파이프 — 앰버 (N2 dilution) */}
          <linearGradient id="gRed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#fbbf24" />
            <stop offset="40%"  stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#78350f" />
          </linearGradient>
          {/* 수직선 — 파란 (NPNJ2) */}
          <linearGradient id="gBlue" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"   stopColor="#60a5fa" />
            <stop offset="50%"  stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#1d4ed8" />
          </linearGradient>
          {/* 터빈 몸통 */}
          <linearGradient id="gTurb" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#1e293b" />
            <stop offset="30%"  stopColor="#1a2332" />
            <stop offset="70%"  stopColor="#0f172a" />
            <stop offset="100%" stopColor="#0a1120" />
          </linearGradient>
          {/* 연소캔 */}
          <radialGradient id="gCan" cx="35%" cy="35%">
            <stop offset="0%"   stopColor="#fbbf24" />
            <stop offset="45%"  stopColor="#ef4444" />
            <stop offset="100%" stopColor="#7f1d1d" />
          </radialGradient>
          {/* 패널 */}
          <linearGradient id="gPanel" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#161d26" />
            <stop offset="100%" stopColor="#11161d" />
          </linearGradient>
          {/* 버튼 - 초록 */}
          <linearGradient id="gBtnGreen" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#059669" />
            <stop offset="100%" stopColor="#047857" />
          </linearGradient>
          {/* 버튼 - 빨강 */}
          <linearGradient id="gBtnRed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#dc2626" />
            <stop offset="100%" stopColor="#b91c1c" />
          </linearGradient>
          {/* 버튼 - 회색 */}
          <linearGradient id="gBtnGray" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#1e293b" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>
        </defs>

        {/* ── 배경 ── */}
        <rect width="1456" height="816" fill={C.bg} />

        {/* ════════════════════════════════
            LEFT PANELS
            ════════════════════════════════ */}

        {/* Purge Timer */}
        <rect x="14" y="8" width="126" height="100" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="77" y="23" fontSize="9" fontWeight="600" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">PURGE TIMER</text>
        <rect x="20" y="28" width="114" height="18" rx="3" fill={C.bg} stroke={C.line} />
        <text x="77" y="41" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">26373.0</text>
        <text x="77" y="58" fontSize="9" fontWeight="600" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">RE PURGE</text>
        <rect x="20" y="62" width="114" height="18" rx="3" fill={C.bg} stroke={C.line} />
        <text x="77" y="75" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">11.3</text>

        {/* SYNGAS 패널 */}
        <rect x="155" y="8" width="122" height="98" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" rx="4" />
        <text x="216" y="22" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.1em">SYNGAS</text>
        <circle cx="168" cy="34" r="5" fill={C.green} opacity=".7" />
        <circle cx="168" cy="50" r="5" fill={C.green} opacity=".7" />
        <circle cx="168" cy="66" r="5" fill={C.amber} opacity=".6" />
        <text x="216" y="38" fontSize="11" fontWeight="700" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{sg.toFixed(1)}</text>
        <text x="249" y="38" fontSize="8"  fill={C.text3}>raw</text>
        <text x="216" y="54" fontSize="10" fontWeight="600" fill={C.text2}>184.4</text>
        <text x="249" y="54" fontSize="8"  fill={C.text3}>°C</text>
        <text x="216" y="70" fontSize="10" fontWeight="600" fill={C.text2}>44.7</text>
        <text x="249" y="70" fontSize="8"  fill={C.text3}>kg/s</text>
        <text x="216" y="84" fontSize="8"  fill={C.text3}>9086.5 kg/m³</text>
        <text x="216" y="98" fontSize="8"  fontWeight="600" fill={C.green}>GC Normal</text>

        {/* N2 INJECT 패널 */}
        <rect x="155" y="185" width="122" height="72" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="216" y="199" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">N2 INJECT</text>
        <text x="216" y="215" fontSize="11" fontWeight="700" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{n2.toFixed(1)}</text>
        <text x="262" y="215" fontSize="8"  fill={C.text3}>raw</text>
        <text x="216" y="230" fontSize="10" fontWeight="600" fill={C.text2}>36.0</text>
        <text x="249" y="230" fontSize="8"  fill={C.text3}>°C</text>
        <text x="216" y="245" fontSize="10" fontWeight="600" fill={C.text2}>0.3</text>
        <text x="244" y="245" fontSize="8"  fill={C.text3}>kg/s</text>

        {/* Fuel Split 패널 */}
        <rect x="14" y="190" width="134" height="118" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="81" y="204" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">FUEL SPLIT</text>
        {[
          ['FSR',    '69.0', '%'],
          ['N2 FSR', '0.0',  '%'],
          ['SG FSR', '69.0', '%'],
          ['FX1',    '100.0','%'],
          ['SIM',    '128.4','s'],
          ['Eff',    efficiency, '%'],
        ].map(([label, val, unit], i) => (
          <g key={label}>
            <text x="22"  y={218 + i * 15} fontSize="8"  fill={C.text3}>{label}</text>
            <text x="82"  y={218 + i * 15} fontSize="10" fontWeight="600" fill={label === 'Eff' ? C.green : C.blue} fontFamily="'JetBrains Mono',monospace">{val}</text>
            <text x={112} y={218 + i * 15} fontSize="8"  fill={C.text3}>{unit}</text>
          </g>
        ))}

        {/* Generator / System 패널 */}
        <rect x="200" y="340" width="184" height="92" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="252" y="356" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">GENERATOR</text>
        <text x="324" y="356" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">SYSTEM</text>
        <line x1="287" y1="346" x2="287" y2="432" stroke={C.line} strokeWidth="1" />
        <text x="241" y="372" fontSize="10" fontWeight="600" fill={C.blue} fontFamily="'JetBrains Mono',monospace">17.9</text>
        <text x="269" y="372" fontSize="8"  fill={C.text3}>kV</text>
        <text x="298" y="372" fontSize="10" fontWeight="600" fill={C.blue} fontFamily="'JetBrains Mono',monospace">17.9</text>
        <text x="326" y="372" fontSize="8"  fill={C.text3}>kV</text>
        <text x="241" y="388" fontSize="10" fontWeight="600" fill={C.blue} fontFamily="'JetBrains Mono',monospace">60.0</text>
        <text x="269" y="388" fontSize="8"  fill={C.text3}>Hz</text>
        <text x="298" y="388" fontSize="10" fontWeight="600" fill={C.blue} fontFamily="'JetBrains Mono',monospace">60.0</text>
        <text x="326" y="388" fontSize="8"  fill={C.text3}>Hz</text>
        <rect x="201" y="396" width="70" height="26" rx="4" fill="url(#gBtnRed)" />
        <text x="236" y="413" fontSize="11" fontWeight="700" textAnchor="middle" fill="#fff">CLOSE</text>

        {/* MW / MVAR 출력 박스 */}
        <rect x="382" y="340" width="162" height="66" rx="4" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <rect x="386" y="348" width="154" height="22" rx="3" fill={C.bg} stroke={C.line} />
        <text x="463" y="363" fontSize="13" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{power.toFixed(1)} MW</text>
        <rect x="386" y="374" width="154" height="22" rx="3" fill={C.bg} stroke={C.line} />
        <text x="463" y="389" fontSize="13" fontWeight="700" textAnchor="middle" fill={C.text2} fontFamily="'JetBrains Mono',monospace">35.9 MVAR</text>
        <circle cx="364" cy="370" r="10" fill={C.surface3} stroke={C.line} />
        <text x="364" y="374" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3}>11</text>

        {/* ════════════════════════════════
            SYNGAS 메인 수평 배관
            ════════════════════════════════ */}
        <rect x="273" y="102" width="440" height="12" fill="url(#gPink)" rx="2" />
        <rect x="273" y="103" width="440" height="4"  fill="#f9a8d4" opacity=".25" />

        {/* VS4-11 밸브 */}
        <g transform="translate(305,98)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <line x1="10" y1="0"  x2="10" y2="-7"  stroke="#064e3b" strokeWidth="1.5" />
          <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5" />
          <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.text3}>VS4-11</text>
        </g>

        {/* VSR-11 밸브 */}
        <g transform="translate(380,98)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <line x1="10" y1="0"  x2="10" y2="-7"  stroke="#064e3b" strokeWidth="1.5" />
          <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5" />
          <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.text3}>VSR-11</text>
        </g>

        {/* FPSG2 센서 */}
        <circle cx="470" cy="108" r="8" fill={C.surface3} stroke={C.lineStr} strokeWidth="1" />
        <rect x="446" y="78" width="82" height="22" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="487" y="88"  fontSize="7" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">FPSG2</text>
        <text x="487" y="97"  fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">27.0 kg/cm²</text>
        <line x1="487" y1="100" x2="470" y2="108" stroke={C.line} strokeWidth="1" />

        {/* VGC-11A */}
        <g transform="translate(548,98)">
          <polygon points="0,0 20,10 0,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <text x="10" y="-3" fontSize="7" textAnchor="middle" fill={C.text3}>VGC-11A</text>
        </g>
        <rect x="526" y="124" width="72" height="24" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="562" y="134" fontSize="7" textAnchor="middle" fill={C.text3}>DM 45.9 %</text>
        <text x="562" y="144" fontSize="7" textAnchor="middle" fill={C.text3}>FB 45.9 %</text>

        {/* ── SYNGAS 직사각형 매니폴드 ── */}
        <rect x="600" y="55" width="12"  height="60" fill="url(#gPink)" />
        <rect x="600" y="55" width="220" height="12" fill="url(#gPink)" />
        <rect x="808" y="55" width="12"  height="60" fill="url(#gPink)" />
        <rect x="713" y="102" width="107" height="12" fill="url(#gPink)" />

        {/* VGC-11 */}
        <g transform="translate(596,60) rotate(90)">
          <polygon points="0,0 16,8 0,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <polygon points="16,0 0,8 16,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
        </g>
        <rect x="556" y="35" width="70" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="591" y="45" fontSize="7" textAnchor="middle" fill={C.text3}>VGC-11</text>
        <text x="591" y="53" fontSize="7" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">DM 76.0%</text>

        {/* VGC-12 */}
        <g transform="translate(804,60) rotate(90)">
          <polygon points="0,0 16,8 0,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <polygon points="16,0 0,8 16,16" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
        </g>
        <rect x="812" y="35" width="58" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="841" y="45" fontSize="7" textAnchor="middle" fill={C.text3}>VGC-12</text>

        {/* FPG3 */}
        <circle cx="760" cy="108" r="8" fill={C.surface3} stroke={C.lineStr} strokeWidth="1" />
        <rect x="730" y="122" width="80" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="770" y="131" fontSize="7" textAnchor="middle" fill={C.text3}>FPG 3</text>
        <text x="770" y="139" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">15.7 kg/cm²</text>

        {/* 포인트 10 */}
        <circle cx="870" cy="108" r="9" fill={C.surface3} stroke={C.lineStr} strokeWidth="1" />
        <text x="870" y="112" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>10</text>
        <rect x="848" y="88" width="60" height="16" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="878" y="99" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">15.7 kg/cm²</text>

        {/* ════════════════════════════════
            N2 수평 배관 (올리브)
            ════════════════════════════════ */}
        <rect x="273" y="222" width="440" height="12" fill="url(#gOlive)" rx="2" />
        <rect x="273" y="223" width="440" height="4"  fill="#bef264" opacity=".2" />

        {/* VS4-1 */}
        <g transform="translate(305,218)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <line x1="10" y1="0"  x2="10" y2="-7"  stroke="#064e3b" strokeWidth="1.5" />
          <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5" />
          <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.text3}>VS4-1</text>
        </g>

        {/* VSR-1 */}
        <g transform="translate(380,218)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <line x1="10" y1="0"  x2="10" y2="-7"  stroke="#064e3b" strokeWidth="1.5" />
          <line x1="10" y1="20" x2="10" y2="27" stroke="#064e3b" strokeWidth="1.5" />
          <text x="10" y="-10" fontSize="8" textAnchor="middle" fill={C.text3}>VSR-1</text>
        </g>

        {/* FPG2 */}
        <circle cx="466" cy="228" r="8" fill={C.surface3} stroke={C.lineStr} strokeWidth="1" />
        <rect x="440" y="242" width="68" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="474" y="251" fontSize="7" textAnchor="middle" fill={C.text3}>FPG2</text>
        <text x="474" y="259" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">0.0 kg/cm²</text>

        {/* VGC-1 */}
        <g transform="translate(516,218)">
          <polygon points="0,0 20,10 0,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.red} stroke="#7f1d1d" strokeWidth="1.2" />
          <text x="10" y="-3" fontSize="7" textAnchor="middle" fill={C.text3}>VGC-1</text>
        </g>
        <rect x="500" y="242" width="72" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="536" y="251" fontSize="7" textAnchor="middle" fill={C.text3}>DM -25.0%</text>
        <text x="536" y="259" fontSize="7" textAnchor="middle" fill={C.text3}>FB  0.1%</text>

        {/* ════════════════════════════════
            인렛 덕트 + IGV
            ════════════════════════════════ */}
        <rect x="580" y="200" width="78" height="180" fill={C.surface3} stroke={C.line} strokeWidth="1" rx="2" />

        {[
          { cy: 230, n: 12, label: 'INLET', val: '53.0 mmH₂O' },
          { cy: 260, n: 13, label: null, val: '30.1 °C' },
          { cy: 290, n: 14, label: null, val: '755.2 mmHg' },
        ].map(({ cy, n, label, val }) => (
          <g key={n}>
            <circle cx="600" cy={cy} r="9" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
            <text x="600" y={cy + 4} fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>{n}</text>
            {label && <text x="618" y={cy - 6} fontSize="7" fill={C.text3}>{label}</text>}
            <rect x="618" y={cy - 2} width="82" height="13" rx="2" fill={C.surface2} stroke={C.line} />
            <text x="659" y={cy + 8} fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{val}</text>
          </g>
        ))}

        {/* IGV 포인트 15 */}
        <circle cx="630" cy="362" r="9" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <text x="630" y="366" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>15</text>
        <rect x="590" y="375" width="106" height="40" rx="3" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <text x="643" y="387" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">IGV</text>
        <text x="643" y="400" fontSize="9" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">DM {igv.toFixed(1)} %</text>
        <text x="643" y="412" fontSize="9" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">FB {igv.toFixed(1)} %</text>

        {/* MAX VIB */}
        <rect x="590" y="420" width="106" height="28" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="643" y="432" fontSize="8" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">MAX VIB</text>
        <rect x="598" y="436" width="90" height="8" rx="2" fill={C.bg} />
        <rect x="598" y="436" width="58" height="8" rx="2" fill={C.amber} opacity=".7" />
        <text x="643" y="445" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.amber} fontFamily="'JetBrains Mono',monospace">6.7 mm/s</text>

        {/* ════════════════════════════════
            가스 터빈 본체
            ════════════════════════════════ */}

        {/* 메인 케이싱 */}
        <polygon points="660,145 1120,170 1120,500 660,520"
          fill="url(#gTurb)" stroke={C.lineStr} strokeWidth="2" />

        {/* 컴프레서 페이스 (타원) */}
        <ellipse cx="660" cy="332" rx="22" ry="188" fill="#1e293b" stroke={C.lineStr} strokeWidth="2" />
        <ellipse cx="660" cy="332" rx="16" ry="140" fill="#1a2332" stroke={C.line}    strokeWidth="1.5" />
        <ellipse cx="660" cy="332" rx="10" ry="90"  fill="#162030" stroke={C.line}    strokeWidth="1" />
        <ellipse cx="660" cy="332" rx="5"  ry="44"  fill="#1c2a3a" stroke={C.line}    strokeWidth="1" />

        {/* 블레이드 스테이지 수직선 */}
        {[740, 820, 910, 1010].map((x) => (
          <line key={x} x1={x} y1="151" x2={x} y2="513"
            stroke={C.lineStr} strokeWidth="1" strokeDasharray="5,4" opacity=".5" />
        ))}

        {/* 블레이드 디스크 */}
        {[
          [700, 175], [770, 155], [860, 132],
          [960, 108], [1060, 85],
        ].map(([cx, ry], i) => (
          <ellipse key={i} cx={cx} cy="332" rx={14 - i * 1.2} ry={ry}
            fill="#162030" stroke={C.lineStr} strokeWidth="1" opacity={.7 - i * 0.06} />
        ))}

        {/* 중심 샤프트 */}
        <rect x="660" y="322" width="460" height="20" rx="4" fill="#1a2332" stroke={C.lineStr} strokeWidth="1.5" />
        <rect x="660" y="326" width="460" height="12" rx="3" fill="#1e2d42" />

        {/* 연소캔 A/B/C/D */}
        {[
          [740, 175, 'A'],
          [740, 246, 'B'],
          [740, 418, 'C'],
          [740, 488, 'D'],
        ].map(([cx, cy, label]) => (
          <g key={String(label)}>
            <ellipse cx={cx as number} cy={cy as number} rx="38" ry="24"
              fill="url(#gCan)" stroke="#7f1d1d" strokeWidth="1.5" />
            <text x={cx as number} y={(cy as number) + 5} fontSize="12" fontWeight="700"
              textAnchor="middle" fill="#fff" opacity=".9">{label}</text>
            <rect x={(cx as number) - 16} y={cy as number} width="30" height="18"
              fill="#7f1d1d" stroke="#6b1515" strokeWidth="1" />
          </g>
        ))}

        {/* CPD 포인트 16 */}
        <circle cx="870" cy="195" r="9" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <text x="870" y="199" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>16</text>
        <rect x="840" y="170" width="80" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="880" y="179" fontSize="7" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">CPD</text>
        <text x="880" y="188" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">13.1 kg/cm²</text>

        {/* CTD 포인트 17 */}
        <circle cx="920" cy="380" r="9" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <text x="920" y="384" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>17</text>
        <rect x="930" y="370" width="74" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="967" y="379" fontSize="7" fontWeight="700" textAnchor="middle" fill={C.text3}>CTD</text>
        <text x="967" y="388" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.amber} fontFamily="'JetBrains Mono',monospace">391.5 °C</text>

        {/* λ 표시 */}
        <rect x="800" y="530" width="104" height="24" rx="4"
          fill={C.blueBg} stroke="rgba(59,130,246,0.35)" strokeWidth="1" />
        <text x="852" y="546" fontSize="13" fontWeight="700" textAnchor="middle"
          fill={C.blue} fontFamily="'JetBrains Mono',monospace">λ = {lambda.toFixed(2)}</text>

        {/* ════════════════════════════════
            CBV 밸브들 (터빈 오른쪽)
            ════════════════════════════════ */}
        {[
          [185, 'CBV#1 CLSD'],
          [207, 'CBV#3 CLSD'],
          [445, 'CBV#4 CLSD'],
          [467, 'CBV#2 CLSD'],
        ].map(([y, label]) => (
          <g key={String(label)}>
            <rect x="1126" y={y as number} width="78" height="16" rx="3"
              fill={C.greenBg} stroke="rgba(16,185,129,0.3)" strokeWidth="1" />
            <text x="1165" y={(y as number) + 11} fontSize="8" textAnchor="middle"
              fill={C.green} fontFamily="'JetBrains Mono',monospace">{label}</text>
          </g>
        ))}

        {/* ════════════════════════════════
            DGAN + 오른쪽 수치 패널
            ════════════════════════════════ */}
        <rect x="1214" y="8" width="228" height="110" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="1328" y="22" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.1em">DGAN</text>
        {[
          ['27.8',  'kg/cm²', 36],
          ['116.1', '°C',     50],
          ['30.6',  'kg/s',   64],
          ['3.7',   '% O2',   78],
        ].map(([val, unit, y]) => (
          <g key={String(y)}>
            <text x="1222" y={y as number} fontSize="10" fontWeight="600" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{val}</text>
            <text x={1222 + String(val).length * 6 + 8} y={y as number} fontSize="8" fill={C.text3}>{unit}</text>
          </g>
        ))}

        {/* 오른쪽 수치 패널 */}
        <rect x="1214" y="122" width="230" height="375" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />

        {/* 상단 수치 */}
        {[
          ['Speed Cntrl Ref', '102.9', '%',   136, C.blue],
          ['Speed in %',      '100.0', '%',   150, C.blue],
          ['Speed in RPM',    '3600',  'rpm', 164, C.blue],
          ['Ambient Temp',    '29.9',  '°C',  180, C.blue],
          ['Exh. Mass Flow',  '426.1', 'kg/s',196, C.blue],
          ['Lube Oil Temp',   '48.8',  '°C',  212, C.blue],
        ].map(([label, val, unit, y, clr], i) => (
          <g key={i}>
            {(y === 164 || y === 178 || y === 194) && (
              <circle cx="1219" cy={(y as number) - 6} r="8" fill={C.surface3} stroke={C.line} strokeWidth="1" />
            )}
            {(y === 164 || y === 178 || y === 194) && (
              <text x="1219" y={(y as number) - 2} fontSize="7" fontWeight="700" textAnchor="middle" fill={C.text3}>
                {y === 164 ? '19' : y === 178 ? '20' : '21'}
              </text>
            )}
            <text x={(y === 164 || y === 178 || y === 194) ? 1232 : 1220} y={y as number}
              fontSize="8" fill={C.text3}>{label}</text>
            <text x="1368" y={y as number} fontSize="9" fontWeight="600" fill={clr as string}
              fontFamily="'JetBrains Mono',monospace">{val}</text>
            <text x="1400" y={y as number} fontSize="7" fill={C.text3}>{unit}</text>
          </g>
        ))}

        <line x1="1216" y1="220" x2="1440" y2="220" stroke={C.line} strokeWidth="1" />

        {/* 중단: FSR / IGV / CPR / Vib */}
        {[
          ['FSR',     '69.0',            '% ',   234, C.blue],
          ['IGV',     igv.toFixed(1),    '°',    248, C.blue],
          ['CPR',     '13.8',            'ratio', 262, C.blue],
          ['Max Vib', '6.7',             'mm/s', 276, C.amber],
        ].map(([label, val, unit, y, clr]) => (
          <g key={String(label)}>
            <text x="1220" y={y as number} fontSize="8" fill={C.text3}>{label}</text>
            <text x="1368" y={y as number} fontSize="9" fontWeight="600" fill={clr as string}
              fontFamily="'JetBrains Mono',monospace">{val}</text>
            <text x="1400" y={y as number} fontSize="7" fill={C.text3}>{unit}</text>
          </g>
        ))}

        <line x1="1216" y1="284" x2="1440" y2="284" stroke={C.line} strokeWidth="1" />

        {/* 하단: Exh Spread / 배출 / 출력 */}
        {[
          ['Exh. Spread Lim', '93.5',           '°C',  298, C.blue,  false],
          ['Exh. Temp',       exhaust.toFixed(1),'°C',  312, C.amber, true ],
          ['Exh. Spread #1',  '30.9',            '°C',  326, C.blue,  false],
          ['Exh. Spread #2',  '30.1',            '°C',  340, C.blue,  false],
          ['Exh. Spread #3',  '29.2',            '°C',  354, C.blue,  false],
          ['Exh. Spread #4',  '26.2',            '°C',  368, C.blue,  false],
        ].map(([label, val, unit, y, clr, isPoint]) => (
          <g key={String(label)}>
            {isPoint && (
              <circle cx="1219" cy={(y as number) - 5} r="8" fill={C.surface3} stroke={C.line} strokeWidth="1" />
            )}
            {isPoint && (
              <text x="1219" y={(y as number) - 1} fontSize="7" fontWeight="700" textAnchor="middle" fill={C.text3}>22</text>
            )}
            <text x={isPoint ? 1232 : 1220} y={y as number} fontSize="8" fill={C.text3}>{label}</text>
            <text x="1368" y={y as number} fontSize="9" fontWeight="600" fill={clr as string}
              fontFamily="'JetBrains Mono',monospace">{val}</text>
            <text x="1400" y={y as number} fontSize="7" fill={C.text3}>{unit}</text>
          </g>
        ))}

        <line x1="1216" y1="376" x2="1440" y2="376" stroke={C.line} strokeWidth="1" />

        {/* NOx / CO / Efficiency / Power */}
        <text x="1220" y="390" fontSize="8" fill={C.text3}>NOx</text>
        <text x="1368" y="390" fontSize="9" fontWeight="700" fill={noxColor}
          fontFamily="'JetBrains Mono',monospace">{nox.toFixed(1)}</text>
        <text x="1400" y="390" fontSize="7" fill={C.text3}>ppm</text>

        <text x="1220" y="404" fontSize="8" fill={C.text3}>CO</text>
        <text x="1368" y="404" fontSize="9" fontWeight="600" fill={C.blue}
          fontFamily="'JetBrains Mono',monospace">{co.toFixed(1)}</text>
        <text x="1400" y="404" fontSize="7" fill={C.text3}>ppm</text>

        <text x="1220" y="418" fontSize="8" fill={C.text3}>Efficiency</text>
        <text x="1368" y="418" fontSize="9" fontWeight="600" fill={C.green}
          fontFamily="'JetBrains Mono',monospace">{efficiency}</text>
        <text x="1400" y="418" fontSize="7" fill={C.text3}>%</text>

        <text x="1220" y="432" fontSize="8" fill={C.text3}>Comb Reference</text>
        <text x="1368" y="432" fontSize="9" fontWeight="600" fill={C.blue}
          fontFamily="'JetBrains Mono',monospace">92.2</text>

        <text x="1220" y="446" fontSize="8" fill={C.text3}>Power Output</text>
        <text x="1368" y="446" fontSize="9" fontWeight="700" fill={C.blue}
          fontFamily="'JetBrains Mono',monospace">{power.toFixed(1)}</text>
        <text x="1400" y="446" fontSize="7" fill={C.text3}>MW</text>

        <text x="1220" y="460" fontSize="8" fill={C.text3}>MVAR</text>
        <text x="1368" y="460" fontSize="9" fontWeight="600" fill={C.text2}
          fontFamily="'JetBrains Mono',monospace">35.9</text>
        <text x="1400" y="460" fontSize="7" fill={C.text3}>MVAR</text>

        {/* NPNJ2 / VS7-1 / VNC-1 */}
        <rect x="1050" y="80" width="66" height="22" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="1083" y="90"  fontSize="7" textAnchor="middle" fill={C.text3}>NPNJ2</text>
        <text x="1083" y="99"  fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">16.0 kg/cm²</text>
        <rect x="1083" y="102" width="8" height="88" fill="url(#gBlue)" rx="2" />
        <g transform="translate(1078,128)">
          <polygon points="0,0 16,8 0,16" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="16,0 0,8 16,16" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <text x="8" y="-3" fontSize="7" textAnchor="middle" fill={C.text3}>VS7-1</text>
        </g>
        <rect x="1100" y="175" width="62" height="32" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="1131" y="186" fontSize="7" textAnchor="middle" fill={C.text3}>VNC-1</text>
        <text x="1131" y="196" fontSize="7" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">DM 28.7%</text>
        <text x="1131" y="205" fontSize="7" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">FB 28.4%</text>

        {/* FPSG3 */}
        <circle cx="1030" cy="228" r="8" fill={C.surface3} stroke={C.lineStr} strokeWidth="1" />
        <rect x="995" y="238" width="78" height="20" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="1034" y="247" fontSize="7" textAnchor="middle" fill={C.text3}>FPSG 3</text>
        <text x="1034" y="256" fontSize="8" fontWeight="600" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">15.7 kg/cm²</text>

        {/* ════════════════════════════════
            N2 하단 배관 (앰버 — dilution)
            ════════════════════════════════ */}
        <rect x="155" y="558" width="122" height="66" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="216" y="572" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">N2 DILUT</text>
        <text x="216" y="588" fontSize="11" fontWeight="700" textAnchor="middle" fill={C.blue} fontFamily="'JetBrains Mono',monospace">{n2.toFixed(1)}</text>
        <text x="216" y="602" fontSize="8" textAnchor="middle" fill={C.text3}>32.4 °C</text>
        <text x="216" y="614" fontSize="8" textAnchor="middle" fill={C.text3}>0.3 kg/s</text>

        <rect x="273" y="575" width="520" height="12" fill="url(#gRed)" rx="2" />
        <rect x="273" y="576" width="520" height="4"  fill="#fde68a" opacity=".2" />

        {/* VS3-1 */}
        <g transform="translate(440,571)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <text x="10" y="-3" fontSize="8" textAnchor="middle" fill={C.text3}>VS3-1</text>
        </g>

        {/* VA4-1 */}
        <g transform="translate(620,571)">
          <polygon points="0,0 20,10 0,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <polygon points="20,0 0,10 20,20" fill={C.green} stroke="#064e3b" strokeWidth="1.2" />
          <text x="10" y="-3" fontSize="8" textAnchor="middle" fill={C.text3}>VA4-1</text>
        </g>

        {/* 수직 상승 → IBH */}
        <rect x="710" y="450" width="12" height="137" fill="url(#gRed)" rx="2" />
        <rect x="710" y="451" width="4"  height="137" fill="#fde68a" opacity=".15" />
        <circle cx="716" cy="468" r="9" fill={C.surface2} stroke={C.lineStr} strokeWidth="1" />
        <text x="716" y="472" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text2}>18</text>
        <rect x="680" y="478" width="106" height="28" rx="3" fill={C.surface2} stroke={C.line} />
        <text x="733" y="490" fontSize="7" textAnchor="middle" fill={C.text3}>IBH  DM -25.0%</text>
        <text x="733" y="500" fontSize="7" textAnchor="middle" fill={C.text3}>FB  0.2%</text>
        <text x="718" y="598" fontSize="8" fill={C.text3}>-0.1 %</text>

        {/* ════════════════════════════════
            하단 제어 바
            ════════════════════════════════ */}
        <rect x="0" y="640" width="1456" height="176" fill={C.surface} />
        <line x1="0" y1="640" x2="1456" y2="640" stroke={C.lineStr} strokeWidth="1" />

        {/* Status 패널 */}
        <rect x="8" y="650" width="252" height="158" fill={C.surface2} stroke={C.line} strokeWidth="1" rx="4" />
        <text x="60" y="665" fontSize="9" fontWeight="700" fill={C.text3} letterSpacing="0.1em">STATUS</text>
        <rect x="88" y="654" width="166" height="18" rx="3"
          fill={C.greenBg} stroke="rgba(16,185,129,0.3)" strokeWidth="1" />
        <text x="171" y="666" fontSize="10" fontWeight="700" textAnchor="middle"
          fill={C.green} fontFamily="'JetBrains Mono',monospace">RUNNING</text>
        <rect x="88" y="675" width="166" height="14" rx="3" fill={C.bg} stroke={C.line} />
        <text x="171" y="685" fontSize="8" textAnchor="middle" fill={C.text3}>NO STATUS</text>

        {[
          ['Startup Status', 'PART LOAD',    C.blue],
          ['Turbine Status', 'EXT LOAD CTRL',C.blue],
          ['Control Mode',   'AUTO',          C.blue],
          ['Fuel Control',   'CPR LIMIT',     C.amber],
          ['Misc. Status',   'NO STATUS',     C.text3],
          ['IGV Control',    'MACH_NUM',      C.blue],
          ['Speed Level',    '>95% - 14HS',   C.text3],
        ].map(([label, val, clr], i) => (
          <g key={String(label)}>
            <text x="14"  y={702 + i * 14} fontSize="8" fill={C.text3}>{label}</text>
            <text x="120" y={702 + i * 14} fontSize="8" fontWeight="600" fill={clr as string}
              fontFamily="'JetBrains Mono',monospace">{val}</text>
          </g>
        ))}

        {/* Mode Select */}
        <rect x="270" y="648" width="84" height="12" rx="2" fill={C.bg} />
        <text x="312" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">MODE SELECT</text>
        {['Off', 'Crank', 'Fire'].map((label, i) => (
          <g key={label}>
            <rect x="270" y={663 + i * 22} width="84" height="18" rx="3"
              fill={C.bg} stroke={C.line} strokeWidth="1" />
            <text x="312" y={675 + i * 22} fontSize="9" textAnchor="middle" fill={C.text3}>{label}</text>
          </g>
        ))}
        <rect x="270" y="729" width="84" height="18" rx="3" fill="url(#gBtnRed)" />
        <text x="312" y="741" fontSize="9" fontWeight="700" textAnchor="middle" fill="#fff">Auto</text>
        <rect x="270" y="750" width="84" height="18" rx="3" fill={C.bg} stroke={C.line} strokeWidth="1" />
        <text x="312" y="762" fontSize="9" textAnchor="middle" fill={C.text3}>Remote</text>

        {/* Master Control */}
        <rect x="364" y="648" width="84" height="12" rx="2" fill={C.bg} />
        <text x="406" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">MASTER CTRL</text>
        <rect x="364" y="663" width="84" height="24" rx="3" fill="url(#gBtnGreen)" />
        <text x="406" y="679" fontSize="10" fontWeight="700" textAnchor="middle" fill="#fff">Start</text>
        <rect x="364" y="690" width="84" height="24" rx="3" fill={C.bg} stroke={C.line} strokeWidth="1" />
        <text x="406" y="706" fontSize="10" fontWeight="600" textAnchor="middle" fill={C.text3}>Stop</text>

        {/* Load Select */}
        <rect x="458" y="648" width="100" height="12" rx="2" fill={C.bg} />
        <text x="508" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">LOAD SELECT</text>
        {[
          ['Base Load',     C.greenBg, 'rgba(16,185,129,0.3)', C.green],
          ['Preselect Load',C.greenBg, 'rgba(16,185,129,0.3)', C.green],
          ['Ext Load Cntrl','rgba(239,68,68,0.12)','rgba(239,68,68,0.35)', C.red],
          ['SG Follow',     C.greenBg, 'rgba(16,185,129,0.3)', C.green],
        ].map(([label, bg, border, clr], i) => (
          <g key={String(label)}>
            <rect x="458" y={663 + i * 22} width="100" height="18" rx="3"
              fill={bg as string} stroke={border as string} strokeWidth="1" />
            <text x="508" y={675 + i * 22} fontSize="8" fontWeight="600"
              textAnchor="middle" fill={clr as string}>{label}</text>
          </g>
        ))}

        {/* Fuel Select */}
        <rect x="568" y="648" width="100" height="12" rx="2" fill={C.bg} />
        <text x="618" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.08em">FUEL SELECT</text>
        <rect x="568" y="663" width="100" height="18" rx="3" fill={C.bg} stroke={C.line} strokeWidth="1" />
        <text x="618" y="675" fontSize="9" textAnchor="middle" fill={C.text3}>Gas</text>
        <rect x="568" y="684" width="100" height="18" rx="3"
          fill={C.blueBg} stroke="rgba(59,130,246,0.35)" strokeWidth="1" />
        <text x="618" y="696" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.blue}>Syngas</text>

        {/* MW Control */}
        <rect x="678" y="648" width="178" height="130" rx="4"
          fill={C.surface2} stroke={C.line} strokeWidth="1" />
        <text x="738" y="663" fontSize="9" fontWeight="700" textAnchor="middle"
          fill={C.text3} letterSpacing="0.08em">MW CONTROL</text>
        <text x="800" y="663" fontSize="9" fontWeight="700" textAnchor="middle"
          fill={C.text3} letterSpacing="0.08em">SETPOINT</text>
        <line x1="678" y1="668" x2="856" y2="668" stroke={C.line} strokeWidth="1" />
        <text x="692" y="684" fontSize="8" fill={C.text3}>Setpoint</text>
        <rect x="752" y="672" width="78" height="18" rx="3"
          fill={C.blueBg} stroke="rgba(59,130,246,0.35)" strokeWidth="1" />
        <text x="791" y="685" fontSize="10" fontWeight="700" textAnchor="middle"
          fill={C.blue} fontFamily="'JetBrains Mono',monospace">170.4 MW</text>
        <text x="692" y="706" fontSize="8" fill={C.text3}>MEGAWATTS</text>
        <rect x="752" y="694" width="78" height="18" rx="3" fill={C.bg} stroke={C.line} />
        <text x="791" y="707" fontSize="10" fontWeight="700" textAnchor="middle"
          fill={C.blue} fontFamily="'JetBrains Mono',monospace">{power.toFixed(1)} MW</text>

        {/* Gen Control Mode */}
        <rect x="866" y="648" width="100" height="12" rx="2" fill={C.bg} />
        <text x="916" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">GEN CONTROL</text>
        <rect x="866" y="663" width="100" height="18" rx="3"
          fill={C.blueBg} stroke="rgba(59,130,246,0.35)" strokeWidth="1" />
        <text x="916" y="675" fontSize="9" fontWeight="700" textAnchor="middle" fill={C.blue}>Voltage</text>
        {['PF', 'VAR'].map((label, i) => (
          <g key={label}>
            <rect x="866" y={684 + i * 22} width="100" height="18" rx="3"
              fill={C.bg} stroke={C.line} strokeWidth="1" />
            <text x="916" y={696 + i * 22} fontSize="9" fontWeight="600"
              textAnchor="middle" fill={C.text3}>{label}</text>
          </g>
        ))}

        {/* Speed/Load Ctrl */}
        <rect x="976" y="648" width="100" height="12" rx="2" fill={C.bg} />
        <text x="1026" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">SPD/LOAD CTRL</text>
        {['Raise', 'Lower'].map((label, i) => (
          <g key={label}>
            <rect x="976" y={663 + i * 22} width="100" height="18" rx="3"
              fill={C.greenBg} stroke="rgba(16,185,129,0.3)" strokeWidth="1" />
            <text x="1026" y={675 + i * 22} fontSize="9" fontWeight="600"
              textAnchor="middle" fill={C.green}>{label}</text>
          </g>
        ))}

        {/* Syngas Control */}
        <rect x="1086" y="648" width="100" height="12" rx="2" fill={C.bg} />
        <text x="1136" y="657" fontSize="8" fontWeight="700" textAnchor="middle" fill={C.text3} letterSpacing="0.06em">SYNGAS CTRL</text>
        {['Raise', 'Lower'].map((label, i) => (
          <g key={label}>
            <rect x="1086" y={663 + i * 22} width="100" height="18" rx="3"
              fill={C.blueBg} stroke="rgba(59,130,246,0.25)" strokeWidth="1" />
            <text x="1136" y={675 + i * 22} fontSize="9" fontWeight="600"
              textAnchor="middle" fill={C.blue}>{label}</text>
          </g>
        ))}

        {/* 우측 버튼들 */}
        {['Startup Trend', 'Master Reset', 'Diagnostic Reset'].map((label, i) => (
          <g key={label}>
            <rect x="1312" y={653 + i * 26} width="132" height="20" rx="3"
              fill={C.surface2} stroke={C.line} strokeWidth="1" />
            <text x="1378" y={667 + i * 26} fontSize="9" textAnchor="middle" fill={C.text2}>{label}</text>
          </g>
        ))}
      </svg>
    </div>
  )
}
