export interface MissingRole {
  role: string
  id: string
}
export interface RoleConflict {
  id: string
  roles: string[]
}

export interface BuildValidationDetail {
  missing: MissingRole[]
  conflicts: RoleConflict[]
}

// erasableSyntaxOnly: true 호환 형태
export class BuildValidationError extends Error {
  readonly detail: BuildValidationDetail

  constructor(detail: BuildValidationDetail) {
    super(BuildValidationError.format(detail))
    this.name = 'BuildValidationError'
    this.detail = detail
  }

  static format(detail: BuildValidationDetail): string {
    const lines: string[] = []
    for (const m of detail.missing) {
      lines.push(`  missing: role="${m.role}" id="${m.id}" not in SVG`)
    }
    for (const c of detail.conflicts) {
      lines.push(`  conflict: id="${c.id}" used by roles ${c.roles.join(', ')}`)
    }
    return `Role mapping validation FAILED\n${lines.join('\n')}`
  }

  toReport(): string {
    return BuildValidationError.format(this.detail)
  }
}
