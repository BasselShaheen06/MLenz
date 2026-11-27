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

MLenz flips Coronal and Sagittal slices vertically before display
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
| Bone | 400 | 1800 |
| Lung | −600 | 1500 |
| Soft tissue | 40 | 400 |
| Angio | 300 | 600 |

MLenz normalises all intensities to [0, 1] on load, so the sliders work in
fractions: the default (L=0.5, W=1.0) shows the full range.

For CT, the presets are stored in Hounsfield units and converted to that scale
before they reach the sliders:

$$\text{stored} = \text{normalised}\cdot(\text{raw}_{max}-\text{raw}_{min}) + \text{raw}_{min}$$
$$\text{HU} = \text{stored}\cdot\text{RescaleSlope} + \text{RescaleIntercept}$$

The rescale tags come from the file header rather than a table of scanner
models. SimpleITK applies them while reading, so MLenz records that in
`VolumeData.rescale_applied` and does not apply them a second time — doing so
would shift every voxel by the intercept.

---

## VTK GPU Volume Rendering

Volume rendering casts a ray from each screen pixel through the volume
and integrates contributions along the path.

**Transfer functions** control how intensity maps to colour and opacity:

- **Colour transfer function** → intensity to RGB
- **Opacity transfer function** → intensity to transparency

MLenz uses `vtkGPUVolumeRayCastMapper` — GPU-accelerated OpenGL ray
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

MLenz uses SimpleITK's orientation correction to reorient all loaded
volumes to a consistent LPS+ orientation before display.

---

## DICOM loading

DICOM stores each 2-D slice as a separate file. In the UI, MLenz loads a
single `.dcm` file for quick inspection. The core loader still supports
full series loading for scripts and notebooks. Sorting by filename is
unreliable, so series loading uses SimpleITK's `GetGDCMSeriesFileNames()`
which sorts by the `ImagePositionPatient` DICOM tag — the physical position
of each slice guaranteed by the scanner — giving correct spatial order.

Physical voxel spacing from `PixelSpacing` and `SliceThickness` tags is
applied to the viewport aspect ratio so non-isotropic acquisitions
(e.g. thick axial slices) display with correct proportions.