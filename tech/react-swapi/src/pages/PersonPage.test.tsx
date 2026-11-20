import { screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { API_ROOT } from '../api/swapi'
import { renderApp } from '../test/render'
import { requests } from '../test/server'

describe('character page', () => {
  it('shows the character, their homeworld, and their films in episode order', async () => {
    renderApp('/people/1')

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Luke Skywalker' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Tatooine')).toBeInTheDocument()
    const films = screen.getByRole('list', { name: 'Films' })
    await waitFor(() => expect(within(films).getAllByRole('listitem')).toHaveLength(4))
    expect(
      within(films)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual([
      'Episode 3: Revenge of the Sith (2005)',
      'Episode 4: A New Hope (1977)',
      'Episode 5: The Empire Strikes Back (1980)',
      'Episode 6: Return of the Jedi (1983)',
    ])
  })

  it('opens from the list with no new request, and goes back to the same search', async () => {
    const { user } = renderApp('/?q=sky')

    await user.click(await screen.findByRole('link', { name: 'Luke Skywalker' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Luke Skywalker' }),
    ).toBeInTheDocument()
    // The list's queryFn copied Luke into his own cache entry.
    expect(requests).not.toContain(`${API_ROOT}/people/1/`)

    await user.click(screen.getByRole('link', { name: '← Back to characters' }))

    expect(await screen.findByRole('searchbox')).toHaveValue('sky')
  })

  it('says there is no such character', async () => {
    renderApp('/people/999')

    expect(await screen.findByText('There’s no character with id 999.')).toBeInTheDocument()
  })

  it('rejects an id that is not a number, without a request', () => {
    renderApp('/people/abc')

    expect(screen.getByText('“abc” isn’t a character id.')).toBeInTheDocument()
    expect(requests).toEqual([])
  })
})
