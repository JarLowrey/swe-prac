# SWAPI explorer

A small React app that searches and pages through Star Wars characters from
[SWAPI](https://swapi.dev): React 19 with the React Compiler, TypeScript, TanStack Query,
React Router, Zod, and Vitest with Testing Library and MSW.

It's the example for the **React: fetching data the modern way** page of the practice app
(Tech > React, or `tech/01_react_swapi.md`), which walks through every file.

Needs Node 22.22 or newer.

```
npm install
npm run dev          # http://localhost:5173
npm test             # against a fake SWAPI: no network needed
npm run lint
npm run format       # Prettier
npm run build        # type-check, then bundle into dist/
```
