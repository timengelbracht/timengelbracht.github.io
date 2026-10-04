---
name: plan-change
description: Plan a non-trivial code change before writing it — map where new code goes, what existing code is reused or extended, and what (if anything) is genuinely new. Use for anything over ~50 lines, any new module/feature/experiment type, or changes touching more than 3 files.
---

# Plan change

Goal: prevent duplicate implementations and monoliths by deciding *where*
code goes before writing it.

1. Read `docs/ARCHITECTURE.md` and `AGENTS.md` → Architecture & reuse.
2. **Search for existing code** that already does part of this:
   grep for likely function/class names, related config keys, and similar
   call sites in `src/`. List what you found.
3. Write a short plan (≤ 15 lines) to Tim:
   ```
   Goal: <one line>
   Reuse:   <existing functions/modules used as-is>
   Extend:  <existing code changed, and how>
   New:     <new functions/files, each with its module and one-line purpose>
   Config:  <new config keys / files>
   Tests:   <what gets tested>
   Docs:    <ARCHITECTURE.md lines added/changed>
   ```
   Every "New" item must say why nothing existing fits.
4. Prototype profile: proceed unless the plan creates a new subpackage or
   touches > 5 files — then wait for Tim. Release profile: wait for Tim's OK.
5. Implement in small steps; run tests after each step.
