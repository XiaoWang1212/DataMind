export interface AuthUser {
  id: number
  email: string
  displayName: string | null
  isAdmin: boolean
}

async function parseAuthResponse (response: Response): Promise<Record<string, unknown>> {
  const result = (await response.json()) as Record<string, unknown>
  if (!response.ok || !result.success) {
    throw new Error(result.error ? String(result.error) : `HTTP ${response.status}`)
  }
  return result
}

function toAuthUser (raw: Record<string, unknown>): AuthUser {
  return {
    id: raw.id as number,
    email: raw.email as string,
    displayName: (raw.displayName as string | null | undefined) ?? null,
    isAdmin: Boolean(raw.isAdmin),
  }
}

export async function register (email: string, password: string, displayName: string): Promise<void> {
  const response = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password, displayName }),
  })
  await parseAuthResponse(response)
}

export async function login (email: string, password: string): Promise<void> {
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  })
  await parseAuthResponse(response)
}

export async function logout (): Promise<void> {
  const response = await fetch('/api/auth/logout', {
    method: 'POST',
    credentials: 'include',
  })
  await parseAuthResponse(response)
}

export async function fetchCurrentUser (): Promise<AuthUser | null> {
  const response = await fetch('/api/auth/me', { credentials: 'include' })
  if (response.status === 401) {
    return null
  }
  const result = await parseAuthResponse(response)
  return toAuthUser(result.result as Record<string, unknown>)
}

export async function loginWithGoogle (idToken: string): Promise<void> {
  const response = await fetch('/api/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ idToken }),
  })
  await parseAuthResponse(response)
}

export async function forgotPassword (email: string): Promise<void> {
  const response = await fetch('/api/auth/forgot-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email }),
  })
  await parseAuthResponse(response)
}

export async function resetPassword (token: string, password: string): Promise<void> {
  const response = await fetch('/api/auth/reset-password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ token, password }),
  })
  await parseAuthResponse(response)
}
