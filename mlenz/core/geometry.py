"""Pure geometry helpers shared by the viewer.

No Qt, no file I/O — safe to import in tests and scripts.
"""

from __future__ import annotations


def aspect_scale(col_spacing: float, row_spacing: float) -> float:
    """Horizontal scale that gives pixels their true physical proportions.

    A slice is a grid of pixels whose physical width (``col_spacing``) and
    height (``row_spacing``) usually differ — for example 0.5 x 0.5 mm
    in-plane but 5 mm between slices. Displaying such a slice with square
    pixels distorts anatomy, so the horizontal axis is scaled by the ratio
    of column spacing to row spacing.

    Args:
        col_spacing: Physical width of one pixel, in millimetres.
        row_spacing: Physical height of one pixel, in millimetres.

    Returns:
        Multiplier for the horizontal axis. ``1.0`` when pixels are already
        square or when the spacing is invalid.
    """
    if col_spacing <= 0 or row_spacing <= 0:
        return 1.0
    return col_spacing / row_spacing
