"""Hounsfield-unit conversion and clinical window presets.

Every volume is normalised to ``[0, 1]`` on load so one display path can serve
MRI, CT and anything else. That is right for rendering and wrong for
measurement: a radiologist specifies a window as "level 40, width 80" in
Hounsfield units, and CT voxels are stored as integers that only mean something
after rescaling.

Two conversions sit between the normalised array and HU::

    stored = normalised * (raw_max - raw_min) + raw_min
    HU     = stored * RescaleSlope + RescaleIntercept

``raw_min``/``raw_max`` are recorded by the loader at normalisation time and the
rescale tags come from the DICOM headers preserved in :attr:`VolumeData.meta`,
so nothing here is hard-coded per scanner.

One wrinkle matters for correctness: SimpleITK already applies the rescale tags
while reading a DICOM, so for real files ``stored`` is *already* in Hounsfield
units. :attr:`VolumeData.rescale_applied` records that, and the second line
above is skipped — applying it twice would silently double-shift every value.
It is only applied here for volumes built by other paths.

This module is pure numpy and knows nothing about Qt or pyqtgraph.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from mlenz.core.loader import VolumeData

# DICOM tags used by the rescale step.
_TAG_INTERCEPT = "0028|1052"  # RescaleIntercept
_TAG_SLOPE = "0028|1053"  # RescaleSlope


class NotCTError(ValueError):
    """Raised when Hounsfield units are requested from a non-CT volume."""


@dataclass(frozen=True)
class WindowPreset:
    """A named clinical window, in Hounsfield units."""

    name: str
    level: float  # centre of the window, HU
    width: float  # full width of the window, HU
    description: str = ""

    def apply(self, values: np.ndarray) -> np.ndarray:
        """Map ``values`` in HU to display intensities in ``[0, 1]``."""
        return window(values, self.level, self.width)


PRESETS: tuple[WindowPreset, ...] = (
    WindowPreset("Brain", 40, 80, "Grey/white matter differentiation"),
    WindowPreset("Bone", 400, 1800, "Cortex and trabeculae"),
    WindowPreset("Lung", -600, 1500, "Parenchyma, air-filled spaces"),
    WindowPreset("Soft tissue", 40, 400, "Abdomen and mediastinum"),
    WindowPreset("Angio", 300, 600, "Contrast-enhanced vessels"),
)

PRESETS_BY_NAME: dict[str, WindowPreset] = {p.name.casefold(): p for p in PRESETS}


# ---------------------------------------------------------------------------
# Intensity conversion
# ---------------------------------------------------------------------------

def to_raw(volume: VolumeData) -> np.ndarray:
    """Undo the loader's normalisation and return the stored voxel values.

    Works for every modality, not just CT — it only depends on the min/max
    recorded during loading.
    """
    data = np.asarray(volume.data, dtype=np.float32)
    span = volume.raw_max - volume.raw_min
    if span <= 0:
        return np.full_like(data, volume.raw_min, dtype=np.float32)
    return data * span + volume.raw_min


def rescale(volume: VolumeData) -> tuple[float, float]:
    """Return ``(slope, intercept)`` from the DICOM headers.

    Missing tags fall back to the DICOM defaults ``(1.0, 0.0)``. A zero or
    non-finite slope would flatten the volume, so it is treated as the default
    too — a malformed header should not silently produce garbage.
    """
    slope = _tag_float(volume.meta, _TAG_SLOPE, 1.0)
    intercept = _tag_float(volume.meta, _TAG_INTERCEPT, 0.0)
    if not math.isfinite(slope) or slope == 0:
        slope = 1.0
    if not math.isfinite(intercept):
        intercept = 0.0
    return slope, intercept


def is_ct(volume: VolumeData) -> bool:
    """True when the volume declares itself as CT."""
    return (volume.modality or "").strip().upper() == "CT"


def has_rescale(volume: VolumeData) -> bool:
    """True when the volume carries explicit rescale tags."""
    return _TAG_SLOPE in volume.meta or _TAG_INTERCEPT in volume.meta


def to_hounsfield(volume: VolumeData) -> np.ndarray:
    """Convert a CT volume to Hounsfield units.

    When the loader reports that SimpleITK already applied the rescale tags
    (:attr:`VolumeData.rescale_applied`), the stored values are returned
    unchanged; the tags are not applied a second time.

    Raises:
        NotCTError: if the volume is not CT and has no rescale tags, because
            "HU" has no meaning for MRI or for an unrescaled dataset.
    """
    if not is_ct(volume) and not has_rescale(volume):
        raise NotCTError(
            "Hounsfield units require a CT volume or explicit RescaleSlope/"
            "RescaleIntercept tags; this volume has neither "
            f"(modality={volume.modality!r})."
        )
    values = to_raw(volume)
    if volume.rescale_applied:
        return values
    slope, intercept = rescale(volume)
    return values * slope + intercept


# ---------------------------------------------------------------------------
# Display windowing
# ---------------------------------------------------------------------------

def window(values: np.ndarray, level: float, width: float) -> np.ndarray:
    """Map values to ``[0, 1]`` using a window centre and full width.

    ``level`` lands on 0.5; anything below ``level - width/2`` clips to 0 and
    anything above ``level + width/2`` clips to 1.

    Note:
        This is the common linear form. DICOM PS3.3 C.11.2.1.2 additionally
        nudges the edges by half a unit and divides by ``width - 1``; the
        difference is invisible for real windows (tens to thousands of HU) and
        would disagree with the formula used in the UI and the docs.
    """
    if width <= 0:
        raise ValueError(f"Window width must be positive, got {width!r}.")
    values = np.asarray(values, dtype=np.float32)
    low = level - width / 2.0
    return np.clip((values - low) / width, 0.0, 1.0)


def get_preset(name: str) -> WindowPreset:
    """Look a preset up by name, case-insensitively."""
    try:
        return PRESETS_BY_NAME[name.strip().casefold()]
    except KeyError:
        available = ", ".join(p.name for p in PRESETS)
        raise KeyError(f"Unknown preset {name!r}. Available: {available}.") from None


def to_normalised_window(
    volume: VolumeData, level: float, width: float
) -> tuple[float, float]:
    """Express a window given in HU on the loader's ``[0, 1]`` scale.

    The UI sliders operate on normalised intensities, so a clinical preset has
    to be converted before it can drive them. The conversion undoes the
    rescale when the loader did not already apply it, which keeps the result
    correct for both paths.

    Returns:
        ``(level, width)`` in normalised units.

    Raises:
        ValueError: if the volume has no intensity range to map onto.
    """
    span = volume.raw_max - volume.raw_min
    if span <= 0:
        raise ValueError("Cannot window a volume with a flat intensity range.")

    if not volume.rescale_applied:
        slope, intercept = rescale(volume)
        level = (level - intercept) / slope
        width = width / slope

    return (level - volume.raw_min) / span, abs(width) / span


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _tag_float(meta: dict[str, str], key: str, default: float) -> float:
    raw = meta.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default
