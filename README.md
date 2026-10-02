# ProyectoDeltaWeb

Versión web de [ProyectoDelta](https://github.com/tamayodiego/ProyectoDelta), la app de
escritorio (Java + Swing, 2018) para investigar **delta-matroides**: generarlas a partir de
matrices simétricas o antisimétricas sobre GF(2) y GF(3), y estudiar sus propiedades.

Backend en Python + FastAPI, frontend en React + TypeScript + Vite, PostgreSQL, y despliegue
en k3s con GitHub Actions + Helm.

## Requisitos

| Herramienta | Versión |
|---|---|
| [uv](https://docs.astral.sh/uv/) | 0.12 (con Python 3.12) |
| Node + pnpm | Node 24, pnpm 12 |
| Docker (OrbStack o Docker Desktop) | Compose v2 |

## Empezar

```bash
make install   # dependencias de backend y frontend
make hooks     # activa pre-commit (una sola vez)
make db        # PostgreSQL local en localhost:5432
make backend   # API en http://127.0.0.1:8000/docs
make frontend  # frontend en modo desarrollo (en otra terminal)
```

`make` sin argumentos muestra todos los atajos (`test`, `lint`, `format`, `build`, ...).

## Estructura

```
backend/            API (FastAPI). La lógica de delta-matroides vive en src/deltaweb/domain/
backend/tests/golden/  resultados de referencia de la app Java (ver su README)
frontend/           Aplicación web (React + TypeScript + Vite)
infra/              Infraestructura: Ansible, k8s, Helm, monitoreo (fases 5 a 7)
docs/               Documentación y decisiones
docker-compose.yml  PostgreSQL para desarrollo local
Makefile            Atajos de desarrollo
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

Los commits siguen [Conventional Commits](https://www.conventionalcommits.org/) en inglés:
`feat(backend): ...`, `fix(frontend): ...`, `chore: ...`.

## Licencia

[GPL-3.0](LICENSE), igual que ProyectoDelta.
