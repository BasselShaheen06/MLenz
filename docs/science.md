# The Science

---

## Multi-Planar Reconstruction

A volumetric medical image is a 3-D array of voxels. Each voxel has a
physical size in millimetres stored in the file header. MPR slices through
this array in three orthogonal directions:

$$\text{Axial}(z) = V[z, :, :] \qquad
\text{Coronal}(y) = V[:, y, :] \qquad
\text{Sagittal}(x) = V[:, :, x]$$

Where $V$ has shape $(Z, Y, X)$.

**Anatomical orientation:**

| Plane | Slice direction | Standard orientation |
|---|---|---|
| Axial | Inferior → Superior | Superior at top |
| Coronal | Anterior → Posterior | Superior at top |
| Sagittal | Left → Right | Superior at top |

MPRViewer flips Coronal and Sagittal slices vertically before display
so superior is always at the top — matching clinical convention.

### Crosshair synchronisation

Dragging the crosshair to $(x, y)$ in the Axial plane causes the Coronal
plane to display slice at column $x$, and Sagittal to display slice at
column $y$. All three planes always show the same physical voxel.

---

## Window and Level

Medical images span wider intensity ranges than a display can show. Brain CT
covers roughly −1000 HU (air) to +3000 HU (bone). Mapping this linearly
compresses soft tissue into ~6% of the display range.

Window/Level selects a sub-range to fill the full display:

$$\text{pixel} = \text{clip}\!\left(\frac{I - (L - W/2)}{W},\ 0,\ 1\right)$$

Where $I$ is voxel intensity, $L$ is Level (centre), $W$ is Window (width).

Standard CT presets (Hounsfield Units):

| Tissue | L | W |
|---|---|---|
| Brain soft tissue | 40 | 80 |
| Subdural haematoma | 75 | 215 |
| Bone | 400 | 1800 |
| Lung | −600 | 1500 |

MPRViewer normalises all intensities to [0, 1] on load. L and W are
expressed as fractions. The default (L=0.5, W=1.0) shows the full range.

---

## VTK GPU Volume Rendering

Volume rendering casts a ray from each screen pixel through the volume
and integrates contributions along the path.

**Transfer functions** control how intensity maps to colour and opacity:

- **Colour transfer function** → intensity to RGB
- **Opacity transfer function** → intensity to transparency

MPRViewer uses `vtkGPUVolumeRayCastMapper` — GPU-accelerated OpenGL ray
casting, the same approach used by 3D Slicer and OsiriX.

### Transfer function presets

| Preset | Colour strategy | Opacity strategy |
|---|---|---|
| `mri_default` | Black → grey → white | Transparent < 0.1, opaque > 0.7 |
| `bone` | Black → tan → white | Only high intensities (> 0.6) visible |
| `angio` | Black → red → orange | Mid-to-high intensities visible |
| `pet` | Blue → cyan → yellow → white | Low counts transparent |

---

## NIfTI format

NIfTI stores a 3-D intensity array plus a 348-byte header containing
voxel dimensions, data type, and an orientation matrix (qform/sform)
that maps voxel indices to millimetre coordinates in patient space.

MPRViewer uses SimpleITK's orientation correction to reorient all loaded
volumes to a consistent LPS+ orientation before display.

---

## DICOM series loading

DICOM stores each 2-D slice as a separate file. Sorting by filename is
unreliable. MPRViewer uses SimpleITK's `GetGDCMSeriesFileNames()` which
sorts by the `ImagePositionPatient` DICOM tag — the physical position of
each slice guaranteed by the scanner — giving correct spatial order.

Physical voxel spacing from `PixelSpacing` and `SliceThickness` tags is
applied to the viewport aspect ratio so non-isotropic acquisitions
(e.g. thick axial slices) display with correct proportions.