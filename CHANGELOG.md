# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

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

[Sin publicar]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/releases/tag/v0.1.0
