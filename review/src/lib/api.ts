// Every read goes to this Worker's own /api, behind the same Cloudflare Access application
// as the pages. Nothing here holds a key: the Access cookie travels with the request.
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string
  ) {
    super(message)
  }
}

export async function api<T>(path: string): Promise<T> {
  const answer = await fetch(`/api${path}`, {
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
  })
  if (!answer.ok) throw new ApiError(answer.status, await answer.text())
  return (await answer.json()) as T
}

export type Me = { email: string }

export type Environment = {
  name: 'staging' | 'production'
  host: string
  store: 'connected' | 'not-connected'
}

export type Overview = {
  environment: Environment['name']
  current: {
    version: string
    loaded_at: string
    counts: Record<string, number>
  } | null
  versions: { version: string; loaded_at: string; current: boolean }[]
  // What the host serves, read from its /build-revision.txt and /bundle-version.txt.
  published: {
    host: string
    revision: string | null
    bundle: string | null
  } | null
  tables: { name: string; rows: number | null }[]
}

export type ModelState =
  | {
      status: 'present'
      rows: number
      inCurrent?: number | null
      version?: string | null
      schema?: boolean
    }
  | { status: 'absent'; reason: string }
  | { status: 'unavailable' }

export type Model = {
  id: string
  kind: 'table' | 'page-model'
  name: string
  area: string
  table?: string
  model?: string
  migration?: string
  source?: string
  versioned?: boolean
  hidden?: string[]
  environments: Record<string, ModelState>
}

export type EnvironmentState = {
  name: string
  label: string
  store: string
  readable: boolean
  reason?: string
  bundle?: { version: string; loaded_at: string } | null
  unlisted?: string[]
}

export type Inventory = {
  areas: string[]
  environments: EnvironmentState[]
  models: Model[]
}

export type Rows = {
  columns: { name: string; key: boolean }[]
  hiddenColumns?: string[]
  rows: Record<string, unknown>[]
  total: number
  offset: number
  limit: number
  version?: string | null
  absent?: boolean
}

export type PageRecord = {
  model: string
  key: string
  version: string
  loaded_at: string
  body: unknown
  schema: { properties?: Record<string, { description?: string; type?: unknown }> } | null
  manifest: {
    made_at: string | null
    checksum: string | null
    lab_commit: string | null
    snapshot: unknown
  } | null
}
