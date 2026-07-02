---
name: wiki-query
description: Consult the wiki at docs/wiki/ before answering project questions about the hiring-service. USE when the user asks about service architecture, ingestion domain (models, UCs, adapters), recorded decisions (ADRs), system design rationale, or any topic covered by the wiki pages. SKIP for generic programming/framework questions, external tools not specific to this project, trivial questions answerable by reading a single file, or implementation / code-writing requests.
argument-hint: user question
---

You will answer the user's question using the wiki as the primary source.

## Required steps

1. **Read `docs/INDEX.md`** to know what's available.

2. **Search `docs/wiki/`** for pages relevant to the question. Grep aggressively over titles, claims, and body. Also check the ADR folders.

3. **Synthesize an answer** combining what you found. Always cite the pages used with their path and slug, e.g. `[[hiring-service-design]]` in `docs/wiki/hiring-service/domain/hiring-service-design.md`.

4. **If the answer needs to go beyond the wiki** (reading code, checking PRs, external sources), state it explicitly: "this wasn't in the wiki, I inferred it from reading X." Never silently mix wiki claims with your own inferences.

5. **If the wiki has nothing on the topic**, say so directly. Answer with what you can derive from code, making clear the wiki doesn't cover this yet (candidate for documenting).

## At the end, offer to archive

If the Q&A has reusable value (non-trivial, non-ephemeral), ask the user:

> Want me to archive this Q&A? Options:
> - Append to an existing page (which one)
> - Create a new page (propose slug and location)
> - Don't archive

If they choose to archive, do it following front-matter conventions: full front-matter, atomic claims, `[[slug]]` links.

## Rules

- Don't say "according to the wiki..." if the wiki doesn't have the info. Be honest about the source.
- If the wiki contradicts current code, mark the page as a `stale` candidate and warn the user.
- If this skill was auto-invoked and the question turns out to be unrelated to the project (generic programming, external tool), abandon the skill silently and answer normally.
