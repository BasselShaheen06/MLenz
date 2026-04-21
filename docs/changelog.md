# Changelog

## [1.0.0] — 2026

### Complete rewrite — modular architecture

The original single-file `MPR_Viewer1.py` (710 lines, one class, no separation)
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