import { useQueries, useQuery, type UseQueryResult } from '@tanstack/react-query'
import { useId } from 'react'
import { Link, useLocation, useParams } from 'react-router'
import { filmQuery, personQuery, planetQuery } from '../api/queries'
import { HttpError, type Film } from '../api/swapi'
import { QueryError } from '../components/QueryError'
import { NotFoundPage } from './NotFoundPage'

export function PersonPage() {
  const { id } = useParams()
  const { state } = useLocation()
  const personId = parseId(id)
  if (personId === null) return <NotFoundPage message={`“${id}” isn’t a character id.`} />
  // The list sends its search ("?q=sky&page=2") along with the navigation, so Back to
  // characters returns to the same results. Opened from a bookmark there's none: show page 1.
  return <PersonDetails id={personId} backTo={`/${listSearchFrom(state)}`} />
}

function PersonDetails({ id, backTo }: { id: number; backTo: string }) {
  const filmsHeadingId = useId()
  const person = useQuery(personQuery(id))

  // A dependent query: the homeworld's id comes from the person. Until the person arrives,
  // planetQuery gets `undefined` and waits (see skipToken in queries.ts).
  const homeworld = useQuery(planetQuery(person.data?.homeworldId))

  // Parallel queries: one per film, all in flight at once. useQueries takes a list that can
  // change length between renders. Calling useQuery in a loop can't do that, because a
  // component must call the same hooks, in the same order, on every render.
  const films = useQueries({
    queries: (person.data?.filmIds ?? []).map((filmId) => filmQuery(filmId)),
    combine: combineFilms,
  })

  if (person.isPending) return <p role="status">Loading character…</p>
  if (person.isError) {
    if (person.error instanceof HttpError && person.error.status === 404) {
      return <NotFoundPage message={`There’s no character with id ${id}.`} />
    }
    return <QueryError error={person.error} onRetry={person.refetch} />
  }

  const p = person.data
  return (
    <article>
      <title>{`${p.name} · SWAPI explorer`}</title>
      <p>
        <Link to={backTo}>← Back to characters</Link>
      </p>
      <h1>{p.name}</h1>
      <dl className="facts">
        <Fact label="Born" value={p.birthYear} />
        <Fact label="Gender" value={p.gender} />
        <Fact label="Height" value={p.heightCm && `${p.heightCm} cm`} />
        <Fact label="Mass" value={p.massKg && `${p.massKg} kg`} />
        <Fact label="Hair" value={p.hairColor} />
        <Fact label="Eyes" value={p.eyeColor} />
        <Fact label="Homeworld" value={homeworldText(homeworld)} />
      </dl>

      <h2 id={filmsHeadingId}>Films</h2>
      <ul className="films" aria-labelledby={filmsHeadingId}>
        {films.loaded.map((film) => (
          <li key={film.id}>
            Episode {film.episode}: <cite>{film.title}</cite> ({film.releaseDate.slice(0, 4)})
          </li>
        ))}
      </ul>
      {films.pending > 0 && <p className="status">Loading {films.pending} more…</p>}
      {films.failed > 0 && <p className="status">{films.failed} couldn’t be loaded.</p>}
    </article>
  )
}

// Turns the per-film results into what the page renders: the loaded films in episode order,
// plus counts of the rest. It's declared outside the component so it's the same function on
// every render, and TanStack Query only re-runs it when a film's result changes. (Written
// inline, the React Compiler would keep it stable anyway.)
function combineFilms(results: UseQueryResult<Film>[]) {
  return {
    // toSorted() returns a sorted copy and leaves the input alone.
    loaded: results
      .flatMap((result) => (result.data ? [result.data] : []))
      .toSorted((a, b) => a.episode - b.episode),
    pending: results.filter((result) => result.isPending).length,
    failed: results.filter((result) => result.isError).length,
  }
}

function homeworldText(query: UseQueryResult<{ name: string }>): string {
  if (query.isPending) return 'Loading…'
  if (query.isError) return 'Couldn’t load'
  return query.data.name
}

function Fact({ label, value }: { label: string; value: string | null }) {
  // A fragment: <dt> and <dd> must be direct children of the <dl>, so no wrapper element.
  return (
    <>
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </>
  )
}

// Route parameters are untrusted text. Anything but a positive whole number is not an id, and
// is rejected before any request is made.
function parseId(value: string | undefined): number | null {
  const id = Number(value)
  return Number.isInteger(id) && id > 0 ? id : null
}

// Navigation state can be anything, or missing entirely (a bookmark, a new tab), so check
// its shape instead of trusting a type annotation.
function listSearchFrom(state: unknown): string {
  if (typeof state === 'object' && state !== null && 'listSearch' in state) {
    if (typeof state.listSearch === 'string') return state.listSearch
  }
  return ''
}
