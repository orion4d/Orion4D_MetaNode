# 🚀 Orion4D_Metanode — Custom Nodes ComfyUI

<div align="left">

![ComfyUI](https://img.shields.io/badge/ComfyUI-Custom_Nodes-blue?style=for-the-badge&logo=python&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Nodes](https://img.shields.io/badge/Nodes-29+-orange?style=for-the-badge)

This project brings together all my work on ComfyUI.

**Orion4D_Metanode transforms ComfyUI into a true programmable environment.**
Thanks to the **PyCode Max** engine, execute Python directly within your workflows and build your own tools, logic, and interfaces.
Dynamic routing, variable buses, enriched UI, file management, image processing...  
Everything is designed to push beyond the limits of traditional node-based systems.

✔ Compatible with the Nodes V2

## ✨ Why Orion4D_Metanode?

- Create dynamic and scalable workflows
- Eliminate complex wiring with an intelligent bus system
- Develop your own tools directly in ComfyUI
- Transform a workflow into a true programmable pipeline

</div>

## 🚧 Status

**Version: 1** (15/04/2026)

---

## 🔧 Nodes

### ⚙️ PyCode Max
> The true "brain" of this suite, run Python code directly inside your workflows.
> 
<img width="606" height="1110" alt="image" src="https://github.com/user-attachments/assets/702f3a5a-34e5-43b8-8993-c2e97a51f9af" />

- **Two modes**: direct input (`text_input`) or external file (`file`)
- **Universal inputs**: text, integers, floats, images, masks, latents, conditioning, model, clip, vae, audio, video, and custom types
- **Persistent STATE** per node between executions (resettable)
- **Configurable timeout** (5–600 sec) against infinite loops
- **Security mode**: text mode execution is locked by default (requires `"developer_mode": true` in `config.json`)
- **Automatic documentation**: comments at the top of a `.py` script are displayed in the console
- **Built-in console** with execution time and structured logging

---

### 📂 Folder File Max
> A complete visual file explorer, directly inside a ComfyUI node.
> 
<img width="1048" height="1089" alt="image" src="https://github.com/user-attachments/assets/d7393eef-8508-40c7-af11-7bfac40e924a" />
<img width="1068" height="1124" alt="image" src="https://github.com/user-attachments/assets/12f7457f-fde7-449a-ab77-d68e4c15fd8f" />

- **Grid or list view** with thumbnails generated on the fly
- **Filtering** by extension, regex (include/exclude), sorting by name/date/size
- **Navigation**: go up folders, double-click to open
- **Integrated Lightbox** to preview images, videos, and audio
- **"Explore" button** to open the folder in the system explorer (Windows/macOS/Linux)
- **Seed modes**: fixed, random, increment...
- Returns: `file_path`, `filename`, `dir_used`, `files_json`, `file_info`, `IMAGE`

---

### 📄 Load Text File
> Loads any text file and exposes its content in an editable widget.
> 
<img width="949" height="738" alt="image" src="https://github.com/user-attachments/assets/c60e0b47-92ab-4098-9f94-15f382859d25" />

- **Drag-and-drop** or file selection from the interface
- The content appears in a multiline `STRING` widget **directly editable** in the node
- Supported formats: `.txt`, `.json`, `.csv`, `.py`, `.js`, `.md`, `.yaml`, `.toml`, `.xml`, `.html`, `.sh`, `.bat`, `.ini`, `.cfg`, `.env`, `.log`
- Automatic encoding detection (UTF-8, Latin-1, CP1252...)
- Returns: `text` (STRING)

---

### 💾 Super Saver
> Advanced image and text saving with fine management of filenames and metadata.
> 
<img width="875" height="1103" alt="image" src="https://github.com/user-attachments/assets/fcfe12f8-0a63-4cdb-ae92-79e8bd472f60" />

- **Image**: PNG, JPEG, WEBP, TIFF — configurable quality per format
- **Dynamic Alpha**: additional `alpha_N` ports to save layers (managed by JS)
- **Text**: simultaneous saving of a `.txt` (or other extension) file alongside the image
- **Metadata**: JSON or free text injection into the `iTXt` chunk of the PNG (native UTF-8)
- **Naming**: prefix, timestamp (Date_Time / HHMMSS / Unix_Epoch), auto-counter, subfolders
- **Strip Workflow**: removes workflow data from PNG before saving
- Returns: `image_path`, `text_path` (STRING)

---

### 🔀 Dynamic Road
> Dynamic input router — connect N universal inputs and choose which one to transmit.
> 
<img width="1531" height="992" alt="image" src="https://github.com/user-attachments/assets/9e7731d0-4256-48e4-beb5-256a68988a89" />

- The `*` input ports automatically appear upon connection
- Each input has a **memo field** (customizable label) and a **radio toggle**
- Selection via visual interface or Python index
- Returns: the selected value, its text representation, and a detailed log

---

### 📝 Text Road
> Multi-input text concatenator with fine control per input.
> 
<img width="1250" height="850" alt="image" src="https://github.com/user-attachments/assets/e9185f96-9480-4e56-b6c4-98fa1f2ee3b1" />

- Dynamic `STRING` inputs (ports appear upon connection)
- Each input has a **memo**, an **active/inactive toggle**, a **prefix**, and a **suffix**
- **Configurable separator** (supports `\n`, `\t`, or any string)
- Returns: `text_out` (STRING)

---

### 🔀 Dynamic Splitter
> Broadcasts a single input to N dynamic outputs, with selective activation per output.
> 
<img width="1348" height="1016" alt="image" src="https://github.com/user-attachments/assets/bec16c4c-688c-43cc-99da-87241e7df216" />

- **1 input → N outputs**: the same data is broadcast to all active outputs
- Outputs appear dynamically (managed by JS)
- **Disabled** outputs emit an `ExecutionBlocker` — the downstream flow is cleanly stopped without crashing
- Each output has a **customizable label** and an **active/inactive toggle**
- Returns: up to 32 `out_N` outputs + a `log` (STRING)

---

### 🚦 Execution Gate
> Cleanly allows or blocks a flow based on a boolean.
> 
<img width="469" height="284" alt="image" src="https://github.com/user-attachments/assets/907f1395-8fee-4318-af3c-8a172823bbae" />

- **Open ✅** → the data passes as is
- **Blocked 🚫** → emits an `ExecutionBlocker`: the entire downstream graph is stopped without error
- Compatible with the `boolean` output of the **Boolean Switch**
- Accepts any type as input (`*`)
- Returns: `output` (`*`)

---

### 🚌 Variable Bus (Set) + Variable Bus (Get) + Variable Bus (Clear)
> Share any data between distant nodes **without visible cables**, with intelligent auto-connection and strong typing.

**Principle**
The bus relies on a common identification triplet for Set and Get:
- `variable_name`: logical name of the variable (e.g., `my_image`, `main_prompt`)
- `data_type`: strong type (`IMAGE`, `LATENT`, `MASK`, `STRING`, `INT`, `FLOAT`, `MODEL`, `CONDITIONING`, `CLIP`, `VAE`, `LIST`, `*`)
- `execution_phase`: execution phase (1 to 8) to order multiple Sets/Gets sharing the same name

As soon as a Set and a Get share the same triplet, a `sync → dependency` link is **automatically created** by JavaScript — the user has no cables to draw. This link is invisible by default ("wireless bus" effect) but actually exists in the graph, ensuring the execution order on the ComfyUI side.

**Variable Bus (Set)**
- Stores the data in a global bus (Python `OrderedDict` in memory) under the declared triplet
- `passthrough` output: returns the original data, typed according to `data_type` (corresponding slot color)
- `sync` (INT) output: write tick, auto-connected to the corresponding Get's `dependency`
- `OUTPUT_NODE = True` + `IS_CHANGED = NaN`: executes on every run, ensuring the written value is always fresh
- FIFO of 64 variables max with eviction of the oldest and VRAM release (`torch.cuda.empty_cache()`)

**Variable Bus (Get)**

<img width="1924" height="1099" alt="image" src="https://github.com/user-attachments/assets/180a63e8-9655-46ac-8dfe-29a8d4438c47" />

- Retrieves the data from the global bus by its triplet
- `output` output: dynamically typed according to `data_type`
- `dependency` port: auto-connected to the corresponding Set's `sync` (rendered invisible)
- Intelligent auto-reconnection: if `variable_name`, `data_type`, or `execution_phase` changes, the link is remade to the correct Set
- If the variable is not found → clean `ExecutionBlocker` (no crash)

**Variable Bus (Clear) — central controller**
Mainly used to **control the display of bus cables** in the graph:
- `show_bus_links` (hidden/visible toggle): toggles the visibility of all `sync → dependency` links in the workflow in real-time
- `clear_mode`:
  - `none` (default): does nothing, the node serves solely as a visual controller
  - `all`: completely empties the bus
  - `single`: deletes only the named variable
  - `all_except`: empties everything except the named variable
- **🧹 Clear now** button: executes the clear immediately via an HTTP route, without having to run the workflow
- **🔄 Refresh bus links** button: forces a complete rescan of Set/Get auto-connections (useful after importing a workflow or manual manipulations)
- The first `Variable Bus (Clear)` found in the graph acts as the authority for the visibility toggle; without a Clear placed, cables are hidden by default

> 💡 Ideal for sharing a model, an image, a text, or a latent between distant branches without extending cables. Auto-connection via triplet makes usage seamless: you declare it, it connects itself.

---

### 📋 List Selector Max
> A "must-have" for prompt generation: Multi-group line selector from `.txt` / `.csv` files, with independent seed per group.
> - Bonus: **lists_starter_pack** included containing 82 files
> Tip: the result can be enriched via PyCode Max with an LLM model, entirely automatically!
> 
<img width="683" height="1163" alt="image" src="https://github.com/user-attachments/assets/892fa828-94b7-43cf-9c90-dc6c039518bb" />
<img width="1224" height="979" alt="image" src="https://github.com/user-attachments/assets/f98734cf-22ec-46de-94eb-0924a0735df8" />

- **Multi-groups**: each group points to a different file, with its own seed and separator
- **Selection modes per group**: `select` (manual index), `randomize`, `increment`, `decrement`
- **Inline editing**: modify the selected line directly in the node before sending it
- **Manual override**: enter free text in the preview field to bypass the selection
- **Path tokens**: `{COMFY}` and `{CUSTOM}` for portable paths between machines
- **Security**: access is restricted to the ComfyUI root and the defined custom folder
- Returns: `concatenated` (STRING), `lines_json` (STRING), `total_count` (INT)

---

### 🎚️ Parametric Slider

> Dynamically configurable slider from JSON files.
> <img width="849" height="554" alt="image" src="https://github.com/user-attachments/assets/0d187e92-aec2-4087-962d-1e34da1a1658" />
<img width="925" height="779" alt="image" src="https://github.com/user-attachments/assets/a788dfe6-e709-41ab-b5fa-5f4d29a5601b" />

- Load your **range presets** from the `json_slider/` folder
- Supports `min`, `max`, `step`, `default`, `label`, `precision`, `unit`
- **Modes post-generation**: `fixed`, `increment`, `decrement`, `randomize`
- Returns: `float_val`, `int_val`, `text_val` (with unit), `label`, `min`, `max`, `step`, `log`

**Preset example (`json_slider/px_1_to_8192.json`):**
```json
{ "min": 1, "max": 8192, "step": 64, "default": 512, "label": "Resolution", "precision": 0, "unit": "px" }
```

---

### 🔽 Master Combo Box
> Double dropdown menu linked to JSON files in the `dropdowns/` folder.
> 
<img width="1084" height="829" alt="image" src="https://github.com/user-attachments/assets/0cfbc386-411f-47b3-98b2-50b88a36b247" />

- **Menu 1**: chooses the JSON file (category)
- **Menu 2**: displays the content of the selected file
- **Refresh** button to reload without restarting ComfyUI
- Returns: `selected_text` (STRING)

---

### 📂 Model Selector
> Navigate through `models/` subfolders with a two-level selector.
> 
<img width="568" height="689" alt="image" src="https://github.com/user-attachments/assets/e110e697-61ef-4e63-a238-8503b7d368b1" />

- **Menu 1**: category (`checkpoints`, `loras`, `upscale_models`...)
- **Menu 2**: file in that category
- Automatic filter on `.safetensors`, `.gguf`, `.pth`, `.bin` extensions
- Returns: `absolute_path`, `relative_path`, `filename_only`, `any_path`, `any_filename`

---

### 🎨 Color Picker
> Opens the native OS color palette to select a color.
> 
<img width="1123" height="1088" alt="image" src="https://github.com/user-attachments/assets/5d6ca7aa-b86c-4bdf-b6e3-465b9cb1e81c" />

- Color preview drawn directly on the node
- Returns: `hex_value` (e.g., `#F54927`), `rgb_string` (e.g., `245, 73, 39`), `R`, `G`, `B` channels

---

### 📈 Curves Pro + 🖼️ Curves Pro Image
> Photoshop-style RGB curves editor, with live preview.
> 
<img width="1847" height="943" alt="image" src="https://github.com/user-attachments/assets/3a5fe5a9-a6ea-412c-9d45-2f0f70936f63" />
<img width="1230" height="1109" alt="image" src="https://github.com/user-attachments/assets/de0a5aa9-c390-42f9-abf4-479f379ab375" />
<img width="1694" height="1032" alt="image" src="https://github.com/user-attachments/assets/e420a817-bf39-4763-a740-5dd17f9329f4" />

**Curves Pro (editor):**
- Interactive canvas for **RGB**, **R**, **G**, **B** channels
- **Live histogram** calculated from the connected image
- **Grid snapping** (3 density levels)
- **Preset system**: save/load from `json_curves/`
- Returns: `curves_json` (STRING)

**Curves Pro Image (receiver):**
- Loads an image (native Load Image style)
- Receives `curves_json` and applies curves in real-time
- **Live preview** sent back to the editor node via WebSocket
- Returns: `IMAGE`, `MASK`, `log`

---

### 🎨 LUT Generator + 🎬 LUT Manager
> Creation and application of `.cube` 3D LUTs directly in ComfyUI.
> 
<img width="1873" height="1137" alt="image" src="https://github.com/user-attachments/assets/3f179096-d6c1-4697-8b90-abfc93af72c9" />
<img width="818" height="818" alt="image" src="https://github.com/user-attachments/assets/916de328-0781-44c7-9e41-fbf8cdd8517b" />
<img width="1742" height="946" alt="image" src="https://github.com/user-attachments/assets/4940b4e0-3db4-4a56-b09d-ca0f5dd9985b" />
<img width="1717" height="943" alt="image" src="https://github.com/user-attachments/assets/87a985c1-7ed0-4894-beca-766ee5066f28" />

**LUT Generator:**
- Generates a 3D LUT from two images (before/after) — ideal for **capturing the look of an existing grading**
- Fine parameters: LUT size (9–65), number of samples, interpolation method (`linear`, `nearest`, `cubic`), gaussian blur, identity anchoring
- **No-save mode** (`save_lut = False`): calculates the LUT in memory to test without writing to disk
- Export formats: `.cube`, `.3dl`, `.csp`
- Calibration images stored in `lut_files/images_calibration/` to facilitate comparisons
- Returns: `preview_image`, `tested_image`, `lut_path`

**LUT Manager:**
- Applies any `.cube` LUT to an image, via direct path or selection in `lut_files/`
- Control **intensity** (0–2) and **opacity** (0–1) independently
- Choice of data/table orders (`BGR`/`RGB`) for maximum compatibility with commercial LUTs
- **Memory cache**: the LUT is only reloaded from disk if the file has been modified
- Returns: `IMAGE`, `lut_path`

---

### 🔍 Image Comparer *(Legacy)*

<img width="1001" height="1015" alt="image" src="https://github.com/user-attachments/assets/10cea0dc-f84a-4019-b78a-1decc7267841" />

> Interactive image comparer, optimized for the classic ComfyUI interface (LiteGraph).
- **Direct interaction**: toggle between A and B by clicking the image, or via the two indicator circles under the image
- **HD rendering**: native drawing on the LiteGraph canvas, remains sharp at all zoom levels
- **Different sizes**: automatic alignment to the largest dimension, letterbox on black background — ideal for comparing an original and its upscale
- **Compatible with Nodes 2.0** with two limitations: clicking in the image does not toggle (use the circles at the bottom of the node); hovering darkens the image (native Nodes 2.0 rendering superimposes)
- **Ideal use**: users of the classic ComfyUI interface (LiteGraph)

### 🔍 Image Comparer V2 *(beta, optimized for Nodes 2.0)*

<img width="846" height="991" alt="image" src="https://github.com/user-attachments/assets/c18d7d52-8a1a-42db-8261-b74ca09f2f64" />

> Interactive image comparer, designed for the new ComfyUI Nodes 2.0 interface.
- **Two modes**: `slide` (vertical slider reveals B over A) and `click` (toggle between A and B on click)
- **Swap A/B button**: reverses the two images without rewiring connections (slide mode only)
- **Different sizes**: automatic alignment on the largest dimension, letterbox on black background — ideal for comparing an original and its upscale
- **Limitation**: when ComfyUI canvas is zoomed (values above 100%), progressive pixelation of image display
- **Ideal use**: users of the new Nodes 2.0 interface

---

### 🎨 Color Pro — Modular color grading chain

<img width="869" height="1075" alt="image" src="https://github.com/user-attachments/assets/e7436444-8954-4a57-bad8-4b7bcb036d56" />

> A pipeline color effect system: **emitter** nodes produce `COLOR_FX` descriptors, which the **receiver** node applies in order to an image. Each emitter can also work in **standalone** mode (direct image in/out).

**🎨 Color Pro Receiver** — Receiver / application point
- Receives an `IMAGE` + dynamic slots `fx_1`, `fx_2`, ... of type `COLOR_FX`
- Applies effects in the numerical order of the slots
- Slots are automatically added upon connection (dynamic pattern)
- Returns: `image` (IMAGE), `log` (STRING)

**Available emitters:**

| Node | Description |
|------|-------------|
| **🎨 Channel Mixer FX** | Mixes R/G/B channels to rebuild each output channel. Monochrome mode and luminosity preservation. Photoshop Channel Mixer equivalent. |
| **🎨 Color Balance FX** | Shadows / Midtones / Highlights adjustment like Photoshop. "Preserve Luminosity" toggle. |
| **🎨 CSS Filters FX** | Applies standard CSS filters: `brightness`, `contrast`, `saturate`, `hue-rotate`, `sepia`, `grayscale`, `invert`. |
| **🎨 Hue/Sat/Light FX** | Global HSL adjustment or targeted by hue family (Reds, Yellows, Greens, Cyans, Blues, Magentas) with smooth gaussian transition. Colorize mode included. |
| **🎨 Photo Filter FX** | Color warming/cooling filter with opacity and luminosity preservation mode, inspired by Photoshop's Photo Filter. |
| **🎨 Vibrance FX** | Vibrance adjustment (skin tone protection) and global Saturation, independently controllable. |
| **🎨 Curves Pro** | Compatibility with the tool |

> 💡 Emitters can be used in **chain mode** (`fx` output → `fx_N` slot of Receiver) or **standalone mode** (direct image in/out), or both simultaneously.

---

### 📦 List Packer / Dict Packer / 📤 List Unpacker / 🖨️ Logger

<img width="1399" height="1037" alt="image" src="https://github.com/user-attachments/assets/479d8312-1b36-4598-b99f-a3e9e74c28c3" />
<img width="741" height="1066" alt="image" src="https://github.com/user-attachments/assets/f882f421-d939-48cf-8823-12f8ec7d9eff" />
<img width="756" height="1101" alt="image" src="https://github.com/user-attachments/assets/261803a3-22a0-4aa1-82a8-6d7a038030b7" />
<img width="524" height="375" alt="image" src="https://github.com/user-attachments/assets/f091ac92-dbb0-4265-abd6-29e5d0ec633e" />

| Node | Behavior |
|------|-------------|
| **List Packer (Infinite)** | Dynamic `item_N` ports → `list_out` output |
| **Dict Packer (Infinite)** | `val_N` ports + dynamic `key_N` fields → `dict_out` output |
| **List Unpacker (Dynamic)** | `list_in` input → up to 32 `item_N` outputs |
| **Logger (Debug Console)** | Displays type, shape, and value of any data |

> All Packer/Unpacker ports appear and disappear automatically based on connections.

---

## 🔧 Installation

```bash
cd ComfyUI/custom_nodes
git clone [https://github.com/your-username/Orion4D-coder.git](https://github.com/your-username/Orion4D-coder.git)
```

Restart ComfyUI. The nodes will appear in the **`Orion4D_MetaNode`** category.

> **Optional dependencies** for LUT Generator: `pip install scipy opencv-python`

---

## ⚙️ Configuration

### Developer mode (PyCode Max)
By default, code execution in `text_input` mode is **disabled** to protect against malicious shared workflows.

Edit `config.json` at the root of the custom node:
```json
{
    "developer_mode": true
}
```

> ⚠️ Only enable this option on your personal machine. Never share workflows containing unverified code in `text_input` mode.

---

### 📂 Folder File Max — Custom Folders

#### Why an allow-list?

The HTTP routes for **Folder File Max** are exposed on the ComfyUI server. Without restriction, any client on the same network could enumerate and read any file on the disk. By default, only ComfyUI's internal roots are accessible:

| Label | Resolved path |
|-------|--------------|
| `{COMFY}/input` | `ComfyUI/input/` |
| `{COMFY}/output` | `ComfyUI/output/` |
| `{COMFY}/temp` | `ComfyUI/temp/` |
| `{COMFY}/models` | `ComfyUI/models/` |

Any path outside these roots is **silently refused** (the node returns empty outputs and logs the reason in the console).

#### Add folders via environment variable

Declare the **`ORION4D_FOLDER_ROOTS`** variable before launching ComfyUI. Paths are separated by your OS separator (`;` on Windows, `:` on Linux/macOS).

**Windows — Command Prompt (cmd)**
```bat
set ORION4D_FOLDER_ROOTS=F:\lists;C:\Users\orion4d\Desktop\IN
python main.py
```

**Windows — PowerShell**
```powershell
$env:ORION4D_FOLDER_ROOTS = "F:\lists;C:\Users\orion4d\Desktop\IN"
python main.py
```

**Windows — Permanent (user session)**
```bat
setx ORION4D_FOLDER_ROOTS "F:\lists;C:\Users\orion4d\Desktop\IN"
```
> Restart your terminal after `setx` for the variable to be recognized.

**Linux / macOS — Current session**
```bash
export ORION4D_FOLDER_ROOTS="/home/orion4d/photos:/mnt/nas/shoots"
python main.py
```

**Linux / macOS — Permanent** — add the following line in `~/.bashrc` or `~/.zshrc`:
```bash
export ORION4D_FOLDER_ROOTS="/home/orion4d/photos:/mnt/nas/shoots"
```

#### Verify that roots are loaded

When ComfyUI starts, the node displays the complete list of allowed roots in the console:

```
[FolderFileMax] Allowed roots (6):
  {COMFY}/input                  → C:\ComfyUI\input
  {COMFY}/output                 → C:\ComfyUI\output
  {COMFY}/temp                   → C:\ComfyUI\temp
  {COMFY}/models                 → C:\ComfyUI\models
  F:\lists                       → F:\lists
  C:\Users\orion4d\Desktop\IN    → C:\Users\orion4d\Desktop\IN
```

If a declared folder does not exist at startup, it is silently ignored (no error, no entry in the list).

#### Security behavior

- Paths containing `..` are rejected (no directory traversal).
- Only media extensions are served by the `/thumbnail` and `/view` routes — no `.py`, `.json`, `.exe`, etc. files are ever transmitted to the browser.
- Navigation is **locked to the chosen root** in the dropdown: it is impossible to go up above it via the interface.
- Windows Junction Points pointing outside an allowed root are **blocked**.

> ⚠️ **Network use / workflow sharing**: any root added via `ORION4D_FOLDER_ROOTS` is accessible to **all clients** that can reach your ComfyUI instance. Do not expose ComfyUI to the Internet with personal folders in the allow-list.

---

### 📋 List Selector Max — Allow a custom root folder

#### Security model

By default, **List Selector Max** restricts access to `.txt` / `.csv` files located in the ComfyUI root folder (and all its subfolders). The `{COMFY}` token always points to this root.

```
{COMFY}/custom_nodes/Orion4D_MetaNode/Lists/styles.txt  ✅ allowed
C:\Users\orion4d\Desktop\prompts\abstract.txt           ❌ refused by default
```

#### Allow an external folder via the `custom_root` widget

The node exposes a **`custom_root`** field directly in its interface. Enter the absolute path of the root folder you want to allow:

```
C:\Users\orion4d\Desktop\prompts
```

Once defined, the `{CUSTOM}` token is resolved to this folder. You can use it in your group paths:

```
{CUSTOM}/styles/abstract.txt
{CUSTOM}/moods.csv
```

Validation occurs at each execution: if the folder does not exist or if the path attempts to break out of the root via `..`, access is refused and the group returns an empty selection.

#### Use `{COMFY}` and `{CUSTOM}` together

Both tokens can be used together within the same node. One group can point to `{COMFY}/Lists/cameras.txt` and another to `{CUSTOM}/moods.csv` — each path is validated independently against its root.

```
Group 1  →  {COMFY}/Lists/cameras.txt      (in ComfyUI, portable)
Group 2  →  {CUSTOM}/abstract_moods.txt    (local personal folder)
```

#### ⚠️ Warning for workflow sharing and network use

> **Custom root = local absolute path.** A workflow that contains a `custom_root` or `{CUSTOM}` paths **will not work** as is on another machine, or if ComfyUI is shared on a network with other users.
>
> - **Do not share** workflows with `custom_root` filled in if other people have access to your ComfyUI instance — the HTTP route `/orion4d/lsm/list_dir` and `/orion4d/lsm/read_file` will respond to **all network clients** for files in this root.
> - **Prefer `{COMFY}`** for anything that needs to remain portable: place your lists in a ComfyUI subfolder (e.g., `ComfyUI/Lists/`) and reference them with `{COMFY}/Lists/file.txt`.
> - If you must share a workflow using `{CUSTOM}`, **clear `custom_root`** before exporting or replace the paths with `{COMFY}` equivalents.

---

<div align="center">

Made with ❤️ for the ComfyUI community · **Orion4D**

</div>
