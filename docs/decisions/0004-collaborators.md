# 0004 — Collaborator display

- Date: 2026-10-01
- Status: accepted

## Context
Listing every co-author is noisy; listing none ignores the people Tim works with most.

## Decision
`collaborators.key` in `config.yml` is shown up front; all other co-authors (from the papers)
sit behind "+N more", ordered by number of joint papers. `hide` removes people.

## Why
The key list is a deliberate choice by Tim; the rest stays complete and current without upkeep.
