# 0003 — Automatic teaser chain

- Date: 2026-10-01
- Status: accepted

## Context
Every paper should show a teaser on hover without Tim curating figures.

## Decision
Try in order: `overrides/<slug>/` → project page video / og:image → arXiv HTML Figure 1 →
arXiv LaTeX source figure → Figure 1 region of the PDF (anchored on its caption) → a robot doodle.

## Why
Project pages have the nicest media; the PDF always exists. The doodle keeps the layout intact
when everything fails, and an override is one file when the automatic pick is wrong.
