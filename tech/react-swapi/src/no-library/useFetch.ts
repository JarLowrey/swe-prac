// Data fetching with nothing but useEffect: what you write when an interview says "no
// libraries", and a way to see what TanStack Query does for the rest of the app. The app itself
// doesn't use this hook; useFetch.test.ts checks it gets right what naive versions get wrong:
//
// 1. Race conditions. Typing "l", "lu", "luk" quickly starts three requests, and their
//    responses can arrive in any order. Each new URL aborts the previous request, so an old
//    response can never overwrite a newer one.
// 2. Unmounting. Leaving the page aborts the request in flight.
// 3. StrictMode. In development React runs every effect twice (setup, cleanup, setup) to expose
//    missing cleanups. Here the first request is simply aborted.
//
// Still missing next to the library: a cache (coming back to a page fetches it all again), one
// request shared by every component that wants the same data, retries, refetching stale data,
// prefetching, and keeping the previous page on screen while the next one loads.
import { useEffect, useEffectEvent, useState } from 'react'
import { HttpError } from '../api/swapi'

// One field says which case we're in, and each case carries only the fields that make sense
// for it. There's no state with both `data` and `error`, or `loading` alongside `data`.
export type FetchState<T> =
  { status: 'pending' } | { status: 'error'; error: Error } | { status: 'success'; data: T }

export function useFetch<T>(url: string, parse: (json: unknown) => T): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({ status: 'pending' })

  // A new URL makes the current data the wrong answer. Go back to pending in this same render,
  // not in the effect: the effect runs after paint, so the old data would flash on screen first.
  const [currentUrl, setCurrentUrl] = useState(url)
  if (url !== currentUrl) {
    setCurrentUrl(url)
    setState({ status: 'pending' })
  }

  // `parse` is often written inline, so it's a new function on every render. As an effect
  // dependency it would restart the request on every render. An Effect Event lets the effect
  // call the latest `parse` without depending on it, so only a new `url` restarts the request.
  const parseJson = useEffectEvent((json: unknown) => parse(json))

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const response = await fetch(url, { signal: controller.signal })
        if (!response.ok) throw new HttpError(response.status, url)
        const data = parseJson(await response.json())
        // Aborted while the body was being read? Then a newer request owns the state.
        if (!controller.signal.aborted) setState({ status: 'success', data })
      } catch (error) {
        // Aborting makes fetch reject too. That's us cancelling, not an error to show.
        if (!controller.signal.aborted) {
          setState({
            status: 'error',
            error: error instanceof Error ? error : new Error(String(error)),
          })
        }
      }
    }

    void load()
    // The cleanup runs before the effect runs again (a new URL) and when the component unmounts.
    return () => controller.abort()
  }, [url])

  return state
}
