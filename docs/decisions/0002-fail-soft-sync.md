# 0002 — Fail-soft paper sync

- Date: 2026-10-01
- Status: accepted

## Context
Scholar, Semantic Scholar, arXiv and project pages are flaky or rate-limited; a weekly unattended
sync must never break the site.

## Options
1. Rebuild the paper list from scratch every sync — simple, but one outage empties the page.
2. Merge with the previous `data/publications.json` and keep anything a source fails to return.

## Decision
Option 2. Papers are deduplicated by normalized title and only disappear via `exclude`; details,
links and teasers fall back to the last sync. Links are only used if the page loads and mentions the paper.

## Why
"Never worse than last week" keeps the site trustworthy without supervision, and verified links
avoid dead or wrong project pages.
