// The tests find things the way a user does, by role and visible text, never by class name or
// component internals. A refactor that keeps the behaviour keeps the tests passing.
import { screen } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { describe, expect, it } from 'vitest'
import { API_ROOT } from '../api/swapi'
import { renderApp } from '../test/render'
import { requests, server } from '../test/server'

describe('character list', () => {
  it('shows the first page, then the next', async () => {
    const { user } = renderApp('/')

    expect(await screen.findByRole('link', { name: 'Luke Skywalker' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('12 characters')

    await user.click(screen.getByRole('link', { name: 'Next →' }))

    expect(await screen.findByRole('link', { name: 'Wilhuff Tarkin' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Luke Skywalker' })).not.toBeInTheDocument()
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
  })

  it('searches once typing stops, with a single request', async () => {
    const { user } = renderApp('/')
    await screen.findByRole('link', { name: 'Luke Skywalker' })

    await user.type(screen.getByRole('searchbox', { name: 'Search characters' }), 'sky')

    expect(await screen.findByRole('link', { name: 'Anakin Skywalker' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'C-3PO' })).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('2 characters match “sky”')
    // Three keystrokes, one search request: the debounce waited for the typing to stop.
    const searches = requests.filter((url) => url.includes('search='))
    expect(searches).toEqual([`${API_ROOT}/people/?search=sky&page=1`])
  })

  it('counts a single match in the singular', async () => {
    renderApp('/?q=vader')

    expect(await screen.findByText('1 character matches “vader”')).toBeInTheDocument()
  })

  it('says so when nothing matches', async () => {
    const { user } = renderApp('/')

    await user.type(screen.getByRole('searchbox'), 'zzz{Enter}')

    expect(await screen.findByText('No characters match “zzz”.')).toBeInTheDocument()
  })

  it('starts from the search and page in the URL', async () => {
    renderApp('/?q=sky')

    expect(await screen.findByRole('link', { name: 'Anakin Skywalker' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('sky')
  })

  it('shows a server error, and recovers on Try again', async () => {
    // Fail the first list request only; the retry gets the normal handler.
    server.use(
      http.get(`${API_ROOT}/people/`, () => HttpResponse.json({}, { status: 500 }), { once: true }),
    )
    const { user } = renderApp('/')

    expect(await screen.findByRole('alert')).toHaveTextContent('server error')

    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('link', { name: 'Luke Skywalker' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})
