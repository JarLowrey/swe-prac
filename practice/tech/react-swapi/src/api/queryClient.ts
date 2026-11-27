// The QueryClient owns TanStack Query's cache. The app makes one when it starts (main.tsx). Each
// test makes its own, so no cached data leaks from one test into the next.
import { QueryClient } from '@tanstack/react-query'
import { HttpError } from './swapi'

export function createQueryClient({ retry = true } = {}) {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // How long fetched data counts as fresh. While it's fresh, going back to a page renders
        // it from the cache with no request at all. The default is 0: render the cached copy,
        // but refetch it in the background whenever a component using it mounts. SWAPI's data
        // never changes, so five minutes costs nothing. (Unused entries are dropped after
        // `gcTime`, also five minutes by default.)
        staleTime: 5 * 60 * 1000,
        // Retry twice, with growing delays, but only failures that might go away on their own.
        // Tests turn retries off, so a failure shows at once instead of after the delays.
        retry: retry ? (failureCount, error) => failureCount < 2 && isTransient(error) : false,
      },
    },
  })
}

// fetch() rejects with a TypeError when the network fails, and a 5xx is the server's problem:
// both may work a second later. A 4xx, or data that fails its schema, will fail the same way
// every time: asking again for a character that doesn't exist won't make it exist.
function isTransient(error: Error): boolean {
  if (error instanceof HttpError) return error.status >= 500
  return error instanceof TypeError
}
