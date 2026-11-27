# Changelog

## [Unreleased]

### Added

- **Hounsfield-unit conversion for CT** — `mlenz/core/windowing.py` recovers the
  stored values from the normalised array and converts them to HU using the
  rescale tags preserved in `VolumeData.meta`. Ships with the clinical presets
  Brain (L40/W80), Bone (L400/W1800), Lung (L−600/W1500), Soft tissue (L40/W400)
  and Angio (L300/W600).
- **Preset selector in every viewport** — visible only for CT volumes, and it
  returns to the placeholder as soon as a slider is moved by hand, so the label
  never describes a window the view is not using.
- `VolumeData.rescale_applied` — SimpleITK applies `RescaleSlope`/
  `RescaleIntercept` while reading a DICOM, so the loader records that and
  `to_hounsfield()` leaves the values alone. Applying the tags a second time
  would shift every voxel by the intercept. A real-DICOM round-trip test pins
  the behaviour.
- `tests/test_windowing.py` — 20 tests, including the end-to-end
  DICOM → loader → HU path.

### Fixed

- **Multi-frame DICOM lost its through-plane spacing** — GDCM reports 1.0 mm
  between frames even when `SpacingBetweenSlices`/`SliceThickness` says
  otherwise, so coronal and sagittal reconstructions were squashed. The loader
  now fills the real value in before reorientation, so it is permuted with the
  axes.

## [1.1.0] — 2026-11-27

### Fixed

- **Installed console script was broken** — the `mlenz` entry point pointed at
  the root-level `main.py`, which is not part of the wheel, so `pip install .`
  and then `mlenz` crashed. The launcher now lives in `mlenz/app.py`; `main.py`
  remains as a thin backward-compatible shim and `python -m mlenz` also works.
- **DICOM modality was always lost** — `DICOMOrientImageFilter` drops every
  metadata key, so tags were read after reorientation and came back empty.
  Metadata is now read before orienting. This also unblocks CT Hounsfield-unit
  scaling, which needs `RescaleSlope`/`RescaleIntercept` from the same headers.
- **Anisotropic voxels crashed the viewer** — the aspect-ratio correction called
  `ImageItem.scale(sx, sy)`, which pyqtgraph 0.14 no longer accepts, and the
  ratio was inverted. Replaced with an explicit `QTransform` and moved the math
  into `core/geometry.py`, which is unit-tested. Square-pixel volumes were
  unaffected, so the bug stayed hidden on isotropic demo data.
- **`pip install .` produced a broken install** — `pyqtgraph` was imported by
  the UI but never declared, and the test-only `nibabel`/`pydicom` were listed
  as runtime dependencies. Runtime requirements now match the imports, and the
  test dependencies live in the `dev` extra.

### Added

- `VolumeData.meta` — every metadata key, read before reorientation.
  `VolumeData.spacing_zyx` and `VolumeData.physical_extent` give millimetre
  values in the same axis order as `data` (`Z, Y, X`), removing the silent
  axis-order mix-up in volume maths.
- `tests/test_loader.py` — 19 tests over the public loaders, using synthetic
  NIfTI and DICOM files (no patient data).
- `tests/test_geometry.py` — aspect-ratio tests.
- `mlenz/core/geometry.py` — pure, Qt-free geometry helpers.
- Explicit `__init__.py` files so `mlenz`, `mlenz.core` and `mlenz.ui` are
  regular packages rather than implicit namespace packages.
- CI now runs on `main` (it was watching `master`, so it never ran), installs
  the package, and verifies the console-script entry point.
- `docs/assets/demo/hero.gif` — a 12-second capture used at the top of the
  README, generated from the existing demo recording.
- `docs/README.md` — explains that `docs/` is plain Markdown published on the
  portfolio site, with no static-site generator in this repository.

### Changed

- **Documentation moved to the portfolio site.** MkDocs is gone: `mkdocs.yml`,
  `docs/stylesheets/` and the GitHub Pages workflow were removed. The pages
  stay in `docs/` as plain Markdown — the single source of truth — with the
  API reference kept next to the code.
- README rewritten around a demo GIF, a screenshot grid and an explicit
  limitations section, instead of placeholder boxes.
- The MkDocs-only `!!! info` admonition in `docs/usage.md` became a blockquote
  so the page renders anywhere.

## [1.0.0] — 2026

### Complete rewrite — modular architecture

The original single-file `MLenz1.py` (710 lines, one class, no separation)
was fully rewritten into a modular package.

**New modules:**

| File | Responsibility |
|---|---|
| `core/loader.py` | NIfTI + DICOM loading, `VolumeData` dataclass — no UI |
| `core/renderer.py` | VTK pipeline, 4 transfer function presets — no UI |
| `ui/viewport.py` | `SliceViewport` — pyqtgraph canvas, draggable crosshairs, annotation |
| `ui/controls.py` | `TopBar` global actions |
| `ui/main_window.py` | Crosshair sync, cine timers, background loading, wiring |
| `ui/theme.py` | Dark / light palettes, `ThemeManager` |

### New features

- **Draggable crosshairs** — pyqtgraph `InfiniteLine(movable=True)`. Drag
  any line; all three planes update in real time.
- **Crosshair intersection circle** — `ScatterPlotItem` hollow dot
- **Per-viewport embedded controls** — play/pause, colormap, W/L, annotate,
  clear, save — all inside each viewport's own control bar
- **Global cine control** — ▶ All / ⏸ All to play every plane at once
- **Freehand annotation** — draw on any plane, clear, export as PNG
- **Embedded VTK 3D panel** — volume rendering in the Qt layout, not a
  blocking separate window
- **4 transfer function presets** — mri\_default, bone, angio, pet
- **Background loading** — `QThread` + `LoadWorker` keeps UI responsive
- **LRU slice cache** — 36 slots + ±2 neighbor prefetch
- **Physical voxel spacing** — applied to aspect ratio from DICOM/NIfTI headers
- **Dark / light mode** — system preference on first launch, saved to `QSettings`
- **Start screen** — fMRI-style gradient splash with dark overlay
- **Guided tour** — spotlight overlay with step-by-step prompts

### Fixed (from original)

- Duplicate `pydicom` import removed
- Dead `zoom()` method removed (was never connected)
- `self.data` / `self.scan_array` duplication eliminated  
- All `print()` replaced with status bar messages
- "Brightness/Contrast" renamed to "Window/Level" (correct clinical term)
- `load_dicom()` reading one file → `load_dicom_series()` reading full series
- Clone URL in README corrected (was `yourusername`)
- Branch renamed `master` → `main`