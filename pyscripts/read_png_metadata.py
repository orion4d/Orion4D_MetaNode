# read_png_metadata.py
# Script PyCodeMax — Orion4D_MetaNode
#
# Entrée  : txt_in_1 → chemin absolu du PNG (sortie image_path du Super Saver)
# Sorties :
#   txt_out_1 → JSON ComfyUI workflow (structure complète, format graph)
#   txt_out_2 → JSON ComfyUI API (format prompt/API, comme api.json)
#   txt_out_3 → Métadonnées injectées en texte brut (description + metadata)

import os, struct, json
from PIL import Image

image_path = str(IN.get("txt_in_1", "")).strip().strip('"').strip("'")

if not image_path or not os.path.exists(image_path):
    raise FileNotFoundError(f"Fichier introuvable : '{image_path}'")
if not image_path.lower().endswith(".png"):
    raise ValueError("Ce script fonctionne uniquement sur des PNG.")

# ── Lecture des chunks ───────────────────────────────────────────────────────
img = Image.open(image_path)
chunks = dict(img.text) if hasattr(img, "text") and img.text else {}

try:
    with open(image_path, "rb") as f:
        raw = f.read()
    pos = 8
    while pos < len(raw) - 12:
        length = struct.unpack(">I", raw[pos:pos+4])[0]
        ctype  = raw[pos+4:pos+8].decode("latin-1")
        data   = raw[pos+8:pos+8+length]
        pos   += 12 + length
        if ctype in ("tEXt", "iTXt"):
            ni = data.find(b"\x00")
            if ni == -1: continue
            key = data[:ni].decode("latin-1", errors="replace")
            if key in chunks: continue
            if ctype == "tEXt":
                val = data[ni+1:].decode("latin-1", errors="replace")
            else:
                rest = data[ni+1:]
                nuls = [i for i, b in enumerate(rest) if b == 0]
                val  = rest[nuls[2]+1:].decode("utf-8", errors="replace") if len(nuls) >= 3 else rest.decode("utf-8", errors="replace")
            chunks[key] = val
except Exception as e:
    print(f"⚠️ lecture binaire : {e}")

# ── Sortie 1 : workflow (format graph ComfyUI) ───────────────────────────────
workflow_out = ""
if "workflow" in chunks:
    try:
        workflow_out = json.dumps(json.loads(chunks["workflow"]), indent=2, ensure_ascii=False)
    except Exception:
        workflow_out = chunks["workflow"]
OUT["txt_out_1"] = workflow_out

# ── Sortie 2 : prompt (format API ComfyUI) ───────────────────────────────────
# Le chunk "prompt" contient directement le JSON API (équivalent api.json)
api_out = ""
if "prompt" in chunks:
    try:
        api_out = json.dumps(json.loads(chunks["prompt"]), indent=2, ensure_ascii=False)
    except Exception:
        api_out = chunks["prompt"]
OUT["txt_out_2"] = api_out

# ── Sortie 3 : métadonnées injectées, texte brut ─────────────────────────────
user_parts = []
for k in ("description", "metadata"):
    if k in chunks and chunks[k].strip():
        user_parts.append(chunks[k].strip())
OUT["txt_out_3"] = "\n\n".join(user_parts)

# ── Console ───────────────────────────────────────────────────────────────────
print(f"📄 {os.path.basename(image_path)} — chunks : {', '.join(chunks.keys()) if chunks else 'aucun'}")