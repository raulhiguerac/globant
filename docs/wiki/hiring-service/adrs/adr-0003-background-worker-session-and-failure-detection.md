---
title: "ADR-0003 — Sesión propia del worker + detección de fallos por timeout, no cola de tareas"
status: stable
last-verified: 2026-07-05
sources:
  - sources/hiring-service/2026-07-05-ingestion-robustness-hardening.md
related:
  - hiring-service-design
  - metrics
---

## Contexto

El endpoint `POST /ingest/employees` responde `202` y delega el procesamiento a `ProcessEmployeesChunkWorker.stream_and_process` vía `BackgroundTasks` de FastAPI. Dos problemas surgieron de una revisión de robustez:

1. El worker recibía su `UnitOfWork` (y por lo tanto su `Session` de SQLAlchemy) desde `Depends(get_uow)` → `Depends(get_session)`. Desde FastAPI 0.106, el cleanup de dependencias con `yield` corre **antes** de que se ejecuten los `BackgroundTasks`, no después. La sesión funcionaba solo porque SQLAlchemy permite reabrir una conexión después de `close()` — un comportamiento frágil, no garantizado por diseño.
2. Si el proceso del worker muere a mitad de camino (storage caído, DB caída, o el proceso completo recibe `SIGKILL`/se reinicia el contenedor), el batch queda en `pending` para siempre y el cliente pollea infinito sin señal de error.

## Decisión

**Para (1):** el worker no recibe ni sesión ni UoW vía `Depends`. `get_process_employees_runner()` devuelve la *función* `run_process_employees_chunk` (no un objeto ya construido); esa función abre su propia `Session(engine)` recién cuando el `BackgroundTask` efectivamente corre, con un lifetime acotado exactamente a esa ejecución.

**Para (2):** dos mecanismos, ninguno una cola de tareas real:
- `stream_and_process` envuelve todo el flujo en un `try/except Exception` catch-all que marca el batch como `failed` (nuevo estado en `IngestionBatchStatus`) y re-lanza. Cubre cualquier excepción que el propio proceso llegue a manejar.
- `GetBatchStatusUseCase` agrega una heurística de timeout: un batch `pending` con `created_at` más viejo que `BATCH_TIMEOUT_SECONDS` (600s) se reporta — y persiste — como `failed` en el siguiente poll. Cubre el caso que el catch-all no puede: el proceso muere sin llegar a ejecutar su propio `except`.

## Razón

**Sobre (1):** agregar una `Depends` *dedicada* para el worker no resuelve nada — el problema no es qué dependencia se usa, es el momento en que FastAPI cierra el generador de cualquier dependencia `yield`, sin importar cuántas capas de DI la envuelvan. La única solución real es que el objeto con estado (la `Session`) nazca y muera dentro del propio `BackgroundTask`, no en el ciclo de vida del request. `cache_client` y `storage` sí siguen viniendo de getters `@lru_cache` (sin `yield`, sin cleanup) — son singletons de proceso, seguros de usar tal cual dentro del worker.

**Sobre (2):** una cola de tareas real (Celery/RQ/Cloud Tasks) con reintentos y detección de tareas huérfanas es la solución correcta en producción, pero es overkill para el scope de este challenge. El timeout heurístico es deliberadamente generoso (600s) porque los batches están acotados a 1000 filas (`batch_guard._MAX_ROWS`) — un run real, incluso con el fallback fila-a-fila, termina en segundos. El riesgo de un falso `failed` mientras el batch sigue vivo es por lo tanto muy bajo.

## Consecuencias

- El `Depends` de employees (`get_process_employees_runner`) devuelve un `Callable`, no un worker armado — los tests siguen pudiendo usar `dependency_overrides`, solo que ahora sobreescriben la función en vez del objeto.
- El worker (`ProcessEmployeesChunkWorker`) quedó como pura orquestación; la lógica de negocio se extrajo a `app/workers/helpers/` (`batch_status.py`, `employee_writer.py`, `storage_reader.py`, `chunking.py`), cada una testeada de forma aislada.
- Sigue existiendo un gap residual: si el proceso muere *y* el cliente jamás vuelve a pollear el status, el batch queda `failed` recién en el próximo poll, no proactivamente. Aceptado — no hay observador externo sin una cola real.
- Requiere una migración de Alembic hand-written (`1099b8b292cc`) porque Alembic no autogenera `ALTER TYPE ... ADD VALUE` para enums nativos de Postgres.
