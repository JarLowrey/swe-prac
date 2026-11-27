import { renderHook, waitFor } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { server } from '../test/server'
import { useFetch } from './useFetch'

const nameOnly = z.object({ name: z.string() })
const parse = (json: unknown) => nameOnly.parse(json)

describe('useFetch', () => {
  it('ignores a response that arrives after a newer request', async () => {
    server.use(
      http.get('https://example.test/slow', async () => {
        await delay(100)
        return HttpResponse.json({ name: 'slow' })
      }),
      http.get('https://example.test/fast', () => HttpResponse.json({ name: 'fast' })),
    )
    const { result, rerender } = renderHook(({ url }) => useFetch(url, parse), {
      initialProps: { url: 'https://example.test/slow' },
    })

    rerender({ url: 'https://example.test/fast' })

    await waitFor(() =>
      expect(result.current).toEqual({ status: 'success', data: { name: 'fast' } }),
    )
    // Give the slow response time to arrive. Without the abort, it would overwrite "fast".
    await delay(200)
    expect(result.current).toEqual({ status: 'success', data: { name: 'fast' } })
  })

  it('reports an HTTP error', async () => {
    server.use(
      http.get('https://example.test/missing', () => new HttpResponse(null, { status: 404 })),
    )

    const { result } = renderHook(() => useFetch('https://example.test/missing', parse))

    await waitFor(() => expect(result.current.status).toBe('error'))
  })
})
