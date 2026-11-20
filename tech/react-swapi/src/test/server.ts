// A fake SWAPI for the tests: the first twelve characters, one planet and four films, with the
// real API's URLs, JSON shape, search and ten-per-page paging. MSW intercepts the app's real
// fetch() calls and answers them from here, so the code under test runs unchanged.
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { API_ROOT, PAGE_SIZE } from '../api/swapi'

const link = (resource: string, id: number) => `${API_ROOT}/${resource}/${id}/`

function person(id: number, name: string, fields: Record<string, string> = {}) {
  return {
    name,
    height: '172',
    mass: '77',
    hair_color: 'brown',
    skin_color: 'fair',
    eye_color: 'brown',
    birth_year: 'unknown',
    gender: 'n/a',
    homeworld: link('planets', 1),
    films: [1, 2, 3, 6].map((film) => link('films', film)),
    species: [],
    url: link('people', id),
    ...fields,
  }
}

const PEOPLE = [
  person(1, 'Luke Skywalker', {
    birth_year: '19BBY',
    gender: 'male',
    hair_color: 'blond',
    eye_color: 'blue',
  }),
  person(2, 'C-3PO'),
  person(3, 'R2-D2'),
  person(4, 'Darth Vader'),
  person(5, 'Leia Organa'),
  person(6, 'Owen Lars'),
  person(7, 'Beru Whitesun lars'),
  person(8, 'R5-D4'),
  person(9, 'Biggs Darklighter'),
  person(10, 'Obi-Wan Kenobi'),
  person(11, 'Anakin Skywalker'),
  person(12, 'Wilhuff Tarkin'),
]

const PLANETS = [
  {
    name: 'Tatooine',
    climate: 'arid',
    terrain: 'desert',
    population: '200000',
    url: link('planets', 1),
  },
]

function film(id: number, title: string, episode: number, released: string) {
  return {
    title,
    episode_id: episode,
    release_date: released,
    director: 'George Lucas',
    url: link('films', id),
  }
}

const FILMS = [
  film(1, 'A New Hope', 4, '1977-05-25'),
  film(2, 'The Empire Strikes Back', 5, '1980-05-17'),
  film(3, 'Return of the Jedi', 6, '1983-05-25'),
  film(6, 'Revenge of the Sith', 3, '2005-05-19'),
]

const notFound = () => HttpResponse.json({ detail: 'Not found' }, { status: 404 })

export const handlers = [
  http.get(`${API_ROOT}/people/`, ({ request }) => {
    const params = new URL(request.url).searchParams
    const search = params.get('search') ?? ''
    const page = Number(params.get('page') ?? 1)
    const matches = PEOPLE.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()))
    const results = matches.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)
    if (page > 1 && results.length === 0) return notFound()
    const pageUrl = (n: number) => `${API_ROOT}/people/?search=${search}&page=${n}`
    return HttpResponse.json({
      count: matches.length,
      next: page * PAGE_SIZE < matches.length ? pageUrl(page + 1) : null,
      previous: page > 1 ? pageUrl(page - 1) : null,
      results,
    })
  }),
  // /people/1/, /planets/1/, /films/6/...: look the record up by its own URL.
  http.get(`${API_ROOT}/:resource/:id/`, ({ request }) => {
    const record = [...PEOPLE, ...PLANETS, ...FILMS].find((r) => r.url === request.url)
    return record ? HttpResponse.json(record) : notFound()
  }),
]

export const server = setupServer(...handlers)

/** Every URL the app requested during the current test, in order (setup.ts clears it). */
export const requests: string[] = []
server.events.on('request:start', ({ request }) => {
  requests.push(request.url)
})
