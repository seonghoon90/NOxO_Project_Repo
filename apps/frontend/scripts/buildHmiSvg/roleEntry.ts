export type RoleKind =
  | 'kpi-card'
  | 'kpi-box'
  | 'kpi-value-remove'
  | 'flow-group'
  | 'cascade-step'
  | 'flame-anchor'

export interface RoleEntry {
  id: string
  kind: RoleKind
}
