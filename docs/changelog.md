# Changelog

## [1.0.0] — March 2026

### Rewritten from scratch — modular architecture

The original single-file `MPR_Viewer1.py` (710 lines, one class) was fully
rewritten into a modular package.

**New modules:**

| File | Responsibility |
|---|---|
| `core/loader.py` | NIfTI + DICOM loading, `VolumeData` dataclass — no UI |
| `core/renderer.py` | VTK pipeline, transfer function presets — no UI |
| `ui/viewport.py` | `SliceViewport` — pyqtgraph canvas, draggable crosshairs |
| `ui/controls.py` | `TopBar` |
| `ui/main_window.py` | Wiring, crosshair sync, background loading, cine |
| `ui/theme.py` | Dark / light palettes, `ThemeManager` |

### New features

- **Draggable crosshairs** — pyqtgraph `InfiniteLine(movable=True)` replaces
  matplotlib crosshair lines. Drag any line; all three planes update in real time.
- **Embedded VTK 3D panel** — volume rendering is a 4th viewport in the Qt
  layout, not a blocking separate window.
- **Transfer function presets** — `mri_default`, `bone`, `angio`, `pet` with
  tuned colour and opacity functions.
- **Background loading** — `QThread` + `LoadWorker` keeps the UI responsive
  while large volumes are loading.
- **Slice cache + prefetch** — 36-slot LRU cache, prefetch ±2 neighbors on
  every crosshair move.
- **Per-plane cine timers** — each plane has an independent play/pause.
- **Per-plane W/L and colormap** — independent controls embedded in each viewport.
- **Dark / light mode** — system preference detected on first launch, saved
  to `QSettings`.
- **Physical voxel spacing** — read from file headers and applied to aspect ratio.

### Fixed (vs original)

- Duplicate `pydicom` import removed
- Dead `zoom()` method removed (was never connected to any event)
- `self.data` / `self.scan_array` duplication eliminated
- All `print()` debug statements replaced with status bar messages
- "Brightness/Contrast" renamed to "Window/Level" (correct clinical term)
- Clone URL in README corrected (was `yourusername`)
- Branch renamed `master` → `main`
- `load_dicom()` that only read one file replaced with `load_dicom_series()`
  that reads a full sorted series