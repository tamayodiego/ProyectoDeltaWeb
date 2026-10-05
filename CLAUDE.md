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
| API en desarrollo | `make backend` (http://127.0.0.1:8000/docs) |
| Frontend en desarrollo | `make frontend` |
| Pruebas | `make test` (o `cd backend && uv run pytest`) |
| Estilo y tipos | `make lint` / `make format` |
| Imágenes Docker | `make build` |

## Estructura del backend

`backend/src/deltaweb/`: `main.py` (`create_app`), `config.py` (variables `DELTAWEB_*`),
`api/` (routers), `schemas/` (Pydantic: solo datos que viajan en JSON), `services/`
(une API, dominio y BD) y `domain/` (lógica pura de delta-matroides, sin FastAPI ni BD).

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
- El `docker-compose.yml` solo tiene `db`; backend y frontend se corren en la Mac durante
  el desarrollo y se agregan a Compose en la Fase 4.
- Infraestructura limitada: VPS de 2 vCPU y 4 GB de RAM. Pensar en el consumo de memoria.
- Generación 2^n en subconjuntos; se usa con n <= 15 (~1.2 s en Python puro).
