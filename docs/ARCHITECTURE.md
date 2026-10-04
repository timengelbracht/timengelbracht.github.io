# Architecture — personal-website

The map of this codebase. **Read before coding; update in the same change
when you add, move or remove a module.** One line per module: what it owns.

## Data flow
```
config.yml + Scholar / Semantic Scholar / arXiv ids
   → sitegen sync → sources/* → links → teasers → data/publications.json + assets/teasers/
config.yml + content/*.yml + data/publications.json
   → sitegen build → templates/index.html.j2 → site/ → GitHub Pages
```

## Layers (enforced by `lint-imports`)
`cli → sync | build | failures → teasers → links → sources → http | media | venues → util | paths`
— a module may import from modules to its right, never to its left.

## Modules (`src/sitegen/`)
| Module | Owns | Key entry points |
|---|---|---|
| `cli.py` | command line, logging setup | `main` |
| `sync.py` | paper pipeline: collect, merge, enrich, carry over last sync | `run`, `collect`, `process` |
| `build.py` | turning config/content/data into the page | `run`, `collaborators`, `apply_overrides` |
| `failures.py` | adding a "failure of the month" clip | `add` |
| `teasers.py` | teaser chain: override → project page → arXiv HTML → arXiv source → PDF → doodle | `Teasers` |
| `links.py` | finding project/code/video/data links and verifying them | `classify`, `verify`, `page_mentions_paper` |
| `sources/` | one file per metadata source (scholar, semantic_scholar, arxiv, openalex, dblp) | |
| `http.py` | the only place that does HTTP; retries, never raises | `get` |
| `media.py` | image/video conversion (Pillow, ffmpeg) | `save_image`, `save_video` |
| `venues.py` | venue names: short labels, from arXiv comments | `short`, `from_text` |
| `util.py` | text helpers (slugs, name keys), YAML loading | |
| `paths.py` | repo paths | `Paths` |
| `templates/index.html.j2` | the page: HTML, CSS, doodles, JS | |

## Extension points
- **paper source:** add `sources/<name>.py`, call it from `sync.collect` (paper list) or `sync.enrich_metadata` (details).
- **teaser source:** add a method to `teasers.Teasers` and put it in the chain.
- **page section:** template block + `content/<name>.yml` + pass it in `build.run`.

## Conventions
- Sync is fail-soft: a failing source never removes papers, links or teasers (decision 0002).
- Hand-written facts in `content/paper_links.yml` win over anything found automatically.
