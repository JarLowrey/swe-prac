// Runs before each test file (see test.setupFiles in vite.config.ts).
import '@testing-library/jest-dom/vitest' // DOM matchers: toBeInTheDocument(), toHaveValue()...
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { requests, server } from './server'

// A request with no handler fails the test: a test can never quietly call the real API.
// (MSW 3 says "frame" because the same rule covers WebSocket messages.)
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))

afterEach(() => {
  cleanup() // unmount whatever the test rendered
  server.resetHandlers() // drop handlers a test added with server.use()
  requests.length = 0
})

afterAll(() => server.close())
