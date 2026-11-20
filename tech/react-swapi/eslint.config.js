// ESLint catches the mistakes the type checker can't: broken Rules of Hooks, effects with
// missing dependencies, query keys that don't match their query function.
import js from '@eslint/js'
import pluginQuery from '@tanstack/eslint-plugin-query'
import { defineConfig, globalIgnores } from 'eslint/config'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      // The React team's rules: the Rules of Hooks, exhaustive effect dependencies, and the
      // React Compiler's checks (no side effects during render, no refs read during render...).
      reactHooks.configs.flat.recommended,
      // Fast Refresh can only hot-swap files that export nothing but components.
      reactRefresh.configs.vite,
      // TanStack Query: every variable the query function uses must be in the query key.
      pluginQuery.configs['flat/recommended'],
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    // Test helpers export functions, not components; Fast Refresh never loads them.
    files: ['src/test/**', '**/*.test.{ts,tsx}'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
