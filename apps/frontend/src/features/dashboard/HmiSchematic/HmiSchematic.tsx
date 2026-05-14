import { useRef, type CSSProperties } from 'react'
import Schematic from './schematic.svg?react'
import { KpiTexts } from './KpiTexts'
import { SparkLines } from './SparkLines'
import { SmokeCanvas } from './SmokeCanvas'
import { LegendTexts } from './LegendTexts'
import { LabelTexts } from './LabelTexts'
import { computeKpiStates, type KpiThresholds } from './kpiState'
import { getFlowAnimationVars } from './flowVarsMap'
import { useCascadeAnimation } from './useCascadeAnimation'
import { cssVarsFromProps, type SchematicInputs } from './cssVarsFromProps'
import type { VariableConfig } from '../mockConsole'
import { clamp, finiteOr, normalize } from './numericHelpers'
import { VIEW_BOX } from './schematic-roles'
import type { MetricPoint } from '../mockConsole'
import styles from './HmiSchematic.module.css'

export interface HmiSchematicProps extends SchematicInputs {
  history?: ReadonlyArray<MetricPoint>
  kpiThresholds: KpiThresholds
}

export function HmiSchematic(props: HmiSchematicProps) {
  const rootRef = useRef<HTMLDivElement>(null)

  const cssVars = cssVarsFromProps(props)
  const kpi = computeKpiStates(
    {
      nox: props.nox,
      ttxm: props.ttxm,
      dwatt: props.power,
      lambda: props.lambda,
    },
    props.kpiThresholds,
  )

  // 각 계통 파이프 속도는 해당 라인에 연결된 변수들의 단순 평균 ratio로 결정
  const fuelRatio = avgRatio([
    props.syngasFlow, props.syngasSrv, props.syngasGcv1, props.syngasGcv1a, props.syngasGcv2,
  ])
  // flow-nox(초록) 라인은 도면 의미상 "질소 계통"
  const n2Ratio = avgRatio([props.n2Flow, props.n2Valve1])
  const airRatio = avgRatio([props.igvOpening, props.ibhValve])
  // SmokeCanvas 강도는 NOx ppm 기반 — 임계 30ppm 근처가 현재 화면 수준이 되도록 max 100ppm 기준
  const noxRatio = clamp(finiteOr(props.nox, 0) / 100, 0, 1)
  const flowVars = getFlowAnimationVars({ fuel: fuelRatio, nox: n2Ratio, air: airRatio })

  useCascadeAnimation(props.n2Flow.value, rootRef)

  const style = {
    ...cssVars,
    ...flowVars,
  } as CSSProperties

  return (
    <div
      ref={rootRef}
      className={styles.root}
      style={style}
      data-testid="hmi-schematic-root"
      data-kpi-nox={kpi.nox}
      data-kpi-ttxm={kpi.ttxm}
      data-kpi-dwatt={kpi.dwatt}
      data-kpi-lambda={kpi.lambda}
    >
      <Schematic width="100%" height="100%" preserveAspectRatio="xMidYMid meet" />
      <SmokeCanvas intensity={noxRatio} />
      <svg
        className={styles.overlay}
        viewBox={`0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <KpiTexts
          nox={props.nox}
          ttxm={props.ttxm}
          dwatt={props.power}
          lambda={props.lambda}
          syngas={props.syngasFlow.value}
          fsagr={props.syngasSrv.value}
          fsag11={props.syngasGcv1.value}
          fsag11a={props.syngasGcv1a.value}
          fsag12={props.syngasGcv2.value}
          nicvs1={props.n2Valve1.value}
          nqj={props.n2Flow.value}
          csbhx={props.ibhValve.value}
          csgv={props.igvOpening.value}
          nqkr3={props.n2Offset.value}
        />
        {/* 굴뚝(stack) — EXHAUST 박스 윗변 중앙. 박스 fill/stroke와 동일 톤 */}
        <g data-role="exhaust-stack" fill="url(#paint8_linear_1_2)" stroke="#b9d4e8" strokeWidth={1}>
          <path d="M970 210 L972 196 L1000 196 L1002 210 Z" />
        </g>
        {/* 박스 우측면(1012,283) → 카드 점선 분기점(1068,283) 가로 점선 */}
        <line
          x1={1012}
          y1={282.86}
          x2={1068}
          y2={282.86}
          stroke="#6e879c"
          strokeWidth={1}
          strokeDasharray="3 4"
          data-role="exhaust-bridge"
        />
        <SparkLines history={props.history ?? []} />
        <LegendTexts />
        <LabelTexts />
      </svg>
    </div>
  )
}

function avgRatio(cfgs: ReadonlyArray<VariableConfig>): number {
  const sum = cfgs.reduce((acc, cfg) => {
    const r = normalize(finiteOr(cfg.value, cfg.min), cfg.min, cfg.max)
    return acc + clamp(r, 0, 1)
  }, 0)
  return cfgs.length > 0 ? sum / cfgs.length : 0
}
