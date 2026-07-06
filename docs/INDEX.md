# Wiki — Globant Data Engineering Challenge

Wiki del proyecto `hiring-service`. Documenta decisiones de diseño, arquitectura y patrones del challenge.

---

## hiring-service

### domain/
- [hiring-service-design](wiki/hiring-service/domain/hiring-service-design.md) — ingestion UC pattern: bulk + fallback row-by-row, batch tracing, schemas
- [metrics](wiki/hiring-service/domain/metrics.md) — DuckDB OLAP endpoints, cache-aside pattern, SQL queries (Section 2)
- [testing](wiki/hiring-service/domain/testing.md) — unit vs integration split, testcontainers fixtures, pitfalls

### infra/
- [gcp-infra](wiki/hiring-service/infra/gcp-infra.md) — Terraform modules, API enablement, GCS storage, CI/CD workflows

### adrs/
- [ADR-0001 — Single commit para batch + records](wiki/hiring-service/adrs/adr-0001-single-commit-batch-records.md)
- [ADR-0002 — Multipart vs presigned URL (sin front)](wiki/hiring-service/adrs/adr-0002-multipart-vs-presigned-url.md)
- [ADR-0003 — Sesión propia del worker + detección de fallos por timeout](wiki/hiring-service/adrs/adr-0003-background-worker-session-and-failure-detection.md)

---

## Sources

Capturas de conversación en `docs/sources/hiring-service/`:
- [2026-06-30 — Hiring Service Design Decisions](sources/hiring-service/2026-06-30-hiring-service-design.md)
- [2026-06-30 — Ingestion Wiring Completion](sources/hiring-service/2026-06-30-ingestion-wiring-completion.md)
- [2026-07-01 — GCP Infrastructure & CI/CD](sources/hiring-service/2026-07-01-gcp-infra-and-cicd.md)
- [2026-07-01 — README, Diagram & Project Finalization](sources/hiring-service/2026-07-01-readme-diagram-finalization.md)
- [2026-07-05 — Ingestion Robustness Hardening](sources/hiring-service/2026-07-05-ingestion-robustness-hardening.md)
- [2026-07-05 — Integration Tests & Terraform Hardening](sources/hiring-service/2026-07-05-integration-tests-and-terraform-hardening.md)
