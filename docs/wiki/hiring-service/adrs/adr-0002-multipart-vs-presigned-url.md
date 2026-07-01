---
title: "ADR-0002 — Multipart vs presigned URL para upload de CSV"
status: stable
last-verified: 2026-06-30
sources:
  - sources/hiring-service/2026-06-30-hiring-service-design.md
related:
  - hiring-service-design
---

## Contexto

El challenge no tiene front-end. El archivo CSV llega al servicio vía HTTP. La pregunta es si el API recibe el archivo directamente (multipart) o genera una presigned URL para que el cliente haga PUT directo al storage.

## Decisión

**Implementado:** multipart directo al API (`POST /v1/ingest` con `UploadFile`).

**Arquitectura óptima (defensible en system design):** presigned URL — el cliente hace PUT directo a MinIO/GCS y el API nunca paga el bandwidth de la transferencia.

## Razón

Sin front-end no hay cliente web que consuma una presigned URL para hacer el PUT. Multipart es la única opción viable en este contexto.

En producción con cliente web, la arquitectura correcta es:
1. `POST /v1/ingest` → API genera presigned URL → devuelve 201 + URL
2. Cliente hace PUT directo al storage
3. Worker procesa el archivo en chunks (100-200 MB) → bulk insert

Esto elimina el bandwidth del API server y permite escalar el procesamiento independientemente del API.

## Consecuencias

- La implementación actual (multipart) es funcional para el challenge.
- El worker para procesamiento async de `IngestEmployeesUseCase` sigue siendo relevante — el API sube el stream a storage y delega al worker, sin bloquear el request.
- `batch_id` actúa como correlation ID para rastrear el procesamiento del worker.
