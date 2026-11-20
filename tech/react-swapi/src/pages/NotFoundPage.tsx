import { Link } from 'react-router'

type NotFoundPageProps = { message?: string }

export function NotFoundPage({ message = 'There’s nothing at this address.' }: NotFoundPageProps) {
  return (
    <>
      <title>Not found · SWAPI explorer</title>
      <h1>Not found</h1>
      <p>{message}</p>
      <p>
        <Link to="/">See all characters</Link>
      </p>
    </>
  )
}
