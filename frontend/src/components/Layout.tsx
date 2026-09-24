import { NavLink, Outlet } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/knowledge-bases", label: "Knowledge bases" },
  { to: "/conversations", label: "Conversations" },
  { to: "/tickets", label: "Tickets" },
]

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-[var(--color-border)] bg-[var(--color-surface)] flex flex-col">
        <div className="px-5 py-5 border-b border-[var(--color-border)]">
          <div className="font-semibold text-[15px]">Support Agent Console</div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--color-accent-soft)] text-[var(--color-accent)] font-medium"
                    : "text-[var(--color-text-muted)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)]"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 border-t border-[var(--color-border)] text-sm">
          <div className="font-medium truncate">{user?.email}</div>
          <div className="text-[var(--color-text-muted)] capitalize">{user?.role}</div>
          <button
            onClick={logout}
            className="mt-2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] underline underline-offset-2"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 px-8 py-8 max-w-5xl">
        <Outlet />
      </main>
    </div>
  )
}
