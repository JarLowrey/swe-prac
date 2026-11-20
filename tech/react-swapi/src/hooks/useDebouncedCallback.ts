import { useEffect, useLayoutEffect, useRef } from 'react'

/**
 * Delays a callback until calls stop coming for `delayMs`. `run` (re)starts the wait, `cancel`
 * drops a pending call. Search-as-you-type uses it to send one request when the user pauses,
 * instead of one per keystroke.
 */
export function useDebouncedCallback<Args extends unknown[]>(
  callback: (...args: Args) => void,
  delayMs: number,
) {
  // Refs hold values that must survive re-renders but shouldn't cause one when they change.
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)

  // The timer fires after the render that started it. Calling *that* render's callback would
  // use its props and state, which may be out of date by then. So keep the latest callback in
  // a ref and call that. A ref may not be written during render (React can render a component
  // and throw the result away), so it's updated after each commit instead.
  const latest = useRef(callback)
  useLayoutEffect(() => {
    latest.current = callback
  })

  // A pending call is dropped when the component unmounts: no work for a page that's gone.
  useEffect(() => {
    return () => clearTimeout(timer.current)
  }, [])

  return {
    run(...args: Args) {
      clearTimeout(timer.current)
      timer.current = setTimeout(() => latest.current(...args), delayMs)
    },
    cancel() {
      clearTimeout(timer.current)
    },
  }
}
