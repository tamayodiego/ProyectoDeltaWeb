import createClient from 'openapi-fetch'

import type { paths } from './schema'

/*
 * Typed client for the backend. The types in schema.d.ts are generated from
 * FastAPI's OpenAPI with `pnpm api:types` (backend running): never written by hand.
 *
 *   const { data, error } = await api.GET('/readyz')
 *
 * Paths, bodies and responses are checked by TypeScript. "/api" is forwarded to
 * the backend by Vite's proxy in development and by nginx in production; same
 * origin, so the session cookie goes along without CORS.
 */
export const api = createClient<paths>({ baseUrl: '/api' })
