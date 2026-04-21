# Contributing

## Before you start

Open an issue first — use the templates:

- [Bug report](https://github.com/BasselShaheen06/MLenz/issues/new?template=bug_report.md)
- [Feature request](https://github.com/BasselShaheen06/MLenz/issues/new?template=feature_request.md)

## Setup

```bash
git clone https://github.com/BasselShaheen06/MLenz.git
cd MLenz
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Hard boundary — never cross this

`core/` modules must **never** import `PyQt5`, `pyqtgraph`, or `matplotlib`.
They take a path or numpy array, return a `VolumeData` or numpy array.
No side effects.

## Adding a new file format

Add a loader function to `core/loader.py` and add the extension to
`guess_loader()`. SimpleITK supports most formats (`.mhd`, `.nrrd`,
`.mha`, `.vtk`) without extra code — just let it fall through to the
SimpleITK fallback.

## Code standards

- Type hints on all public functions
- Google-style docstrings
- `ruff check .` must pass before committing
- Run `pytest` — all tests must pass

## Commit messages

```
feat: add pixel value readout on hover
fix: annotation stroke duplicated on fast mouse-move
docs: update Window/Level explanation in science.md
refactor: extract cine logic to CineController
test: add loader roundtrip test for NIfTI
```

## Pull request checklist

- [ ] `ruff check .` passes
- [ ] `pytest` passes
- [ ] `core/` has no UI imports
- [ ] Docs updated if behaviour changed
- [ ] `changelog.md` updated