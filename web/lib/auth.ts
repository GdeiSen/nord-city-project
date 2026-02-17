const TOKEN_KEY = "nord_city_token"
const USER_KEY = "nord_city_user"

export interface AuthUser {
  id: number
  username?: string
  first_name?: string
  last_name?: string
  role?: number
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return
  localStorage.setItem(TOKEN_KEY, token)
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function setUser(user: AuthUser | null): void {
  if (typeof window === "undefined") return
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  } else {
    localStorage.removeItem(USER_KEY)
  }
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

export function logout(): void {
  if (typeof window === "undefined") return
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
