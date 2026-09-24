import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { ConversationWithMessages } from "../api/types"
import { Button, ErrorNote, Input, Panel, PageHeader, StatusBadge } from "../components/ui"

export default function ConversationDetail() {
  const { id } = useParams<{ id: string }>()
  const [conversation, setConversation] = useState<ConversationWithMessages | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [sending, setSending] = useState(false)

  function load() {
    if (!id) return
    api
      .get<ConversationWithMessages>(`/conversations/${id}`)
      .then(setConversation)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load conversation"))
  }

  useEffect(load, [id])

  async function handleSend(e: React.FormEvent) {
    e.preventDefault()
    if (!draft.trim() || !id) return
    setSending(true)
    setError(null)
    try {
      await api.post(`/conversations/${id}/messages`, { content: draft })
      setDraft("")
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send message")
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <Link to="/conversations" className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]">
        ← Conversations
      </Link>

      <PageHeader
        title={conversation?.customer_identifier ?? "Conversation"}
        actions={conversation && <StatusBadge status={conversation.status} />}
      />

      {error && <ErrorNote message={error} />}

      <Panel className="p-5 mb-4">
        <div className="space-y-4">
          {conversation?.messages.length === 0 && (
            <p className="text-sm text-[var(--color-text-muted)]">
              No messages yet. Send one below to try the agent for this knowledge base.
            </p>
          )}
          {conversation?.messages.map((m) => (
            <div key={m.id} className={m.role === "user" ? "text-right" : ""}>
              <div
                className={`inline-block max-w-lg rounded-lg px-4 py-2.5 text-sm text-left ${
                  m.role === "user"
                    ? "bg-[var(--color-accent)] text-white"
                    : "bg-[var(--color-bg)] border border-[var(--color-border)]"
                }`}
              >
                {m.content}
              </div>
              {m.role === "assistant" && m.agent_metadata && (
                <div className="text-xs text-[var(--color-text-muted)] mt-1 flex gap-2">
                  {m.agent_metadata.route && <StatusBadge status={m.agent_metadata.route} />}
                  {m.agent_metadata.confidence !== undefined && (
                    <span>confidence: {Math.round((m.agent_metadata.confidence ?? 0) * 100)}%</span>
                  )}
                  {m.agent_metadata.ticket_id && (
                    <Link to="/tickets" className="underline underline-offset-2">
                      ticket created
                    </Link>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </Panel>

      <form onSubmit={handleSend} className="flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type a message as this customer…"
          disabled={sending}
        />
        <Button type="submit" disabled={sending || !draft.trim()}>
          {sending ? "Sending…" : "Send"}
        </Button>
      </form>
    </div>
  )
}
