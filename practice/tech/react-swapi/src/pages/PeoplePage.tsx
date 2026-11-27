import {
  keepPreviousData,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from '@tanstack/react-query'
import { useEffect, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { peopleQuery } from '../api/queries'
import { PAGE_SIZE, type PeoplePage as PeoplePageData } from '../api/swapi'
import { Pagination } from '../components/Pagination'
import { PeopleTable, PeopleTableSkeleton } from '../components/PeopleTable'
import { QueryError } from '../components/QueryError'
import { SearchBox } from '../components/SearchBox'

// The list's state lives in the URL (/?q=sky&page=2), not in useState. A reload, a shared link,
// or Back and Forward all bring back exactly this view, and nothing has to keep two copies of
// the state in sync: the components read the URL, and changing the URL is how they update it.
export function PeoplePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('q') ?? ''
  const page = parsePage(searchParams.get('page'))

  function updateSearch(query: string) {
    // A new search starts again at page 1. `replace` swaps the current history entry instead
    // of adding one, so Back leaves the list rather than replaying every search typed.
    setSearchParams(listParams(query, 1), { replace: true })
  }

  return (
    <>
      {/* React 19 moves a <title> rendered anywhere into <head>. Its child must be one string,
          hence the template literal rather than {search} and text side by side. */}
      <title>{`${search ? `“${search}”` : 'Characters'} · SWAPI explorer`}</title>
      <h1>Characters</h1>
      <SearchBox query={search} onSearch={updateSearch} />
      <PeopleResults search={search} page={page} />
    </>
  )
}

function PeopleResults({ search, page }: { search: string; page: number }) {
  const queryClient = useQueryClient()
  const query = useQuery({
    ...peopleQuery(search, page),
    // While another page or search loads, keep showing the current rows (dimmed) instead of
    // swapping them for a loading state and back. `isPlaceholderData` is true meanwhile.
    placeholderData: keepPreviousData,
  })
  const { data, isPlaceholderData } = query

  // Fetch the next page while the user reads this one, so Next shows it instantly. This is
  // what effects are for: keeping something outside React (here the query cache) in step with
  // what's on screen. It waits for real data, since a placeholder's hasNext describes the
  // previous page.
  useEffect(() => {
    if (data?.hasNext && !isPlaceholderData) {
      void queryClient.prefetchQuery(peopleQuery(search, page + 1))
    }
  }, [data, isPlaceholderData, queryClient, search, page])

  // Exactly one of these shows. Checking the flags in this order narrows the type: past
  // isPending and isError, TypeScript knows `query.data` is defined.
  let body: ReactNode = null
  if (query.isPending) {
    body = <PeopleTableSkeleton />
  } else if (query.isError) {
    body = <QueryError error={query.error} onRetry={query.refetch} />
  } else if (query.data.people.length > 0) {
    body = (
      <div className={isPlaceholderData ? 'stale' : undefined}>
        <PeopleTable people={query.data.people} listSearch={`?${listParams(search, page)}`} />
        <Pagination
          page={page}
          totalPages={Math.ceil(query.data.total / PAGE_SIZE)}
          hasPrevious={query.data.hasPrevious}
          // No skipping ahead from a placeholder: its hasNext belongs to the old page.
          hasNext={query.data.hasNext && !isPlaceholderData}
          searchFor={(n) => `?${listParams(search, n)}`}
        />
      </div>
    )
  }

  return (
    // aria-busy tells assistive technology this region is mid-update.
    <section aria-label="Results" aria-busy={query.isFetching}>
      {/* role="status" is a polite live region: screen readers read out its new text when it
          changes, without moving focus. It stays mounted so every change is announced. */}
      <p role="status" className="status">
        {statusText(query, search)}
      </p>
      {body}
    </section>
  )
}

function statusText(query: UseQueryResult<PeoplePageData>, search: string): string {
  if (query.isPending) return 'Loading characters…'
  if (query.isError) return 'Couldn’t load characters.'
  if (query.isPlaceholderData) return 'Loading…'
  const { total } = query.data
  if (total === 0) return `No characters match “${search}”.`
  if (total === 1) return search ? `1 character matches “${search}”` : '1 character'
  return search ? `${total} characters match “${search}”` : `${total} characters`
}

/** The list's URL parameters: q (left out when empty) and page (left out on page 1). */
function listParams(search: string, page: number): URLSearchParams {
  const params = new URLSearchParams()
  if (search) params.set('q', search)
  if (page > 1) params.set('page', String(page))
  return params
}

// URL parameters are untrusted text: "?page=abc" or "?page=-3" mean page 1.
function parsePage(value: string | null): number {
  const page = Number(value)
  return Number.isInteger(page) && page >= 1 ? page : 1
}
