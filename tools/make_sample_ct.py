"""Generate a synthetic head CT for trying the viewer.

MLenz ships no patient data. This writes a multi-frame DICOM whose voxels are
already in Hounsfield units (``RescaleSlope`` 1, ``RescaleIntercept`` -1024), so
it exercises the CT path end to end: rescale tags, HU conversion and the window
presets.

The file is a *demo*, not a conformant Enhanced CT: it stores several frames in
a classic CT Image Storage object, which SimpleITK/GDCM read as a 3-D volume.

Usage::

    python tools/make_sample_ct.py
    python tools/make_sample_ct.py --out samples/head.dcm --slices 64
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

# Allow `python tools/make_sample_ct.py` from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mlenz.core.phantom import head_ct  # noqa: E402

CT_IMAGE_STORAGE = "1.2.840.10008.5.1.4.1.1.2"


def write_sample_ct(
    path: str | Path,
    size: int = 128,
    slices: int = 48,
    spacing: float = 1.5,
    slice_thickness: float = 3.0,
    seed: int = 0,
) -> Path:
    """Write a synthetic head CT as a multi-frame DICOM and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    hu = head_ct(
        size=size,
        slices=slices,
        spacing=spacing,
        slice_thickness=slice_thickness,
        seed=seed,
    )
    # DICOM stores unsigned integers; the intercept puts them back in HU.
    stored = np.clip(np.round(hu) + 1024.0, 0, 4095).astype(np.uint16)

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = CT_IMAGE_STORAGE
    file_meta.MediaStorageSOPInstanceUID = generate_uid()
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    ds = FileDataset(str(path), {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID

    ds.PatientName = "Synthetic^Phantom"
    ds.PatientID = "PHANTOM"
    ds.StudyDescription = "MLenz synthetic head CT"
    ds.SeriesDescription = "Synthetic head CT"
    ds.Modality = "CT"

    ds.Rows, ds.Columns = size, size
    ds.NumberOfFrames = slices
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0

    ds.RescaleSlope = 1.0
    ds.RescaleIntercept = -1024.0
    ds.WindowCenter = 40
    ds.WindowWidth = 80

    ds.PixelSpacing = [spacing, spacing]
    ds.SliceThickness = slice_thickness
    ds.SpacingBetweenSlices = slice_thickness
    ds.ImagePositionPatient = [0.0, 0.0, 0.0]
    ds.ImageOrientationPatient = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    ds.SliceLocation = 0.0

    ds.PixelData = stored.tobytes()
    ds.save_as(str(path))
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        default="samples/sample_ct_head.dcm",
        help="output file (default: samples/sample_ct_head.dcm)",
    )
    parser.add_argument("--size", type=int, default=128, help="in-plane voxels")
    parser.add_argument("--slices", type=int, default=48, help="axial slices")
    parser.add_argument("--spacing", type=float, default=1.5, help="mm per pixel")
    parser.add_argument(
        "--slice-thickness", type=float, default=3.0, help="mm between slices"
    )
    args = parser.parse_args(argv)

    path = write_sample_ct(
        args.out,
        size=args.size,
        slices=args.slices,
        spacing=args.spacing,
        slice_thickness=args.slice_thickness,
    )
    megabytes = path.stat().st_size / 1_048_576
    print(f"wrote {path}  ({megabytes:.1f} MB)")
    print("Open it in MLenz with Load DICOM, then pick a preset (Brain, Bone, Lung).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
