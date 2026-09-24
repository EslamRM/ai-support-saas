import { useEffect, useState } from "react"
import { api, ApiError } from "../api/client"
import type { AnalyticsSummary } from "../api/types"
import { ErrorNote, Panel } from "../components/ui"

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Panel className="p-5">
      <div className="text-sm text-[var(--color-text-muted)]">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </Panel>
  )
}

export default function Dashboard() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<AnalyticsSummary>("/analytics")
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load analytics"))
  }, [])

  if (error) return <ErrorNote message={error} />
  if (!summary) return <div className="text-sm text-[var(--color-text-muted)]">Loading…</div>

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Overview</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <Stat label="Conversations" value={String(summary.conversation_count)} />
        <Stat label="Messages" value={String(summary.message_count)} />
        <Stat label="Tickets" value={String(summary.ticket_count)} />
        <Stat
          label="Handoff rate"
          value={summary.handoff_rate === null ? "—" : `${Math.round(summary.handoff_rate * 100)}%`}
        />
      </div>

      <Panel className="p-5">
        <div className="text-sm font-medium mb-3">Tickets by status</div>
        <div className="space-y-2">
          {Object.entries(summary.tickets_by_status).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between text-sm">
              <span className="capitalize text-[var(--color-text-muted)]">{status.replace("_", " ")}</span>
              <span className="font-medium">{count}</span>
            </div>
          ))}
        </div>
        {summary.average_confidence !== null && (
          <div className="mt-4 pt-4 border-t border-[var(--color-border)] text-sm flex justify-between">
            <span className="text-[var(--color-text-muted)]">Average agent confidence</span>
            <span className="font-medium">{Math.round(summary.average_confidence * 100)}%</span>
          </div>
        )}
      </Panel>
    </div>
  )
}
