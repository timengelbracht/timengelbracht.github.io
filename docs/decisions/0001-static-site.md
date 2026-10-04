# 0001 — Static generator + GitHub Pages

- Date: 2026-10-01
- Status: accepted

## Context
The site should look individual but need almost no maintenance.

## Options
1. Academic template (al-folio, Hugo themes) — quick, but looks like every other lab page.
2. Hand-written HTML — individual, but papers have to be added by hand.
3. Small Python generator + one Jinja template — individual design, papers synced automatically.

## Decision
Option 3: `sitegen` renders one self-contained page; a weekly GitHub Action syncs papers and deploys to Pages.

## Why
Full control over the design, no JS framework, and the only recurring work is optional content.
