// Everything that knows SWAPI's URLs and JSON shape lives in this file. The rest of the app only
// sees the small typed objects defined here (Person, Planet, Film), so if the API changed, or the
// app moved to a different Star Wars API, this is the only file to edit.
//
// TypeScript types disappear at runtime: annotating a fetch result as `Person` doesn't make it
// one. So every response is *parsed* with a Zod schema at this boundary. If SWAPI ever sent
// something unexpected, the query fails here with a clear error, instead of rendering
// `undefined` somewhere deep in a component.
import { z } from 'zod'

export const API_ROOT = 'https://swapi.dev/api'

/** SWAPI always returns 10 results per page; there's no page-size parameter. */
export const PAGE_SIZE = 10

/** A response that arrived with a non-2xx status. The status lets the UI tell "no such
 * character" (404) apart from "the server is down" (5xx), and the retry policy skip 4xx. */
export class HttpError extends Error {
  // A plain field, not `constructor(readonly status: number)`: parameter properties aren't
  // erasable syntax (see erasableSyntaxOnly in tsconfig.app.json).
  readonly status: number

  constructor(status: number, url: string) {
    super(`HTTP ${status} from ${url}`)
    this.name = 'HttpError'
    this.status = status
  }
}

// fetch() only rejects when the network fails. A 404 or a 500 still resolves, so check `ok`
// and throw; otherwise TanStack Query would treat an error page as data.
//
// `signal` lets the caller cancel the request. TanStack Query passes one to every query
// function and aborts it once nothing needs the answer: the user typed another letter, or left
// the page.
async function getJson(url: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(url, { signal })
  if (!response.ok) throw new HttpError(response.status, url)
  return response.json() // `unknown`, not `any`: nothing can use it until a schema parses it
}

// ---------------------------------------------------------------------------- schemas
// SWAPI links records by URL ("https://swapi.dev/api/planets/1/"). The app routes and caches by
// numeric id, so each URL becomes its id while parsing.
const resourceId = z.string().transform((url, ctx) => {
  const id = Number(/\/(\d+)\/?$/.exec(url)?.[1])
  if (!Number.isInteger(id)) {
    ctx.addIssue({ code: 'custom', message: `no id at the end of ${url}` })
    return z.NEVER
  }
  return id
})

// SWAPI writes missing values as "unknown" or "n/a". Turn those into null, so the UI has one
// thing to check instead of comparing strings everywhere.
const optionalText = z
  .string()
  .transform((value) => (value === 'unknown' || value === 'n/a' ? null : value))

// Each schema checks the raw JSON, then `.transform` reshapes it into what the app wants:
// camelCase names, ids instead of URLs. Fields the app doesn't use are dropped (a z.object
// strips unknown keys by default).
const personSchema = z
  .object({
    url: resourceId,
    name: z.string(),
    birth_year: optionalText,
    gender: optionalText,
    height: optionalText, // a string: SWAPI writes some masses as "1,358"
    mass: optionalText,
    hair_color: optionalText,
    eye_color: optionalText,
    homeworld: resourceId,
    films: z.array(resourceId),
  })
  .transform((raw) => ({
    id: raw.url,
    name: raw.name,
    birthYear: raw.birth_year,
    gender: raw.gender,
    heightCm: raw.height,
    massKg: raw.mass,
    hairColor: raw.hair_color,
    eyeColor: raw.eye_color,
    homeworldId: raw.homeworld,
    filmIds: raw.films,
  }))

const peoplePageSchema = z
  .object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(personSchema),
  })
  .transform((raw) => ({
    total: raw.count,
    hasNext: raw.next !== null,
    hasPrevious: raw.previous !== null,
    people: raw.results,
  }))

const planetSchema = z
  .object({
    url: resourceId,
    name: z.string(),
    climate: optionalText,
    terrain: optionalText,
    population: optionalText,
  })
  .transform(({ url, ...rest }) => ({ id: url, ...rest }))

const filmSchema = z
  .object({
    url: resourceId,
    title: z.string(),
    episode_id: z.number(),
    release_date: z.string(),
    director: z.string(),
  })
  .transform((raw) => ({
    id: raw.url,
    title: raw.title,
    episode: raw.episode_id,
    releaseDate: raw.release_date,
    director: raw.director,
  }))

// The types come *from* the schemas (z.infer gives the type after the transform), so the type
// and the runtime check can never disagree.
export type Person = z.infer<typeof personSchema>
export type PeoplePage = z.infer<typeof peoplePageSchema>
export type Planet = z.infer<typeof planetSchema>
export type Film = z.infer<typeof filmSchema>

// ---------------------------------------------------------------------------- requests
export async function fetchPeople(
  search: string,
  page: number,
  signal?: AbortSignal,
): Promise<PeoplePage> {
  // URL and URLSearchParams encode the search text ("R2-D2", "Obi-Wan & co"). Never build a
  // query string by gluing strings together.
  const url = new URL(`${API_ROOT}/people/`)
  if (search) url.searchParams.set('search', search)
  url.searchParams.set('page', String(page))
  return peoplePageSchema.parse(await getJson(url.href, signal))
}

export async function fetchPerson(id: number, signal?: AbortSignal): Promise<Person> {
  return personSchema.parse(await getJson(`${API_ROOT}/people/${id}/`, signal))
}

export async function fetchPlanet(id: number, signal?: AbortSignal): Promise<Planet> {
  return planetSchema.parse(await getJson(`${API_ROOT}/planets/${id}/`, signal))
}

export async function fetchFilm(id: number, signal?: AbortSignal): Promise<Film> {
  return filmSchema.parse(await getJson(`${API_ROOT}/films/${id}/`, signal))
}
