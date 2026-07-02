---
title: "ADR-0001 — Single commit para batch + records"
status: stable
last-verified: 2026-06-30
sources:
  - sources/hiring-service/2026-06-30-hiring-service-design.md
related:
  - hiring-service-design
---

## Contexto

Al ingerir un CSV, el UC genera un `IngestionBatch` y luego inserta los records con ese `batch_id` como FK. La pregunta es si commitear el batch primero y los records después, o todo en una sola transacción.

## Decisión

Un único `commit()` cubre `batch.add` + `bulk_insert` juntos.

## Razón

Si se hace `commit()` del batch y luego falla el bulk insert, queda un `ingestion_batch` huérfano en la DB sin registros asociados — rompe la trazabilidad. Con un único commit, cualquier fallo hace rollback de todo y no quedan datos inconsistentes.

## Consecuencias

- El batch y los records son atómicos — o entran los dos o no entra ninguno.
- El fallback row-by-row también commitea una sola vez al final (`if ok_count > 0`).
- El `batch_id` se genera en el UC con `uuid.uuid4()` antes de cualquier operación DB.
