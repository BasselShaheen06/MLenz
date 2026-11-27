# Documentation source

These pages are written in **plain GitHub-flavoured Markdown** and are the single
source of truth for MLenz documentation. They are published on the author's
portfolio site, not by a static-site generator in this repository.

## Publishing

Copy the `docs/` directory into the portfolio's content folder, preserving the
relative layout:

```
docs/index.md            -> <portfolio>/content/mlenz/index.md
docs/installation.md     -> <portfolio>/content/mlenz/installation.md
docs/assets/...          -> <portfolio>/content/mlenz/assets/...
```

Relative image and video links (`assets/screenshots/...`) resolve as long as
`docs/assets/` is copied alongside the pages. If you would rather not duplicate
the media, replace `assets/...` with raw GitHub URLs:

```
https://raw.githubusercontent.com/BasselShaheen06/MLenz/main/docs/assets/screenshots/Entry%20Window.png
```

## Conventions

- No MkDocs extensions. Admonitions are blockquotes, not `!!! note`.
- Math uses `$$ ... $$` and needs MathJax or KaTeX enabled on the host site.
- Mermaid blocks need a Mermaid plugin on the host site.
- Keep `api/` here as well: the API reference belongs next to the code for
  contributors, and the portfolio can link to it.

## Editing rules

- Update the page in this folder, then re-copy it to the portfolio.
- Do not edit the copies in the portfolio directly; they will be overwritten.
