"""A synthetic head CT, for demos and tests.

The repository ships no patient data, and the CT window presets need a CT to
demonstrate. This module builds one analytically: an ellipsoidal head with a
skull, brain, ventricles, a small hyperdense lesion and an air sinus, all in
Hounsfield units.

Pure numpy on purpose — writing the DICOM lives in ``tools/make_sample_ct.py``
so that this module can be imported by tests without pydicom.
"""

from __future__ import annotations

import numpy as np

# Hounsfield units for the tissues the phantom contains.
AIR = -1000.0
CSF = 10.0
BRAIN = 35.0
SOFT_TISSUE = 40.0
BLOOD = 75.0
BONE = 1000.0

# Dimensions in millimetres, measured from the centre of the head.
BODY_A, BODY_B = 60.0, 46.0
SKULL_OUTER_A, SKULL_OUTER_B = 56.0, 42.0
SKULL_INNER_A, SKULL_INNER_B = 52.0, 38.0


def head_ct(
    size: int = 128,
    slices: int = 48,
    spacing: float = 1.5,
    slice_thickness: float = 3.0,
    seed: int = 0,
) -> np.ndarray:
    """Build a head CT volume in Hounsfield units.

    Args:
        size: voxels per in-plane axis (square).
        slices: number of axial slices.
        spacing: in-plane voxel size, millimetres.
        slice_thickness: distance between slices, millimetres.
        seed: seed for the acquisition noise.

    Returns:
        float32 array of shape ``(slices, size, size)``, values in HU.
    """
    if size < 32:
        raise ValueError("size must be at least 32 voxels.")
    if slices < 4:
        raise ValueError("slices must be at least 4.")

    hu = np.full((slices, size, size), AIR, dtype=np.float32)

    half = (size - 1) / 2.0
    rows, cols = np.mgrid[0:size, 0:size]
    x = (cols - half) * spacing
    y = (rows - half) * spacing

    z = (np.arange(slices) - (slices - 1) / 2.0) * slice_thickness
    z_half = max(float(np.abs(z).max()), 1e-6)

    for k, zk in enumerate(z):
        # The head is an ellipsoid: in-plane radii shrink towards the top.
        taper = float(np.sqrt(max(0.0, 1.0 - (zk / (z_half * 1.05)) ** 2)))
        if taper < 0.15:
            continue

        def inside(radius_a: float, radius_b: float) -> np.ndarray:
            return (x / (radius_a * taper)) ** 2 + (
                y / (radius_b * taper)
            ) ** 2 <= 1.0

        body = inside(BODY_A, BODY_B)
        skull_outer = inside(SKULL_OUTER_A, SKULL_OUTER_B)
        skull_inner = inside(SKULL_INNER_A, SKULL_INNER_B)

        hu[k][body] = SOFT_TISSUE
        hu[k][skull_outer] = BONE
        hu[k][skull_inner] = BRAIN

        # Two lateral ventricles, filled with CSF.
        ventricles = (
            ((x - 8.0) / 7.0) ** 2 + (y / 12.0) ** 2 <= 1.0
        ) | (((x + 8.0) / 7.0) ** 2 + (y / 12.0) ** 2 <= 1.0)
        hu[k][ventricles & skull_inner] = CSF

        # A hyperdense lesion — the thing the Brain window exists to reveal.
        lesion = (x - 22.0) ** 2 + (y + 14.0) ** 2 <= 8.0**2
        hu[k][lesion & skull_inner] = BLOOD

        # Frontal air sinus, anterior (top of the image), to keep the top of
        # the range honest.
        sinus = (x / 6.0) ** 2 + ((y + 40.0) / 5.0) ** 2 <= 1.0
        hu[k][sinus & body] = AIR

    # Acquisition noise, but only inside tissue — air stays flat.
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 6.0, hu.shape).astype(np.float32)
    tissue = hu > AIR + 50.0
    hu[tissue] += noise[tissue]

    return np.clip(hu, -1024.0, 3071.0)
