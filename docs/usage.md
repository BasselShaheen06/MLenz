# Usage

## Loading data

**Load NIfTI** — opens a file picker for `.nii` or `.nii.gz` files.

**Load DICOM** — opens a folder picker. MPRViewer reads the DICOM series
inside and sorts slices automatically using DICOM position metadata
(more reliable than filename sorting).

While loading, a progress overlay appears and controls are disabled.
Large volumes (>500 slices) may take a few seconds on first load.
Subsequent slice navigation is fast because slices are cached in memory.

---

## Layout

```
┌─────────────────────────────────────────────────┐
│  TopBar: Load · Load DICOM · 3D ☐ · Preset      │
│          Reset · ☀/🌙                           │
├─────────────────────────┬───────────────────────┤
│      Axial              │      Sagittal          │
│   (Z slices)            │   (X slices)           │
├─────────────────────────┼───────────────────────┤
│      Coronal            │   3D Volume (VTK)      │
│   (Y slices)            │   hidden by default    │
└─────────────────────────┴───────────────────────┘
```

The 3D panel is hidden until you tick the **3D** checkbox in the top bar.

---

## Crosshair navigation

### Drag
Each crosshair line is draggable. Click and drag the red dashed line in
any viewport — all three planes update in real time to reflect the new position.

### Click to jump
Left-click anywhere in a viewport to jump the crosshair to that position.
All three planes synchronise immediately.

### Slice slider
The slider below each viewport moves through slices in that plane independently.
The slice counter in the title bar shows current position (e.g. "45 / 180").

---

## Zoom and pan

| Action | Effect |
|---|---|
| Scroll wheel | Zoom in / out, centred on cursor |
| Right-click drag | Pan |
| Double-click | Reset zoom to fit image |

Zoom state is preserved when you move to a different slice — the view
stays at the same zoom and pan position.

---

## Window / Level (W/L)

Window and Level are the radiological standard controls for image brightness
and contrast. Each viewport has its own embedded controls bar with W/L sliders.

| Slider | Effect |
|---|---|
| **W (Window width)** | Contrast. Narrow = high contrast. Wide = low contrast. |
| **L (Window level)** | Brightness centre. High = brighter overall. Low = darker. |

Each plane has independent W/L. This is intentional — in a CT scan you
typically use different settings for soft tissue (W=400, L=40) vs bone
(W=1500, L=300).

!!! info "Why not Brightness / Contrast?"
    Window and Level are the clinical standard terms. They map directly
    to the display pipeline: L sets the centre of the intensity range
    shown, W sets how wide that range is. Values outside the window
    clip to black or white.

---

## Colormaps

Each plane has its own colormap dropdown in the viewport controls. Default is **gray**.

| Colormap | Best for |
|---|---|
| gray | All standard diagnostic use |
| hot / plasma / inferno | Highlighting bright signal (e.g. gadolinium enhancement) |
| viridis / cividis | Perceptually uniform — good for publications |
| bone | Radiograph-style CT display |
| jet | Legacy — avoid for diagnosis, can obscure detail |

---

## Cine playback

Each plane has its own **▶ Play** button in the viewport controls. Playback runs
at 20 fps and loops back to slice 0 when it reaches the end.
You can play multiple planes simultaneously.

Click **⏸ Pause** to stop.

---

## 3D volume rendering

Tick the **3D** checkbox in the TopBar to show the embedded VTK panel.

Interact with the 3D model:
- **Left-click drag** — rotate
- **Right-click drag** — zoom
- **Middle-click drag** — pan

Select a transfer function **Preset** from the dropdown next to the checkbox:

| Preset | Best for |
|---|---|
| `mri_default` | General MRI — soft tissue contrast |
| `bone` | CT — bony structures and calcifications |
| `angio` | MRA / CTA — vessels and blood |
| `pet` | PET scans — hot-metal colormap |

---

## Reset

Click **Reset** in the TopBar to:
- Return crosshairs to the centre of the volume
- Restore W/L to defaults (center=0.5, width=1.0)
- Clear zoom / pan state on all three planes

---

## Theme

Click the **☀ / 🌙** button in the TopBar to toggle light and dark mode.
The canvas background stays black in both modes — this is intentional.
Medical images are read on dark backgrounds in clinical practice.