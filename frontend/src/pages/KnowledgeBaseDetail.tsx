import { useEffect, useRef, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { api, ApiError } from "../api/client"
import type { DocumentSummary, KnowledgeBase } from "../api/types"
import { Button, EmptyState, ErrorNote, Panel, PageHeader, StatusBadge } from "../components/ui"

export default function KnowledgeBaseDetail() {
  const { id } = useParams<{ id: string }>()
  const [kb, setKb] = useState<KnowledgeBase | null>(null)
  const [docs, setDocs] = useState<DocumentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  function loadDocs() {
    if (!id) return
    api
      .get<DocumentSummary[]>(`/documents?knowledge_base_id=${id}`)
      .then(setDocs)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load documents"))
  }

  useEffect(() => {
    if (!id) return
    api.get<KnowledgeBase>(`/knowledge-bases/${id}`).then(setKb).catch(() => {})
    loadDocs()
    // Documents finish processing synchronously-ish in this environment
    // (or asynchronously via a real worker in production) -- poll every
    // few seconds while any document is still pending/processing so
    // status updates without a manual refresh.
    const interval = setInterval(loadDocs, 3000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file || !id) return
    setUploading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append("knowledge_base_id", id)
      formData.append("file", file)
      await api.postForm(`/documents`, formData)
      loadDocs()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      if (fileInput.current) fileInput.current.value = ""
    }
  }

  return (
    <div>
      <Link to="/knowledge-bases" className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text)]">
        ← Knowledge bases
      </Link>

      <PageHeader
        title={kb?.name ?? "Knowledge base"}
        description={kb?.description ?? undefined}
        actions={
          <>
            <input
              ref={fileInput}
              type="file"
              accept=".txt,.md,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button onClick={() => fileInput.current?.click()} disabled={uploading}>
              {uploading ? "Uploading…" : "Upload document"}
            </Button>
          </>
        }
      />

      {error && <ErrorNote message={error} />}

      {docs && docs.length === 0 && (
        <Panel>
          <EmptyState title="No documents yet" description="Upload a .txt, .md, or .pdf file to get started." />
        </Panel>
      )}

      {docs && docs.length > 0 && (
        <Panel>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-muted)]">
                <th className="px-5 py-3 font-medium">File</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Chunks</th>
                <th className="px-5 py-3 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="px-5 py-3">
                    <div className="font-medium">{doc.filename}</div>
                    {doc.error_message && (
                      <div className="text-[var(--color-danger)] text-xs mt-0.5">{doc.error_message}</div>
                    )}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-5 py-3 text-[var(--color-text-muted)]">{doc.chunk_count || "—"}</td>
                  <td className="px-5 py-3 text-[var(--color-text-muted)]">
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}
    </div>
  )
}
