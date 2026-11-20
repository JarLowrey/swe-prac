// Vite serves the app in development (instant start, hot reload) and bundles it for production.
// Vitest reads this same file, so the tests compile the code exactly the way the app does.
import babel from '@rolldown/plugin-babel'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    // JSX, plus Fast Refresh: saving a component swaps it in without losing its state.
    react(),
    // The React Compiler memoizes components and hooks at build time, so the code never needs
    // useMemo, useCallback or React.memo to avoid wasted re-renders. It only optimizes code
    // that follows the Rules of React; the react-hooks lint rules report code it had to skip.
    babel({ presets: [reactCompilerPreset()] }),
  ],
  test: {
    // A simulated DOM inside Node: no browser to start, so the whole suite runs in seconds.
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
  },
})
