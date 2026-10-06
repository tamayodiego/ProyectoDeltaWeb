# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto
usa [Versionado Semántico](https://semver.org/lang/es/).

## [Sin publicar]

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

[Sin publicar]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/tamayodiego/ProyectoDeltaWeb/releases/tag/v0.1.0
