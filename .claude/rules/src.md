---
paths:
  - "src/**/*.py"
---
# Rules for library code (src/)

- No `print`; use `logging.getLogger(__name__)` (the CLI sets up the format).
- No hardcoded site content (names, links, venues): it belongs in `config.yml` or `content/*.yml`.
- Network calls go through `sitegen.http.get`, which retries and never raises.
- A sync step that fails must fall back to what the last sync had (see docs/decisions/0002).
