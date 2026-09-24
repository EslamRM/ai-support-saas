import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { KnowledgeBase } from "../api/types"
import { Button, EmptyState, ErrorNote, Input, Label, Panel, PageHeader } from "../components/ui"

export default function KnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [creating, setCreating] = useState(false)

  function load() {
    api
      .get<KnowledgeBase[]>("/knowledge-bases")
      .then(setKbs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load"))
  }

  useEffect(load, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setCreating(true)
    setError(null)
    try {
      await api.post("/knowledge-bases", { name, description: description || null })
      setName("")
      setDescription("")
      setShowForm(false)
      load()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create knowledge base")
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Knowledge bases"
        description="Documents your AI agent can draw on to answer customer questions."
        actions={<Button onClick={() => setShowForm((s) => !s)}>{showForm ? "Cancel" : "New knowledge base"}</Button>}
      />

      {showForm && (
        <Panel className="p-5 mb-6">
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Product Docs" required />
            </div>
            <div>
              <Label>Description (optional)</Label>
              <Input value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <Button type="submit" disabled={creating}>
              {creating ? "Creating…" : "Create"}
            </Button>
          </form>
        </Panel>
      )}

      {error && <ErrorNote message={error} />}

      {kbs && kbs.length === 0 && (
        <Panel>
          <EmptyState
            title="No knowledge bases yet"
            description="Create one, then upload documents for the agent to search."
          />
        </Panel>
      )}

      {kbs && kbs.length > 0 && (
        <Panel>
          <ul className="divide-y divide-[var(--color-border)]">
            {kbs.map((kb) => (
              <li key={kb.id}>
                <Link to={`/knowledge-bases/${kb.id}`} className="flex items-center justify-between px-5 py-4 hover:bg-[var(--color-bg)]">
                  <div>
                    <div className="font-medium text-sm">{kb.name}</div>
                    {kb.description && (
                      <div className="text-sm text-[var(--color-text-muted)] mt-0.5">{kb.description}</div>
                    )}
                  </div>
                  <div className="text-sm text-[var(--color-text-muted)]">
                    {new Date(kb.created_at).toLocaleDateString()}
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
