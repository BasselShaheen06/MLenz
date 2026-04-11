# The Science

---

## Multi-Planar Reconstruction

A volumetric medical image is a 3-D array of voxels. Each voxel has a
physical size in millimetres defined by the acquisition parameters — this
is stored in the file header and read by MPRViewer to set the correct
aspect ratio on display.

MPR slices through this array in three orthogonal directions:

$$\text{Axial}(z) = V[z, :, :] \qquad
\text{Coronal}(y) = V[:, y, :] \qquad
\text{Sagittal}(x) = V[:, :, x]$$

Where $V$ is the volume array with axes (Z, Y, X).

**Anatomical orientation:**

- **Axial** — horizontal, inferior → superior (feet to head)
- **Coronal** — frontal, anterior → posterior (front to back)
- **Sagittal** — lateral, left → right

MPRViewer flips the coronal and sagittal slices vertically before display
so that superior is at the top, matching clinical convention.

### Crosshair synchronisation

When you drag the crosshair to position $(x, y)$ in the Axial plane,
the Coronal plane updates to show the slice at column $x$, and the
Sagittal plane updates to show the slice at column $y$. All three
planes always show the same physical point in the volume.

---

## Window and Level

Medical image data spans a much wider intensity range than an 8-bit
display can show. A brain CT covers roughly −1000 HU (air) to +3000 HU
(dense bone). Mapping this linearly to 0–255 puts soft tissue — which
spans only −100 to +100 HU — into a flat 6% of the display range.

**Window/Level** selects a sub-range of intensities to fill the display:

$$\text{pixel} = \text{clip}\!\left(\frac{I - (L - W/2)}{W},\ 0,\ 1\right)$$

Where $I$ is the voxel intensity, $L$ is the Level (centre), and $W$ is
the Window (width). Intensities below $L - W/2$ display as black;
intensities above $L + W/2$ display as white.

Standard clinical presets (in Hounsfield Units for CT):

| Tissue | L | W |
|---|---|---|
| Brain soft tissue | 40 | 80 |
| Subdural haematoma | 75 | 215 |
| Bone | 400 | 1800 |
| Lung parenchyma | −600 | 1500 |
| Liver | 60 | 160 |

MPRViewer normalises all intensities to [0, 1] on load, so L and W
are expressed as fractions. The default (L=0.5, W=1.0) shows the
full dynamic range of the loaded volume.

---

## VTK GPU Volume Rendering

Volume rendering produces a 2-D image from the 3-D array by casting a
ray from each screen pixel through the volume and integrating
contributions along the ray path.

### Transfer functions

Two functions control how intensity maps to the visual output:

- **Colour transfer function** — maps intensity → RGB colour
- **Opacity transfer function** — maps intensity → opacity (0=invisible, 1=opaque)

By assigning low opacity to intensities you want to hide (e.g. soft
tissue in a bone preset), structures of interest become visible through
the volume.

### GPU ray casting

MPRViewer uses `vtkGPUVolumeRayCastMapper`, which runs ray integration
on the GPU using OpenGL. This is the same rendering approach used by
3D Slicer and OsiriX. A discrete GPU is recommended for volumes larger
than 256³.

### Presets

| Preset | Strategy |
|---|---|
| `mri_default` | Soft tissue opaque at 0.3–0.7, bone opaque at 0.7–1.0 |
| `bone` | Only high-intensity voxels (> 0.6) are opaque |
| `angio` | Mid-high intensities (vessels) highlighted in warm colours |
| `pet` | Hot-metal colormap — low counts blue → high counts white |

---

## NIfTI format

NIfTI (Neuroimaging Informatics Technology Initiative) is the standard
format for neuroimaging research. A `.nii.gz` file contains:

- A 348-byte header with voxel dimensions, data type, and an
  orientation matrix (qform or sform)
- A 3-D (or 4-D for fMRI) intensity array, gzip-compressed

The **orientation matrix** maps voxel indices to physical millimetre
coordinates in patient space (RAS convention: Right-Anterior-Superior).
MPRViewer uses SimpleITK's `_orient_image()` to reorient all loaded
volumes into a consistent LPS+ orientation before display, so coronal
and sagittal flips are applied correctly regardless of how the
acquisition was oriented.

---

## DICOM series loading

DICOM files store each 2-D slice as a separate file. Sorting slices
by filename is unreliable — filenames may not reflect acquisition order.
MPRViewer uses SimpleITK's `GetGDCMSeriesFileNames()` which sorts by
the `ImagePositionPatient` DICOM tag, giving the correct spatial order
guaranteed by the scanner.

Physical voxel spacing is read from the `PixelSpacing` and
`SliceThickness` tags and passed through to the display layer so
aspect ratios are preserved correctly even for anisotropic acquisitions
(e.g. thick axial slices reconstructed into thin coronal slices).