// The entry point: create the app-wide objects once, wrap the app in their providers, mount it.
import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { createQueryClient } from './api/queryClient'
import { App } from './App'
import './index.css'

// Created once, outside any component. It holds the cache, so making it inside a component
// would create a new, empty cache on every render.
const queryClient = createQueryClient()

createRoot(document.getElementById('root')!).render(
  // StrictMode (development only) renders every component twice and runs every effect's
  // setup, cleanup, setup. Impure renders and effects that don't clean up then show up at once
  // instead of as rare bugs in production.
  <StrictMode>
    {/* Providers put an object into React context, where any component below can reach it
        with a hook (useQueryClient, useSearchParams...) without passing it down as props. */}
    <QueryClientProvider client={queryClient}>
      {/* BrowserRouter keeps the UI in sync with the address bar, using the History API. */}
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
