# Usage

## Loading data

| Button | What it does |
|---|---|
| **Load NIfTI** | Opens a file picker for `.nii` or `.nii.gz` |
| **Load DICOM** | Opens a folder picker — reads the series inside, sorted by position |

While loading, a progress overlay appears and controls are disabled.
The load runs in a background thread so the UI stays responsive.

---

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  TopBar: Load NIfTI · Load DICOM · [3D ☐] [Preset ▾]    │
│          Reset · ☀/🌙                                    │
├──────────────────────────┬───────────────────────────────┤
│  Axial          N/M      │  Sagittal          N/M        │
│  [image]                 │  [image]                      │
│  ◀─── slice ───▶        │  ◀─── slice ───▶             │
│  ▶ [gray ▾] W── L──    │  ▶ [gray ▾] W── L──         │
│  ✏ 🗑 💾               │  ✏ 🗑 💾                    │
├──────────────────────────┼───────────────────────────────┤
│  Coronal        N/M      │  3D Volume (hidden by default) │
│  [image]                 │                               │
│  ◀─── slice ───▶        │  (tick 3D checkbox to show)   │
│  ▶ [gray ▾] W── L──    │                               │
│  ✏ 🗑 💾               │                               │
└──────────────────────────┴───────────────────────────────┘
│  Status bar                                              │
└──────────────────────────────────────────────────────────┘
```

---

## Crosshair navigation

### Drag
Each red dashed crosshair line is draggable. Hover over a line until it
highlights, then click and drag. All three planes update in real time.
A hollow red circle marks the intersection point.

### Click to jump
Left-click anywhere inside a viewport to jump the crosshair to that position.

### Slice slider
The slider below each viewport moves through slices for that plane independently.
The counter in the title bar shows `current / total`.

---

## Zoom and pan

| Action | Effect |
|---|---|
| Scroll wheel | Zoom in / out centred on cursor |
| Right-click drag | Pan the image |
| Double-click | Reset zoom and pan to fit |

Zoom state is preserved when you change slices — the view stays at the
same zoom and pan position.

---

## Per-viewport controls

Each viewport has its own embedded control bar:

| Control | Effect |
|---|---|
| **▶ / ⏸** | Play or pause cine for this plane at 20 fps |
| **Colormap dropdown** | Change colormap for this plane only |
| **W slider** | Window width — contrast |
| **L slider** | Window level — brightness centre |
| **✏ Annotate** | Toggle freehand drawing mode |
| **🗑 Clear** | Remove all annotations from this plane |
| **💾 Save** | Export viewport (image + annotations) as PNG |

---

## Window / Level

W and L are the radiological standard for controlling image display:

$$\text{pixel} = \text{clip}\!\left(\frac{I - (L - W/2)}{W},\ 0,\ 1\right)$$

| Slider | Effect |
|---|---|
| **W (width)** | Contrast. Narrow = high contrast. Wide = low contrast. |
| **L (level)** | Brightness centre. High = brighter. Low = darker. |

Each plane has independent W/L — standard PACS behaviour.

!!! info "Why not Brightness/Contrast?"
    Window and Level are the clinical standard terms. They directly define
    which intensity range maps to the full display scale.

---

## Colormaps

Each plane has its own colormap. Default is **gray**.

| Colormap | Best for |
|---|---|
| gray | All standard diagnostic work |
| hot / plasma / inferno | Highlighting bright signal |
| viridis / cividis | Perceptually uniform — publications |
| bone | Radiograph-style CT |
| jet | Legacy — avoid for diagnosis |

---

## Cine playback

Click **▶** on any viewport to animate through slices at 20 fps. Click
**⏸** to pause. Each plane has independent play/pause — you can play
multiple planes simultaneously.

---

## Annotation mode

1. Click **✏ Annotate** on any viewport — button turns teal
2. Cursor changes to a crosshair
3. Click and drag to draw freehand strokes (bright yellow)
4. Crosshair lines lock while drawing to avoid accidental movement
5. Click **🗑 Clear** to remove all annotations on that plane
6. Click **💾 Save** to export the viewport with annotations as PNG

---

## 3D volume rendering

Tick the **3D** checkbox in the TopBar to show the embedded VTK panel.

| Interaction | Effect |
|---|---|
| Left-click drag | Rotate |
| Right-click drag | Zoom |
| Middle-click drag | Pan |

**Preset** dropdown (next to the checkbox):

| Preset | Best for |
|---|---|
| `mri_default` | General MRI, soft tissue |
| `bone` | CT, bony structures |
| `angio` | MRA/CTA, vessels |
| `pet` | PET scans, hot-metal colormap |

---

## Reset

Click **Reset** in the TopBar to restore crosshairs to centre, W/L to
defaults, and clear all zoom/pan states on all three planes.

---

## Theme

Click **☀ / 🌙** in the TopBar to toggle light and dark mode.
The canvas background stays black in both — medical images are always
read on a dark background in clinical practice.