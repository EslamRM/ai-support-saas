// Small shared primitives -- kept deliberately minimal (this is an
// internal ops tool, "engineering quality, not visual design" -- see
// docs/architecture.md Phase 8). Not a component library, just the
// handful of repeated patterns actual pages need.
import type { ReactNode } from "react"

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-xl font-semibold">{title}</h1>
        {description && <p className="text-sm text-[var(--color-text-muted)] mt-1">{description}</p>}
      </div>
      {actions}
    </div>
  )
}

export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg ${className}`}>
      {children}
    </div>
  )
}

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  className = "",
}: {
  children: ReactNode
  onClick?: () => void
  type?: "button" | "submit"
  variant?: "primary" | "secondary" | "danger"
  disabled?: boolean
  className?: string
}) {
  const variants = {
    primary: "bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]",
    secondary:
      "bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-bg)]",
    danger: "bg-[var(--color-danger)] text-white hover:opacity-90",
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`px-3.5 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  )
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:border-[var(--color-accent)] ${props.className ?? ""}`}
    />
  )
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-sm focus:border-[var(--color-accent)] ${props.className ?? ""}`}
    />
  )
}

export function Label({ children }: { children: ReactNode }) {
  return <label className="block text-sm font-medium mb-1.5">{children}</label>
}

const STATUS_STYLES: Record<string, string> = {
  indexed: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  answered: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  open: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  resolved: "bg-[var(--color-accent-soft)] text-[var(--color-accent)]",
  processing: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
  pending: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
  handoff: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
  in_progress: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
  failed: "bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
  closed: "bg-gray-100 text-[var(--color-text-muted)]",
}

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-[var(--color-text-muted)]"
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${style}`}>
      {status.replace("_", " ")}
    </span>
  )
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return (
    <div className="text-center py-16 px-4">
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="text-sm text-[var(--color-text-muted)] mt-1">{description}</p>}
    </div>
  )
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="rounded-md bg-[var(--color-danger-soft)] text-[var(--color-danger)] text-sm px-3 py-2">
      {message}
    </div>
  )
}
