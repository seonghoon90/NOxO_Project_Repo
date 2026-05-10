import { BuildValidationError, type MissingRole, type RoleConflict } from './BuildValidationError'
import type { RoleEntry } from './roleEntry'

export function validateRoles(
  originalIds: Set<string>,
  roleMap: Readonly<Record<string, Readonly<RoleEntry>>>,
): void {
  const missing: MissingRole[] = []
  const conflicts: RoleConflict[] = []
  const idToRole = new Map<string, string>()

  for (const [role, entry] of Object.entries(roleMap)) {
    if (!originalIds.has(entry.id)) {
      missing.push({ role, id: entry.id })
    }
    if (idToRole.has(entry.id)) {
      conflicts.push({ id: entry.id, roles: [idToRole.get(entry.id)!, role] })
    } else {
      idToRole.set(entry.id, role)
    }
  }

  if (missing.length > 0 || conflicts.length > 0) {
    throw new BuildValidationError({ missing, conflicts })
  }
}
