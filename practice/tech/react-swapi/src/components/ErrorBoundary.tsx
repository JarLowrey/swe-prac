import { Component, type ErrorInfo, type ReactNode } from 'react'

type ErrorBoundaryProps = { children: ReactNode }
type ErrorBoundaryState = { error: Error | null }

// Catches an error thrown while rendering anything inside it and shows a message instead of a
// blank page (without a boundary, React unmounts the whole app). It's the one thing still
// written as a class: there's no hook for getDerivedStateFromError or componentDidCatch. Many
// apps use the react-error-boundary package, which wraps this same class.
//
// It only sees errors thrown during rendering. Errors in event handlers and in async code
// happen outside rendering, and a failed request isn't one either: TanStack Query returns it as
// the query's `error`, and the pages show that themselves. So this is the last line of defence,
// for bugs.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  // Called during rendering, after a child throws: return the state that shows the fallback.
  static getDerivedStateFromError(error: unknown): ErrorBoundaryState {
    return { error: error instanceof Error ? error : new Error(String(error)) }
  }

  // Called after the fallback is on screen: the place to report the error. A real app sends
  // it to an error tracker here, with the component stack showing where it was thrown.
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error" role="alert">
          <p>Something went wrong showing this page.</p>
          <button type="button" onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
