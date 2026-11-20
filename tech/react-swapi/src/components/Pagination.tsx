import type { ReactNode } from 'react'
import { Link } from 'react-router'

type PaginationProps = {
  page: number
  totalPages: number
  hasPrevious: boolean
  hasNext: boolean
  /** The URL search string for page n, e.g. "?q=sky&page=2". */
  searchFor: (page: number) => string
}

// Pages are links, not buttons, because changing page is navigation. Each page has its own URL:
// it can be bookmarked, shared or opened in a new tab, and Back returns to the previous page.
export function Pagination({ page, totalPages, hasPrevious, hasNext, searchFor }: PaginationProps) {
  return (
    <nav className="pagination" aria-label="Pages">
      <PageLink search={searchFor(page - 1)} enabled={hasPrevious}>
        ← Previous
      </PageLink>
      <span>
        Page {page} of {totalPages}
      </span>
      <PageLink search={searchFor(page + 1)} enabled={hasNext}>
        Next →
      </PageLink>
    </nav>
  )
}

type PageLinkProps = { search: string; enabled: boolean; children: ReactNode }

function PageLink({ search, enabled, children }: PageLinkProps) {
  // A link can't be disabled. On the first or last page, show plain text instead.
  if (!enabled) return <span className="page-link disabled">{children}</span>
  // `to` with only a search keeps the current path and replaces the query string.
  return (
    <Link className="page-link" to={{ search }}>
      {children}
    </Link>
  )
}
