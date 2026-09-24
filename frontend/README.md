# Frontend — Support Agent Console

The staff-facing admin dashboard: manage knowledge bases, upload documents, review
conversations, try the agent, and track tickets. Built with React + TypeScript + Vite +
Tailwind CSS v4.

## Setup

```bash
npm install
npm run dev
```

Requires the backend running at `http://localhost:8000` (see `../backend/README.md`) --
`vite.config.ts` proxies `/api/*` requests there during local development, so no CORS
configuration is needed.

## Structure

```
src/
  api/
    client.ts      # the ONE place that calls fetch() -- attaches the JWT, normalizes errors
    types.ts        # TypeScript types mirroring the backend's Pydantic schemas
  auth/
    AuthContext.tsx # login/logout state, session restore on page load
  components/
    Layout.tsx       # sidebar navigation + page shell
    ui.tsx            # small shared primitives (Button, Input, Panel, StatusBadge, ...)
  pages/
    Login.tsx
    Dashboard.tsx            # analytics overview (GET /analytics)
    KnowledgeBases.tsx        # list + create
    KnowledgeBaseDetail.tsx    # document list + upload, polls for processing status
    Conversations.tsx          # list + start a new one
    ConversationDetail.tsx      # transcript + send a message (drives the real agent)
    Tickets.tsx                  # list + status updates (admin+ only, matches backend RBAC)
```

## Design notes

This is an internal ops tool for support-team staff, built for density and fast scanning --
see `docs/architecture.md`'s Phase 8 note: "the goal is engineering quality, not visual
design." Design tokens (color, type) live as CSS variables in `src/index.css`; there's no
component library, just the handful of shared primitives actual pages need
(`src/components/ui.tsx`).

## Known gap

There's no dedicated customer-facing chat widget here -- `ConversationDetail`'s message form
lets *staff* send messages as a stand-in for a customer, useful for testing a knowledge base's
answers. A real embeddable widget for actual end customers is out of scope for this phase --
see `docs/tickets.md` and `docs/architecture.md`'s notes on customer-facing auth being a
documented gap in the backend too.
