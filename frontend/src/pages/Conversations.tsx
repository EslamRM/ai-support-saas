import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { Conversation, KnowledgeBase } from "../api/types"
import { Button, EmptyState, ErrorNote, Input, Label, Panel, PageHeader, StatusBadge } from "../components/ui"

export default function Conversations() {
  const navigate = useNavigate()
  const [conversations, setConversations] = useState<Conversation[] | null>(null)
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [kbId, setKbId] = useState("")
  const [customerIdentifier, setCustomerIdentifier] = useState("")
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api
      .get<Conversation[]>("/conversations")
      .then(setConversations)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load conversations"))
    api.get<KnowledgeBase[]>("/knowledge-bases").then((list) => {
      setKbs(list)
      if (list.length > 0) setKbId(list[0].id)
    }).catch(() => {})
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    setError(null)
    try {
      const conversation = await api.post<Conversation>("/conversations", {
        knowledge_base_id: kbId,
        customer_identifier: customerIdentifier,
      })
      navigate(`/conversations/${conversation.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start conversation")
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Conversations"
        description="Transcripts between customers and the AI agent."
        actions={
          kbs.length > 0 && (
            <Button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New conversation"}</Button>
          )
        }
      />

      {kbs.length === 0 && (
        <Panel className="p-5 mb-6">
          <p className="text-sm text-[var(--color-text-muted)]">
            Create a <Link to="/knowledge-bases" className="underline underline-offset-2">knowledge base</Link> first
            before starting a conversation.
          </p>
        </Panel>
      )}

      {showForm && (
        <Panel className="p-5 mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <Label>Knowledge base</Label>
              <select
                value={kbId}
                onChange={(e) => setKbId(e.target.value)}
                className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm"
              >
                {kbs.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label>Customer identifier</Label>
              <Input
                value={customerIdentifier}
                onChange={(e) => setCustomerIdentifier(e.target.value)}
                placeholder="customer@example.com"
                required
              />
            </div>
            <Button type="submit" disabled={creating}>
              {creating ? "Starting…" : "Start conversation"}
            </Button>
          </form>
        </Panel>
      )}

      {error && <ErrorNote message={error} />}

      {conversations && conversations.length === 0 && (
        <Panel>
          <EmptyState
            title="No conversations yet"
            description="Conversations appear here once customers start chatting with the agent."
          />
        </Panel>
      )}

      {conversations && conversations.length > 0 && (
        <Panel>
          <ul className="divide-y divide-[var(--color-border)]">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link to={`/conversations/${c.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-[var(--color-bg)]">
                  <div className="font-medium text-sm">{c.customer_identifier}</div>
                  <div className="flex items-center gap-3">
                    <StatusBadge status={c.status} />
                    <span className="text-sm text-[var(--color-text-muted)]">
                      {new Date(c.created_at).toLocaleString()}
                    </span>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  )
}
