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
