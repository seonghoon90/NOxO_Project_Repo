import { useRef, type CSSProperties } from 'react'
import Schematic from './schematic.svg?react'
import { KpiTexts } from './KpiTexts'
import { FlameOverlay } from './FlameOverlay'
import { computeKpiStates } from './kpiState'
import { getFlowAnimationVars } from './flowVarsMap'
import { useCascadeAnimation } from './useCascadeAnimation'
import { cssVarsFromProps, type SchematicInputs } from './cssVarsFromProps'
import { clamp, finiteOr, normalize } from './numericHelpers'
import { VIEW_BOX } from './schematic-roles'
import styles from './HmiSchematic.module.css'

export interface HmiSchematicProps extends SchematicInputs {}

export function HmiSchematic(props: HmiSchematicProps) {
  const rootRef = useRef<HTMLDivElement>(null)

  const cssVars = cssVarsFromProps(props)
  const kpi = computeKpiStates({
    nox: props.nox,
    ttxm: props.ttxm,
    dwatt: props.power,
    lambda: props.lambda,
  })

  const fuelRatio = clamp(
    normalize(finiteOr(props.syngasFlow.value, props.syngasFlow.min), props.syngasFlow.min, props.syngasFlow.max),
    0,
    1,
  )
  const noxRatio = clamp(finiteOr(props.nox, 0) / 50, 0, 1)
  const airRatio = clamp(
    normalize(finiteOr(props.igvOpening.value, props.igvOpening.min), props.igvOpening.min, props.igvOpening.max),
    0,
    1,
  )
  const flowVars = getFlowAnimationVars({ fuel: fuelRatio, nox: noxRatio, air: airRatio })

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
      <svg
        className={styles.overlay}
        viewBox={`0 0 ${VIEW_BOX.width} ${VIEW_BOX.height}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <KpiTexts nox={props.nox} ttxm={props.ttxm} dwatt={props.power} lambda={props.lambda} />
        <FlameOverlay />
      </svg>
    </div>
  )
}
