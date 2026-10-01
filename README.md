# ProyectoDeltaWeb

Monorepo del proyecto Delta Web.

## Estructura

```
backend/    API / servidor
frontend/   Aplicación web cliente
```

## Flujo de ramas (Git Flow)

| Rama        | Propósito                                   | Se crea desde | Se fusiona en      |
|-------------|---------------------------------------------|---------------|--------------------|
| `main`      | Código en producción (siempre estable)      | —             | —                  |
| `develop`   | Integración de nuevas funcionalidades       | `main`        | `main` (vía release) |
| `feature/*` | Nueva funcionalidad                         | `develop`     | `develop`          |
| `fix/*`     | Corrección de errores no urgentes           | `develop`     | `develop`          |
| `release/*` | Preparación de una versión                  | `develop`     | `main` y `develop` |
| `hotfix/*`  | Corrección urgente en producción            | `main`        | `main` y `develop` |

Convención de nombres: indica el proyecto afectado, p. ej.
`feature/backend-auth`, `feature/frontend-login`, `fix/backend-validacion-email`.

`main` y `develop` están protegidas: los cambios entran solo mediante Pull Request.
