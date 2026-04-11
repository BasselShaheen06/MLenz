# Contributing to MPRViewer

Thanks for taking the time to contribute.

## Setup

```bash
git clone https://github.com/BasselShaheen06/MPR_Viewer.git
cd MPR_Viewer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Workflow

- Create a branch per change.
- Keep pull requests focused and small.
- Update docs when behavior changes.

## Quality checks

```bash
ruff check .
pytest
```

## Code guidelines

- Keep `core/` free of UI dependencies.
- Keep UI logic in `ui/` and avoid circular imports.
- Add docstrings to public functions and classes.

## Reporting issues

Please use the GitHub issue templates and include steps to reproduce.
