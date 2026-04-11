# Contributing

Thanks for considering a contribution.

## Setup

```bash
git clone https://github.com/BasselShaheen06/MPR_Viewer.git
cd MPR_Viewer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Guidelines

- Keep `core/` free of UI dependencies.
- Keep UI logic in `ui/` and avoid circular imports.
- Prefer small, focused PRs with clear descriptions.

## Style

- Use descriptive names and keep functions short.
- Add docstrings to public functions and classes.

## Quality checks

```bash
ruff check .
pytest
```

## Reporting issues

Please include sample data (if possible) and steps to reproduce.

## Bug reports

When filing a bug, include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- OS and Python version
- A minimal dataset or screenshots (anonymized)
