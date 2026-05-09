export interface FlowInputs {
  fuel: number  // 0~1
  nox: number   // 0~1
  air: number   // 0~1
}

export type FlowVars = {
  '--flow-fuel-duration': string
  '--flow-fuel-state': 'running' | 'paused'
  '--flow-nox-duration': string
  '--flow-nox-state': 'running' | 'paused'
  '--flow-air-duration': string
  '--flow-air-state': 'running' | 'paused'
  '--flow-cards-duration': string
  '--flow-cards-state': 'running' | 'paused'
}

interface Stage {
  duration: string
  state: 'running' | 'paused'
}

function stageOf(ratio: number): Stage {
  if (!Number.isFinite(ratio) || ratio < 0.10) return { duration: '1.2s', state: 'paused' }
  if (ratio < 0.40) return { duration: '2.5s', state: 'running' }
  if (ratio < 0.75) return { duration: '1.2s', state: 'running' }
  return { duration: '0.5s', state: 'running' }
}

export function getFlowAnimationVars(inputs: FlowInputs): FlowVars {
  const fuel = stageOf(inputs.fuel)
  const nox = stageOf(inputs.nox)
  const air = stageOf(inputs.air)
  return {
    '--flow-fuel-duration': fuel.duration,
    '--flow-fuel-state': fuel.state,
    '--flow-nox-duration': nox.duration,
    '--flow-nox-state': nox.state,
    '--flow-air-duration': air.duration,
    '--flow-air-state': air.state,
    '--flow-cards-duration': '1.2s',
    '--flow-cards-state': 'running',
  }
}
