import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"
import { api, setToken, ApiError } from "../api/client"
import { Button, ErrorNote, Input, Label } from "../components/ui"

interface TokenResponse {
  access_token: string
  refresh_token: string
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState<"login" | "signup">("login")

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [tenantName, setTenantName] = useState("")
  const [fullName, setFullName] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === "login") {
        await login(email, password)
      } else {
        const tokens = await api.post<TokenResponse>("/auth/register", {
          tenant_name: tenantName,
          email,
          password,
          full_name: fullName || null,
        })
        setToken(tokens.access_token)
        await login(email, password)
      }
      navigate("/")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="font-semibold text-lg">Support Agent Console</div>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            {mode === "login" ? "Sign in to your workspace" : "Create a new workspace"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "signup" && (
            <div>
              <Label>Company name</Label>
              <Input
                value={tenantName}
                onChange={(e) => setTenantName(e.target.value)}
                placeholder="Acme Corp"
                required
              />
            </div>
          )}
          <div>
            <Label>Email</Label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </div>
          {mode === "signup" && (
            <div>
              <Label>Your name</Label>
              <Input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
            </div>
          )}
          <div>
            <Label>Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              minLength={8}
              required
            />
          </div>

          {error && <ErrorNote message={error} />}

          <Button type="submit" disabled={submitting} className="w-full justify-center">
            {submitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create workspace"}
          </Button>
        </form>

        <button
          className="mt-5 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)] w-full text-center underline underline-offset-2"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login")
            setError(null)
          }}
        >
          {mode === "login" ? "New here? Create a workspace" : "Already have a workspace? Sign in"}
        </button>
      </div>
    </div>
  )
}
