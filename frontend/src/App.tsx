import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider, useAuth } from "./auth/AuthContext"
import Layout from "./components/Layout"
import Login from "./pages/Login"
import Dashboard from "./pages/Dashboard"
import KnowledgeBases from "./pages/KnowledgeBases"
import KnowledgeBaseDetail from "./pages/KnowledgeBaseDetail"
import Conversations from "./pages/Conversations"
import ConversationDetail from "./pages/ConversationDetail"
import Tickets from "./pages/Tickets"

function ProtectedRoutes() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-sm text-[var(--color-text-muted)]">Loading…</div>
  }
  if (!user) return <Navigate to="/login" replace />

  return <Layout />
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoutes />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/knowledge-bases" element={<KnowledgeBases />} />
            <Route path="/knowledge-bases/:id" element={<KnowledgeBaseDetail />} />
            <Route path="/conversations" element={<Conversations />} />
            <Route path="/conversations/:id" element={<ConversationDetail />} />
            <Route path="/tickets" element={<Tickets />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
