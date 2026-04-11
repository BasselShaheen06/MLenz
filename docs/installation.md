# Installation

## Requirements

- Python 3.10 or newer
- Windows 10/11 recommended (Qt + VTK tested there)

## Install from source

```bash
git clone https://github.com/BasselShaheen06/MPR_Viewer.git
cd MPR_Viewer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Run

```bash
python main.py
```

## Optional: editable install

```bash
pip install -e .
mprviewer
```

## Data notes

- Supported formats: `.nii`, `.nii.gz`, DICOM series folders, and single DICOM files.
- Large volumes benefit from an SSD for faster series loading.
