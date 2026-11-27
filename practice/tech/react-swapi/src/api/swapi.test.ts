import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { ZodError } from 'zod'
import { server } from '../test/server'
import { API_ROOT, fetchPeople, fetchPerson, HttpError } from './swapi'

describe('the SWAPI client', () => {
  it('turns SWAPI JSON into app objects: ids from URLs, null for unknown', async () => {
    expect(await fetchPerson(2)).toEqual({
      id: 2,
      name: 'C-3PO',
      birthYear: null, // "unknown"
      gender: null, // "n/a"
      heightCm: '172',
      massKg: '77',
      hairColor: 'brown',
      eyeColor: 'brown',
      homeworldId: 1,
      filmIds: [1, 2, 3, 6],
    })
  })

  it('reads the paging fields', async () => {
    const page = await fetchPeople('', 2)

    expect(page).toMatchObject({ total: 12, hasNext: false, hasPrevious: true })
    expect(page.people.map((p) => p.name)).toEqual(['Anakin Skywalker', 'Wilhuff Tarkin'])
  })

  it('throws an HttpError that keeps the status', async () => {
    await expect(fetchPerson(999)).rejects.toThrow(HttpError)
    await expect(fetchPerson(999)).rejects.toMatchObject({ status: 404 })
  })

  it('rejects data in the wrong shape instead of passing it on', async () => {
    server.use(http.get(`${API_ROOT}/people/1/`, () => HttpResponse.json({ name: 42 })))

    await expect(fetchPerson(1)).rejects.toThrow(ZodError)
  })
})
