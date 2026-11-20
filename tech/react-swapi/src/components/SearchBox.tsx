import { useId, useState } from 'react'
import { useDebouncedCallback } from '../hooks/useDebouncedCallback'

type SearchBoxProps = {
  /** The search the results are showing, read from the URL. */
  query: string
  /** Called with the trimmed text 300 ms after typing stops, or at once on Enter. */
  onSearch: (query: string) => void
}

export function SearchBox({ query, onSearch }: SearchBoxProps) {
  // A unique id to tie the <label> to the <input>. A hard-coded id would clash if the component
  // were ever rendered twice on one page.
  const inputId = useId()

  // What's in the box right now. It changes on every keystroke, while the URL (and the request)
  // only change after a pause, so the two are separate pieces of state on purpose.
  const [draft, setDraft] = useState(query)

  // The URL can also change without typing: Back and Forward, or the site title link. When it
  // does, show the new search in the box. Comparing with the previous `query` and setting state
  // during render is how React's docs adjust state when a prop changes. An effect would paint
  // the stale text first and only then correct it.
  const [previousQuery, setPreviousQuery] = useState(query)
  if (query !== previousQuery) {
    setPreviousQuery(query)
    // Our own debounced search changes `query` too. Leave the draft alone then: if the user
    // paused after "luke " (about to type "sky..."), resetting it would delete the space.
    if (query !== draft.trim()) setDraft(query)
  }

  const debouncedSearch = useDebouncedCallback((text: string) => onSearch(text.trim()), 300)

  return (
    // role="search" makes this a landmark that screen-reader users can jump straight to.
    <form
      role="search"
      className="search"
      onSubmit={(event) => {
        // Enter searches straight away. Without preventDefault, the browser would submit the
        // form the old-fashioned way and reload the page.
        event.preventDefault()
        debouncedSearch.cancel()
        onSearch(draft.trim())
      }}
    >
      <label htmlFor={inputId}>Search characters</label>
      <input
        id={inputId}
        type="search"
        value={draft}
        placeholder="Luke, Leia, R2-D2…"
        autoComplete="off"
        onChange={(event) => {
          setDraft(event.target.value)
          debouncedSearch.run(event.target.value)
        }}
      />
    </form>
  )
}
