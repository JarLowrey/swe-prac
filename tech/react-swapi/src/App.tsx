import { Link, Route, Routes, useLocation } from 'react-router'
import { ErrorBoundary } from './components/ErrorBoundary'
import { NotFoundPage } from './pages/NotFoundPage'
import { PeoplePage } from './pages/PeoplePage'
import { PersonPage } from './pages/PersonPage'

// The layout every page shares, and the route table: which page renders at which URL.
export function App() {
  const { pathname } = useLocation()
  return (
    <>
      <header className="site-header">
        <Link to="/" className="brand">
          SWAPI explorer
        </Link>
      </header>
      <main>
        {/* key={pathname} gives each page a fresh boundary, so an error caught on one page is
            cleared by navigating to another. A changed key makes React remount the element. */}
        <ErrorBoundary key={pathname}>
          <Routes>
            <Route path="/" element={<PeoplePage />} />
            <Route path="/people/:id" element={<PersonPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </ErrorBoundary>
      </main>
      <footer className="site-footer">
        Data from <a href="https://swapi.dev">SWAPI</a>, the Star Wars API.
      </footer>
    </>
  )
}
