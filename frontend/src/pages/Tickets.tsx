import { useEffect, useState } from "react"
import { api, ApiError } from "../api/client"
import type { Ticket, TicketStatus } from "../api/types"
import { EmptyState, ErrorNote, Panel, PageHeader, StatusBadge } from "../components/ui"
import { useAuth } from "../auth/AuthContext"

const STATUS_OPTIONS: TicketStatus[] = ["open", "in_progress", "resolved", "closed"]

export default function Tickets() {
  const { user } = useAuth()
  const [tickets, setTickets] = useState<Ticket[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Status changes require admin+ (see backend/app/modules/tickets/router.py)
  // -- an agent-level account can view tickets but not resolve them here.
  const canUpdateStatus = user?.role === "owner" || user?.role === "admin"

  function load() {
    api
      .get<Ticket[]>("/tickets")
      .then(setTickets)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load tickets"))
  }

  useEffect(load, [])

  async function handleStatusChange(ticketId: string, status: TicketStatus) {
    setError(null)
    try {
      await api.patch(`/tickets/${ticketId}/status`, { status })
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update ticket")
    }
  }

  return (
    <div>
      <PageHeader
        title="Tickets"
        description="Created automatically when the agent can't confidently answer, or filed manually."
      />

      {error && <ErrorNote message={error} />}

      {tickets && tickets.length === 0 && (
        <Panel>
          <EmptyState title="No tickets yet" description="Tickets appear here when a conversation needs a human." />
        </Panel>
      )}

      {tickets && tickets.length > 0 && (
        <Panel>
          <ul className="divide-y divide-[var(--color-border)]">
            {tickets.map((t) => (
              <li key={t.id} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-medium text-sm">{t.title}</div>
                    <p className="text-sm text-[var(--color-text-muted)] mt-1 line-clamp-2">{t.description}</p>
                    <div className="text-xs text-[var(--color-text-muted)] mt-2">
                      {t.customer_identifier} · {new Date(t.created_at).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={t.priority} />
                    {canUpdateStatus ? (
                      <select
                        value={t.status}
                        onChange={(e) => handleStatusChange(t.id, e.target.value as TicketStatus)}
                        className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs capitalize"
                      >
                        {STATUS_OPTIONS.map((s) => (
                          <option key={s} value={s}>
                            {s.replace("_", " ")}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <StatusBadge status={t.status} />
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  )
}
