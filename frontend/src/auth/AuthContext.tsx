import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { api, setToken, ApiError } from "../api/client"
import type { User } from "../api/types"

interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  // Starts true: on first load we don't yet know whether a stored token
  // is still valid, so routes must wait for this to resolve before
  // deciding to redirect to /login -- otherwise a page refresh would
  // always briefly bounce a logged-in user to the login screen.
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<User>("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const tokens = await api.post<TokenResponse>("/auth/login", { email, password })
    setToken(tokens.access_token)
    const me = await api.get<User>("/auth/me")
    setUser(me)
  }

  function logout() {
    setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider")
  return ctx
}

export { ApiError }
