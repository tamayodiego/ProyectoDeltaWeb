# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

## [0.6.0] - 2026-10-16

Base del frontend: estructura de la app, navegación, temas, idiomas y cliente tipado de la API.

### Añadido

- **Estructura de la app** con React Router: área de trabajo (`/workspace`), páginas de
  autenticación (`/login`, `/register`, `/forgot-password`, `/reset-password`,
  `/verify-email`) y página 404. Las páginas de contenido son provisionales
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Cliente tipado de la API** con `openapi-fetch`: los tipos (`src/api/schema.d.ts`) se
  generan del OpenAPI de FastAPI con `make api-types`. `/api` va al backend por el proxy
  de Vite en desarrollo y por nginx en producción, así la cookie de sesión funciona sin
  CORS ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Estado de la API** en la cabecera (`/readyz` con TanStack Query)
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Temas** claro, oscuro o el del sistema, recordados en el navegador y aplicados antes
  de que cargue React (sin parpadeo)
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Idiomas** español e inglés con i18next y detección del idioma del navegador
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Estilos** con Tailwind y componentes de shadcn
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).
- **Herramientas del frontend:** Vitest con Testing Library, Prettier y `tsc` en
  `make lint` y `make test` ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).

### Eliminado

- La página y los recursos de la plantilla de Vite
  ([#35](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/35)).

## [0.5.0] - 2026-10-15

Fase 2c: iniciar sesión con Google y GitHub.

### Añadido

- **Login con Google y GitHub** (OAuth 2.0, Authorization Code con PKCE):
  `GET /auth/oauth/{provider}/start` redirige al proveedor y `/callback` comprueba el
  `state`, pide el perfil e inicia sesión. Un proveedor sin credenciales queda
  deshabilitado (404) ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).
- **Cuentas vinculadas:** tabla `oauth_accounts` (migración `0006`), única por proveedor e
  id del proveedor; un usuario puede vincular ambos proveedores
  ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).
- **Buscar, vincular o crear** al volver del proveedor: la cuenta ya vinculada; si no, el
  usuario con ese email (solo si el proveedor lo verificó); si no, un usuario nuevo sin
  contraseña ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).
- Errores como redirecciones a `/login?error=oauth|no_email|email_in_use`, para que el
  frontend muestre un mensaje concreto
  ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).
- `backend/.env.example` con las variables de Google y GitHub
  ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).

### Seguridad

- Al vincular una cuenta local cuyo email no estaba verificado se borran su contraseña y
  sus sesiones, para evitar el "pre-account takeover"
  ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).

### Corregido

- `/auth/oauth/{provider}/callback` respondía 500 con un `state` no ASCII (p. ej. `ñ`);
  ahora redirige con error ([#32](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/32)).

## [0.4.0] - 2026-10-15

Fase 2b: cuentas de usuario, sesiones, correo y protección contra abusos.

### Añadido

- **Mailpit** en `docker-compose.yml` para atrapar los correos de desarrollo; `make mail`
  lo levanta y abre la bandeja ([#24](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/24)).
- **Modelos de autenticación:** `User` con `password_hash`, `email_verified_at` y email en
  minúsculas; tabla `user_sessions` (migración `0004`)
  ([#25](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/25)).
- **Registro, login y logout** (`/auth/register`, `/auth/login`, `/auth/logout`,
  `/auth/me`): contraseñas con Argon2id y reglas de fuerza; sesión con un token de 256
  bits en una cookie `httpOnly` y `SameSite=Lax`, guardando solo su hash; mismo 401 para
  email desconocido y contraseña incorrecta
  ([#26](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/26)).
- **Rate limiting en `/auth`:** login 10/min por IP y 5/min por email; registro 5/hora
  por IP; responde 429 con `Retry-After`
  ([#27](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/27)).
- **Correo:** servicio SMTP con plantillas HTML y de texto ("Verifica tu correo",
  "Recupera tu contraseña"), configurable para Mailpit, Resend o Brevo
  ([#28](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/28)).
- **Verificar correo y recuperar contraseña** con tokens de un solo uso (tabla
  `email_tokens`, migración `0005`): `/auth/verify/request`, `/auth/verify`,
  `/auth/password/forgot` (siempre 202) y `/auth/password/reset` (cierra todas las
  sesiones). El registro envía el correo de verificación
  ([#28](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/28)).
- **Rate limiting en la generación:** `/delta-matroids/generate` 20/min por IP y guardar
  30/min por usuario ([#29](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/29)).

### Cambiado

- **Todas las rutas de carpetas y delta-matroides requieren sesión**: el usuario demo
  temporal desapareció ([#26](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/26)).
- Argon2id usa el perfil de OWASP (19 MiB, t=2, p=1) en lugar del predeterminado de
  64 MiB, con como mucho 2 hashes a la vez; los hashes antiguos se actualizan al iniciar
  sesión ([#27](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/27)).
- La cookie de sesión lleva `Secure` en todos los entornos salvo `local`
  ([#27](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/27)).

## [0.3.0] - 2026-10-05

Fase 2a: base de datos, carpetas y delta-matroides guardadas.

### Añadido

- **Base de datos:** PostgreSQL con SQLAlchemy 2 y migraciones Alembic; sesión por
  petición; `/readyz` comprueba la BD (503 si no la alcanza). Atajos `make migrate` y
  `make migration`. Las pruebas de BD usan un Postgres desechable con Testcontainers
  ([#17](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/17)).
- **Carpetas:** modelo `Folder` (migración `0002`), un árbol por usuario con borrado en
  cascada y nombres únicos en el mismo lugar (distingue mayúsculas)
  ([#18](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/18)).
- **API de carpetas:** `POST`, `GET`, `PATCH` y `DELETE /folders`. Mover una carpeta
  dentro de sí misma o de un descendiente da 400; borrar una carpeta con contenido pide
  `force=true` ([#19](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/19)).
- **Generación por la API:** `POST /delta-matroids/generate` calcula sin guardar. El
  trabajo 2ⁿ corre en un pool de procesos, con límite de tamaño (n ≤ 15) y tiempo máximo
  ([#20](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/20)).
- **Delta-matroides guardadas:** modelo `DeltaMatroidRecord` (migración `0003`) y CRUD en
  `/delta-matroids`. Se guardan la matriz y la familia; la huella y las frecuencias se
  recalculan al leer. La lista devuelve resúmenes sin cargar las familias
  ([#21](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/21)).
- Usuario demo temporal: todas las peticiones son del mismo usuario hasta el login (2b)
  ([#17](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/17)).

### Cambiado

- Borrar una carpeta cuenta también las delta-matroides del subárbol: el 409 incluye
  `delta_matroids` y `force=true` las borra
  ([#21](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/21)).
- `make test` necesita Docker encendido para las pruebas de BD.

## [0.2.0] - 2026-10-04

Fase 1: lógica de delta-matroides en Python, validada contra la app Java.

### Añadido

- **Validación de matrices:** `validate_matrix` e `InvalidMatrixError`. GF(2) exige una
  matriz simétrica 0/1 y GF(3) una antisimétrica -1/0/1; la matriz cero vale en ambos
  ([#10](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/10)).
- **Huella y tabla de frecuencias:** atributos `fingerprint` (factibles por tamaño, de 0 a n)
  y `frequencies` (factibles que contienen cada elemento), calculados una vez en el
  constructor ([#11](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/11)).
- **Reetiquetado:** `relabel({vieja: nueva})` devuelve una delta-matroide nueva con las
  etiquetas cambiadas (mapeo parcial e intercambios), sin tocar la familia; `encode` y
  `decode` traducen entre etiquetas y bitmasks
  ([#12](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/12)).
- **Golden master:** pruebas contra los resultados de la app Java. Pasan todos los casos
  compatibles con la regla de campo (SIM/GF2 y ANTI/GF3); los demás se saltan a propósito
  ([#13](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/13)).
- **Benchmark:** `backend/scripts/benchmark.py`. n = 15 tarda ~0.28 s en un Apple M3
  (objetivo: < 1.5 s) ([#14](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/14)).
- Configuración de VS Code para correr las pruebas del backend
  ([#10](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/10)).

### Cambiado

- `relabel` recibe un diccionario y devuelve un objeto nuevo en vez de modificar el actual
  ([#12](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/12)).

### Corregido

- Crear una delta-matroide desde una familia `int64` o una lista de Python ya no truena:
  la familia se convierte a `uint64` al entrar y se rechazan bitmasks negativos o no
  enteros ([#11](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/11)).

## [0.1.0] - 2026-10-02

Fase 0: estructura del proyecto, herramientas y primera versión del dominio.

### Añadido

- **Backend:** proyecto FastAPI con Python 3.12 gestionado con uv, endpoints `/healthz` y
  `/readyz`, configuración por variables `DELTAWEB_*` y herramientas de calidad (pytest,
  Ruff, mypy) ([#1](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/1)).
- **Dominio:** clase `DeltaMatroid`, construible desde una matriz simétrica o antisimétrica
  sobre GF(2) o GF(3), con determinantes exactos (`python-flint`), o desde una familia de
  factibles guardada como bitmasks `uint64`
  ([#1](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/1)).
- **Frontend:** proyecto React 19 + TypeScript + Vite gestionado con pnpm
  ([#3](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/3)).
- **Infraestructura:** Dockerfiles de producción para backend y frontend (nginx con proxy
  de `/api`) y `docker-compose.yml` con PostgreSQL 17 para desarrollo local
  ([#4](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/4)).
- **Herramientas:** `Makefile` con atajos, hooks de pre-commit, `.editorconfig`,
  `CLAUDE.md`, documentación en `docs/` e `infra/`, y el golden master de 164
  delta-matroides de la app Java para validar la Fase 1
  ([#6](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/6)).
- Licencia GPL-3.0-or-later ([#6](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/6),
  [#7](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/7)).

### Corregido

- Las pruebas fallaban con `ModuleNotFoundError` cuando macOS ocultaba el `.pth` de la
  instalación editable; pytest ahora añade `src/` a la ruta
  ([#2](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/2)).
- La imagen del backend usa uv 0.12, la misma versión que en local
  ([#5](https://github.com/tamayodiego/ProyectoDeltaWeb/pull/5)).

[Sin publicar]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/releases/tag/v0.1.0
