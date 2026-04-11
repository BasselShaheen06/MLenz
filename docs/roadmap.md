# Roadmap

## Completed ✓

- [x] NIfTI loading with orientation correction (SimpleITK)
- [x] DICOM series loading sorted by `ImagePositionPatient`
- [x] Three synchronized MPR planes — Axial · Coronal · Sagittal
- [x] Draggable crosshairs (`InfiniteLine(movable=True)`)
- [x] Hollow circle at crosshair intersection (`ScatterPlotItem`)
- [x] Click-to-jump crosshair
- [x] Per-plane W/L sliders (Window width + Window level)
- [x] Per-plane colormaps (9 options each)
- [x] Per-plane cine playback at 20 fps with independent play/pause
- [x] Freehand annotation with yellow strokes
- [x] Clear annotations per plane
- [x] Export annotated viewport as PNG
- [x] Embedded VTK GPU volume rendering as 4th viewport
- [x] Transfer function presets: mri\_default · bone · angio · pet
- [x] Background loading with `QThread`
- [x] LRU slice cache (36 slots) + neighbor prefetch
- [x] Physical voxel spacing applied to aspect ratio
- [x] Dark / light mode with system preference detection

## Planned — short term

- [ ] Pixel value readout on hover
- [ ] Keyboard shortcuts (L=load, R=reset, P=play, 1/2/3=focus plane)
- [ ] DICOM metadata panel (acquisition parameters, anonymised)
- [ ] Screenshot export button in TopBar (current view as PNG)
- [ ] Measurement ruler — distance in physical mm

## Planned — longer term

- [ ] Segmentation overlay — blend a mask NIfTI over anatomy
- [ ] 4D NIfTI support — fMRI timeseries playback
- [ ] Oblique slicing — arbitrary angle through the volume
- [ ] ROI drawing with intensity statistics
- [ ] Batch export — all slices of a plane as PNG sequence

## Will not implement

- **PACS networking** — out of scope for a local desktop viewer
- **Diagnostic reporting** — teaching/research tool only, not for clinical diagnosis

## Suggest a feature

Open a [Feature Request](https://github.com/BasselShaheen06/MPR_Viewer/issues/new?template=feature_request.md).