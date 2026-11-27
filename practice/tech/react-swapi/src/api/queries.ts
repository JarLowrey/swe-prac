// Every request the app makes, described once as "query options": a cache key plus the function
// that fetches it. Components call useQuery(personQuery(id)), and prefetching calls
// queryClient.prefetchQuery(personQuery(id)). Both get the same key, so a prefetched result is
// exactly what the component reads later. queryOptions() does nothing at runtime; it ties the
// data type to the key, so queryClient.getQueryData(personQuery(1).queryKey) is typed Person.
//
// Query keys are arrays, compared by value and matched by prefix: invalidating ['people'] would
// mark every key below that starts with 'people' as stale. Everything the query function uses
// (search text, page, id) must be in its key. When the key changes, TanStack Query switches to
// that key's cache entry and fetches it if needed. The ESLint plugin checks this.
import { queryOptions, skipToken } from '@tanstack/react-query'
import { fetchFilm, fetchPeople, fetchPerson, fetchPlanet } from './swapi'

export function peopleQuery(search: string, page: number) {
  return queryOptions({
    queryKey: ['people', 'list', { search, page }],
    queryFn: async ({ signal, client }) => {
      const result = await fetchPeople(search, page, signal)
      // A list page already holds everything the character page shows. Copy each person into
      // their own cache entry, so opening one renders at once instead of fetching them again.
      for (const person of result.people) {
        client.setQueryData(personQuery(person.id).queryKey, person)
      }
      return result
    },
  })
}

export function personQuery(id: number) {
  return queryOptions({
    queryKey: ['people', 'detail', id],
    queryFn: ({ signal }) => fetchPerson(id, signal),
  })
}

// The planet's id is only known once the person has loaded. Passing skipToken instead of a
// query function means "not yet": the query stays pending without fetching, and starts as soon
// as a real id arrives. It's the type-safe form of `enabled: false`: inside the function,
// TypeScript knows `id` is a number.
export function planetQuery(id: number | undefined) {
  return queryOptions({
    queryKey: ['planets', id],
    queryFn: id === undefined ? skipToken : ({ signal }) => fetchPlanet(id, signal),
  })
}

// Many characters appear in the same films. Caching each film under its own id means the
// second character's page reuses what the first one fetched.
export function filmQuery(id: number) {
  return queryOptions({
    queryKey: ['films', id],
    queryFn: ({ signal }) => fetchFilm(id, signal),
  })
}
