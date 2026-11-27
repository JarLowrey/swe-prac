// Renders the whole app the way main.tsx does, starting at any URL.
import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { userEvent } from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { createQueryClient } from '../api/queryClient'
import { App } from '../App'

export function renderApp(url = '/') {
  // A new cache for every test, so no test sees data another one fetched. No retries, so a
  // failed request shows its error at once instead of after the retry delays.
  const queryClient = createQueryClient({ retry: false })
  render(
    <QueryClientProvider client={queryClient}>
      {/* MemoryRouter keeps the history in memory instead of the address bar. */}
      <MemoryRouter initialEntries={[url]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
  // userEvent acts like a person: it focuses, presses each key, moves the pointer. fireEvent
  // only dispatches the one event you name.
  return { user: userEvent.setup() }
}
