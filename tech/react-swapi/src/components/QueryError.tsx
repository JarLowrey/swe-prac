import { ZodError } from 'zod'
import { HttpError } from '../api/swapi'

type QueryErrorProps = { error: Error; onRetry: () => void }

/** A failed request: what went wrong, in words a user can act on, and a way to try again. */
export function QueryError({ error, onRetry }: QueryErrorProps) {
  return (
    // role="alert" makes screen readers announce the message as soon as it appears.
    <div className="error" role="alert">
      <p>{describe(error)}</p>
      {/* An arrow function, not onClick={onRetry}: React would pass the click event as the
          first argument, and TanStack Query's refetch() reads its first argument as options. */}
      <button type="button" onClick={() => onRetry()}>
        Try again
      </button>
    </div>
  )
}

function describe(error: Error): string {
  if (error instanceof HttpError) {
    return error.status >= 500
      ? 'SWAPI is having problems right now (server error).'
      : `SWAPI turned the request down (HTTP ${error.status}).`
  }
  if (error instanceof ZodError) return 'SWAPI sent data in a shape this app doesn’t understand.'
  return 'Couldn’t reach SWAPI. Check your connection.'
}
