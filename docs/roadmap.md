# Roadmap

## Completed ✓

- [x] NIfTI loading via SimpleITK with orientation correction
- [x] DICOM series loading with automatic position-based slice sorting
- [x] Three synchronized MPR planes — Axial, Coronal, Sagittal
- [x] Draggable crosshairs via pyqtgraph `InfiniteLine(movable=True)`
- [x] Click-to-jump crosshair in any plane
- [x] Per-plane Window / Level controls (W and L sliders)
- [x] Per-plane colormaps
- [x] Per-plane cine playback at 20 fps
- [x] Embedded VTK GPU volume rendering as 4th viewport
- [x] Transfer function presets: mri\_default, bone, angio, pet
- [x] Background loading with QThread — UI stays responsive
- [x] LRU slice cache (36 slots) + neighbor prefetch
- [x] Physical voxel spacing applied to aspect ratio
- [x] Dark / light mode with system preference detection
- [x] Modular architecture: core/ + ui/ with clean boundary

## Planned — short term

- [ ] Pixel value readout on hover (show intensity at cursor position)
- [ ] Screenshot export — save current viewport as PNG
- [ ] Keyboard shortcuts — L=load, R=reset, P=play, 1/2/3=focus plane
- [ ] DICOM metadata panel — acquisition parameters, patient info (anonymised)
- [ ] Measurement tool — distance in millimetres using physical spacing

## Planned — longer term

- [ ] 4D NIfTI support — fMRI timeseries playback
- [ ] Oblique slicing — arbitrary plane at any angle
- [ ] Segmentation overlay — blend a mask NIfTI over the anatomy
- [ ] ROI drawing — freehand region with intensity statistics
- [ ] Batch slice export — save all slices of a plane as PNG sequence

## Will not implement

- **PACS networking / DICOM C-FIND** — out of scope for a local viewer
- **Diagnostic reporting** — MPRViewer is a teaching and research tool,
  not a clinical workstation. Do not use for clinical diagnosis.

## Suggest a feature

Open a [Feature Request](https://github.com/BasselShaheen06/MPR_Viewer/issues/new?template=feature_request.md) on GitHub.