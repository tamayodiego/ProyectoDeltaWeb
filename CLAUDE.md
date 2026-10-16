# CLAUDE.md

Guía para Claude (y para quien trabaje en el proyecto) en este repositorio.

## Proyecto

ProyectoDeltaWeb: versión web de ProyectoDelta (app de escritorio Java + Swing para
investigar delta-matroides). Monorepo con backend Python 3.12 + FastAPI, frontend
React + TypeScript + Vite, PostgreSQL, y despliegue en k3s (VPS OVHcloud) con
GitHub Actions + Helm. El plan completo está en el documento "Roadmap ProyectoDelta Web".

## Forma de trabajar con el usuario (importante)

- **Es un ejercicio de aprendizaje.** Cada fase empieza con una pre-planeación que dice
  qué hace el usuario y qué hace Claude. No hacer las partes que le tocan al usuario;
  guiarlo, explicar y revisar su trabajo como en un code review.
- Conversación con el usuario en **español**. Código, commits, nombres de API y
  comentarios en **inglés**. README, CLAUDE.md y docs en español.
- Cada cambio en su propia rama desde `develop`; el usuario hace commit, push, PR y merge.
  **Preguntar siempre antes de subir algo.** Pedir revisión antes de cada merge.
- Explicar brevemente qué se hizo y por qué.

## Ramas (Git Flow)

`main` (producción, solo releases) ← `release/*` ← `develop` ← `feature/*`, `fix/*`.
`main` y `develop` están protegidas: todo entra por PR. Una release por fase
(`v0.1.0` al cerrar la Fase 0, ...). A partir de la Fase 6, un tag en `main` dispara
el despliegue a producción.

## Comandos

| Tarea | Comando |
|---|---|
| Todo lo disponible | `make` |
| Dependencias | `make install` |
| Postgres local | `make db` / `make db-down` / `make db-shell` |
| Correos de desarrollo | `make mail` (Mailpit: SMTP en 1025, bandeja en http://localhost:8025) |
| Migraciones | `make migrate` / `make migration m="..."` (revisar antes de aplicar) |
| API en desarrollo | `make backend` (http://127.0.0.1:8000/docs) |
| Frontend en desarrollo | `make frontend` (http://localhost:5173; `/api` va al backend por el proxy de Vite) |
| Tipos de la API | `make api-types` (con `make backend` corriendo): regenera `frontend/src/api/schema.d.ts` |
| Pruebas | `make test` (backend con pytest, las de BD necesitan Docker; frontend con Vitest) |
| Estilo y tipos | `make lint` (Ruff, mypy, ESLint, Prettier, tsc) / `make format` |
| Imágenes Docker | `make build` |

## Estructura del frontend

`frontend/src/`: `app/` (`App.tsx`, `router.tsx` con React Router), `pages/`, `components/`
(`layout/` de la app y `ui/` de shadcn), `api/` (`client.ts` con `openapi-fetch` tipado
por `schema.d.ts`, que es generado: nunca editarlo a mano), `i18n/` (i18next, `es` y `en`),
`theme/` (claro, oscuro o el del sistema) y `lib/`. Estilos con Tailwind; datos del servidor con TanStack
Query. Las rutas del frontend `/verify-email` y `/reset-password` reciben los enlaces de
los correos, y `/login?error=...` los errores de OAuth.

## Estructura del backend

`backend/src/deltaweb/`: `main.py` (`create_app`), `config.py` (variables `DELTAWEB_*`),
`api/` (routers), `schemas/` (Pydantic: solo datos que viajan en JSON), `services/`
(une API, dominio y BD), `domain/` (lógica pura de delta-matroides, sin FastAPI ni BD),
`db.py` (engine, sesión, `Base`) y `models/` (tablas: `User`, `UserSession`,
`EmailToken`, `OAuthAccount`, `Folder`, `DeltaMatroidRecord`; cada modelo nuevo se importa en
`models/__init__.py`). Las migraciones están en `backend/migrations/versions/` con IDs
`0001`, `0002`, ...

## Decisiones de diseño del dominio

- `DeltaMatroid` es una clase con sus operaciones como métodos (como en la app Java y
  la librería C++). Las operaciones deben **regresar una delta-matroide nueva** en vez
  de modificar la actual (`relabel` ya lo hace).
- Regla de campo: GF(2) solo acepta matrices simétricas 0/1 y GF(3) solo antisimétricas
  -1/0/1 (la matriz cero vale en ambos). Por eso los casos SIM/GF3 y ANTI/GF2 del golden
  se saltan a propósito.
- `fingerprint` y `frequencies` son atributos calculados en el constructor (la familia no
  cambia). Las etiquetas del conjunto base son solo nombres: `relabel` no toca la familia.
- Factibles como **bitmasks** (`numpy.uint64`): bit k = elemento k + 1.
- Conjunto base = `{1, ..., n}`, con `n` explícito (`len(matrix)` o `size`), para que las
  etiquetas nunca se desalineen de los bits. Convención informática acordada con el
  usuario; en su investigación el conjunto base se define por la unión de los factibles.
- Determinante exacto con `python-flint`. Campo GF(2) o GF(3): factible si `det mod p != 0`.

## Referencias

- `backend/tests/golden/`: golden master de 164 delta-matroides de la app Java. La Fase 1
  no termina hasta que Python reproduzca los resultados. Ver su README (los `sha`
  dependen del orden de las listas de Java).
- Proyectos hermanos en `../ProyectoDelta` (Java) y `../deltamatroids` (C++, cómputo de
  alto rendimiento del usuario): segunda referencia y guía de optimización.

## Trampas conocidas

- **Misma versión de herramientas en todos lados:** la versión de uv del
  `backend/Dockerfile` debe coincidir con la local (hoy 0.12), porque `uv.lock` la escribe
  el uv local. Lo mismo para pnpm en `frontend/Dockerfile`.
- El `docker-compose.yml` tiene `db` y `mailpit`; backend y frontend se corren en la Mac
  durante el desarrollo y se agregan a Compose en la Fase 4.
- Infraestructura limitada: VPS de 2 vCPU y 4 GB de RAM. Pensar en el consumo de memoria.
- Generación 2^n en subconjuntos; se usa con n <= 15 (~0.3 s en un Apple M3, ver
  `backend/scripts/benchmark.py`). En la API corre en un pool de 2 procesos (`spawn`);
  `future.cancel()` no detiene una tarea que ya está corriendo.
- `backend/Dockerfile` todavía no copia `alembic.ini` ni `migrations/`: desde la imagen no
  se pueden aplicar migraciones (pendiente para el despliegue).
- Autenticación (bloque 2b): `get_current_user` (`api/deps.py`) lee la cookie de sesión
  y responde 401 sin ella; los routers solo dependen de `CurrentUser`. En los tests,
  `client` ya tiene sesión iniciada y `anonymous_client` no.
- Argon2id con el perfil de OWASP (19 MiB, t=2, p=1) y como mucho
  `password_hash_concurrency` hashes a la vez, para acotar la memoria en el VPS.
- El rate limiting de `/auth` vive en memoria del proceso: vale para una sola réplica.
  Detrás de un proxy (nginx, ingress) la IP del cliente solo es la real si uvicorn
  confía en `X-Forwarded-For` (`--forwarded-allow-ips`); si no, todos comparten la IP del
  proxy y el límite por IP pasa a ser global (pendiente para el despliegue).
- `cookie_secure` es automático: la cookie solo va sin `Secure` con `environment=local`.
- Correo (`services/email.py`): SMTP según `smtp_*` en `config.py` (Mailpit en local;
  Resend o Brevo en producción). Los endpoints lo envían después de responder
  (`BackgroundTasks`), así `/auth/password/forgot` responde igual exista o no la cuenta.
  En los tests, el fixture autouse `inbox` (conftest) atrapa todos los correos.
- Tokens de un solo uso por correo (`email_tokens`, `services/email_tokens.py`): verificar
  (24 h) y recuperar contraseña (1 h). Se canjean con un `UPDATE ... WHERE used_at IS NULL`
  atómico. Los enlaces apuntan al frontend (`app_url`): `/verify-email` y `/reset-password`.
- Rate limiting: `check_rate` y `client_ip` viven en `api/deps.py`; cada router define
  sus limitadores y una tupla `LIMITERS`, que el fixture `reset_rate_limits` reinicia.
- Login con Google/GitHub (bloque 2c): `services/oauth.py` habla con los proveedores
  (Authorization Code + PKCE) y `api/oauth.py` tiene `/auth/oauth/{provider}/start` y
  `/callback`. Un proveedor sin `*_client_id`/`*_client_secret` queda deshabilitado (404).
  La *redirect URI* registrada debe ser exactamente `{api_url}/auth/oauth/{provider}/callback`.
  Vincular por email solo si el proveedor lo verificó; al vincular una cuenta local sin
  verificar se borra su contraseña ("pre-account takeover"). Los errores redirigen a
  `{app_url}/login?error=oauth|no_email|email_in_use`.
- `Settings()` también lee `backend/.env`, incluso en los tests: si un test necesita un
  valor concreto, pásalo explícito (p. ej. `google_client_id=None`). Pendiente: que los
  tests no lean el `.env`.
- Pendientes de auth: borrar sesiones y tokens caducados; decidir si el 409 del registro
  (que revela si un email tiene cuenta) se mantiene.
- Fuera de pytest, `uv run python` puede fallar con `No module named 'deltaweb'` porque
  macOS oculta el `.pth` de `.venv`; usar `PYTHONPATH=src`.
