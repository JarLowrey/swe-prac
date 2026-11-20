import { Link } from 'react-router'
import { PAGE_SIZE, type Person } from '../api/swapi'

type PeopleTableProps = {
  people: Person[]
  /** The list's URL search ("?q=sky&page=2"), handed to the character page for its back link. */
  listSearch: string
}

// Rows of data with column headings: a real <table>, which screen readers can navigate by row
// and column, rather than a grid of <div>s.
export function PeopleTable({ people, listSearch }: PeopleTableProps) {
  return (
    <table className="people">
      <caption className="visually-hidden">Characters</caption>
      <TableHead />
      <tbody>
        {people.map((person) => (
          // The key is the record's own id, never the array index. With index keys, a new
          // search would make React reuse the first row (and any state inside it) for whoever
          // is now first in the list.
          <tr key={person.id}>
            <th scope="row">
              {/* `state` travels with the navigation without appearing in the URL. The
                  character page uses it to link back to these same results. */}
              <Link to={`/people/${person.id}`} state={{ listSearch }}>
                {person.name}
              </Link>
            </th>
            <td>{person.birthYear ?? '—'}</td>
            <td>{person.gender ?? '—'}</td>
            <td>{person.heightCm ? `${person.heightCm} cm` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

/** Grey bars the size of a page of results, shown before the first page arrives. Reserving
 * the space stops the page from jumping when the rows appear. */
export function PeopleTableSkeleton() {
  return (
    // aria-hidden: the bars mean nothing to a screen reader; the status line says "Loading".
    <table className="people" aria-hidden="true">
      <TableHead />
      <tbody>
        {Array.from({ length: PAGE_SIZE }, (_, row) => (
          // Index keys are fine here: the rows are identical and never reorder.
          <tr key={row}>
            {Array.from({ length: 4 }, (_, cell) => (
              <td key={cell}>
                <span className="skeleton" />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function TableHead() {
  return (
    <thead>
      <tr>
        <th scope="col">Name</th>
        <th scope="col">Born</th>
        <th scope="col">Gender</th>
        <th scope="col">Height</th>
      </tr>
    </thead>
  )
}
