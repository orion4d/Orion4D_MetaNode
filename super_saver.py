# --- START OF FILE super_saver.py ---
# Super Saver v5 - Orion4D_MetaNode
#
# Zéro dépendance externe — uniquement PIL (Pillow) déjà inclus dans ComfyUI.
#
# Entrées :
#   image, caption_image, alpha_1…N (dynamiques)
#   txt          ← sauvegarde fichier texte + métadonnée PNG "description"
#   add_metadata ← JSON ou texte libre injecté en chunk tEXt "metadata" dans le PNG
#
# Globaux : timestamp_mode / overwrite / counter_padding / strip_workflow
# Par catégorie : sub_folder / prefix / format / enable
#
# Sorties : image_path (STRING), text_path (STRING)

import os
import json
import datetime
import time
import struct
import numpy as np
import folder_paths
from PIL import Image
from PIL.PngImagePlugin import PngInfo

try:
    import tifffile
    _TIFFFILE = True
except ImportError:
    _TIFFFILE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dir(base: str, sub: str) -> str:
    sub = sub.strip().replace("\\", "/")
    full = os.path.join(base, sub) if sub else base
    os.makedirs(full, exist_ok=True)
    return full


def _build_path(prefix: str, ts_mode: str, pad: int, ext: str,
                out_dir: str, overwrite: bool) -> str:
    ts  = ""
    now = datetime.datetime.now()
    if ts_mode == "Date_Time":
        ts = now.strftime("_%Y-%m-%d_%H-%M-%S")
    elif ts_mode == "HHMMSS":
        ts = now.strftime("_%H%M%S")
    elif ts_mode == "Unix_Epoch":
        ts = f"_{int(time.time())}"

    base = f"{prefix}{ts}"
    ext  = ext.lstrip(".")

    if overwrite:
        return os.path.join(out_dir, f"{base}.{ext}")

    c = 1
    while True:
        path = os.path.join(out_dir, f"{base}_{str(c).zfill(pad)}.{ext}")
        if not os.path.exists(path):
            return path
        c += 1


def _strip_png_workflow(src_path: str) -> None:
    """Supprime les chunks tEXt/iTXt/zTXt workflow/prompt/parameters du PNG."""
    try:
        with open(src_path, "rb") as f:
            raw = f.read()
        out = bytearray(raw[:8])
        pos = 8
        while pos < len(raw):
            length     = struct.unpack(">I", raw[pos:pos+4])[0]
            chunk_type = raw[pos+4:pos+8].decode("latin-1")
            data       = raw[pos+8:pos+8+length]
            crc        = raw[pos+8+length:pos+12+length]
            pos       += 12 + length
            if chunk_type in ("tEXt", "iTXt", "zTXt"):
                null_idx = data.find(b"\x00")
                key = data[:null_idx].decode("latin-1", errors="replace") if null_idx != -1 else ""
                if key.lower() in ("workflow", "prompt", "parameters"):
                    continue
            out += struct.pack(">I", length)
            out += chunk_type.encode("latin-1")
            out += data
            out += crc
        with open(src_path, "wb") as f:
            f.write(out)
    except Exception as e:
        print(f"⚠️ [SuperSaver] strip_png_workflow : {e}")





# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class PyCodeMax_SuperSaver:

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # ── Globaux ──────────────────────────────────────────────────
                "timestamp_mode":   (["Disabled", "Date_Time", "HHMMSS", "Unix_Epoch"],
                                     {"default": "Disabled"}),
                "overwrite":        ("BOOLEAN", {"default": False,
                                     "label_on": "Overwrite", "label_off": "Increment"}),
                "counter_padding":  ("INT", {"default": 4, "min": 1, "max": 8}),
                "strip_workflow":   ("BOOLEAN", {"default": False,
                                     "label_on": "🧹 Strip Workflow ON",
                                     "label_off": "🧹 Strip Workflow OFF"}),

                # ── IMAGE ────────────────────────────────────────────────────
                "image_enable":     ("BOOLEAN", {"default": True,
                                     "label_on": "🖼️ Image ON", "label_off": "🖼️ Image OFF"}),
                "image_sub_folder": ("STRING",  {"default": "Images"}),
                "image_prefix":     ("STRING",  {"default": "img"}),
                "image_format":     (["PNG", "JPEG", "WEBP", "TIFF"], {"default": "PNG"}),
                "jpeg_quality":     ("INT",     {"default": 95, "min": 1, "max": 100}),
                "webp_quality":     ("INT",     {"default": 90, "min": 1, "max": 100}),
                "tiff_compression": (["deflate", "lzw", "none"], {"default": "deflate"}),

                # ── TEXT ─────────────────────────────────────────────────────
                "text_enable":      ("BOOLEAN", {"default": True,
                                     "label_on": "📄 Text ON", "label_off": "📄 Text OFF"}),
                "text_sub_folder":  ("STRING",  {"default": "Texts"}),
                "text_prefix":      ("STRING",  {"default": "text"}),
                "text_extension":   ("STRING",  {"default": "txt"}),
            },
            "optional": {
                # ── IMAGE ────────────────────────────────────────────────────
                "image":         ("IMAGE",),
                "caption_image": ("STRING", {"forceInput": True}),
                "alpha_1":       ("IMAGE",),   # ports dynamiques gérés par le JS

                # ── TEXT ─────────────────────────────────────────────────────
                "txt":           ("STRING", {"forceInput": True}),

                # ── COMMUN ───────────────────────────────────────────────────
                "add_metadata":  ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("image_path", "text_path")
    FUNCTION     = "save_all"
    OUTPUT_NODE  = True
    CATEGORY     = "Orion4D_MetaNode/FileIO"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def save_all(self,
                 timestamp_mode, overwrite, counter_padding, strip_workflow,
                 image_enable, image_sub_folder, image_prefix,
                 image_format, jpeg_quality, webp_quality, tiff_compression,
                 text_enable, text_sub_folder, text_prefix, text_extension,
                 image=None, caption_image=None, alpha_1=None,
                 txt=None, add_metadata=None,
                 prompt=None, extra_pnginfo=None,
                 **kwargs):

        img_path = ""
        txt_path = ""

        # Collecter les alphas dynamiques
        alpha_list = []
        if alpha_1 is not None:
            alpha_list.append(alpha_1)
        i = 2
        while True:
            val = kwargs.get(f"alpha_{i}")
            if val is None:
                break
            alpha_list.append(val)
            i += 1
            if i > 64:
                break

        # ── IMAGE ────────────────────────────────────────────────────────────
        if image_enable and image is not None:
            try:
                ext_map = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "TIFF": "tif"}
                img_ext = ext_map[image_format]
                out_dir = _make_dir(self.output_dir, image_sub_folder)

                for b_idx, img_t in enumerate(image):
                    pfx   = image_prefix if len(image) == 1 else f"{image_prefix}_{b_idx:02d}"
                    fpath = _build_path(pfx, timestamp_mode, counter_padding,
                                        img_ext, out_dir, overwrite)
                    np_img = np.clip(255.0 * img_t.cpu().numpy(), 0, 255).astype(np.uint8)
                    pil    = Image.fromarray(np_img)

                    if image_format == "PNG":
                        meta = PngInfo()
                        # Workflow ComfyUI — add_text() suffit, ComfyUI écrit déjà en ASCII/Latin-1
                        if not strip_workflow:
                            if prompt:
                                meta.add_text("prompt", json.dumps(prompt))
                            if extra_pnginfo:
                                for k, v in extra_pnginfo.items():
                                    meta.add_text(k, json.dumps(v))
                        # Métadonnées utilisateur — add_itxt() : chunk iTXt, encodage UTF-8 natif
                        # Supporte tous les caractères : accents, guillemets typographiques, emoji…
                        if txt and str(txt).strip():
                            meta.add_itxt("description", str(txt).strip(), lang="", tkey="")
                        if add_metadata and str(add_metadata).strip():
                            meta.add_itxt("metadata", str(add_metadata).strip(), lang="", tkey="")
                        pil.save(fpath, pnginfo=meta, compress_level=4)

                    elif image_format == "JPEG":
                        pil.convert("RGB").save(fpath, quality=jpeg_quality, optimize=True)

                    elif image_format == "WEBP":
                        pil.save(fpath, quality=webp_quality, method=6)

                    elif image_format == "TIFF":
                        if _TIFFFILE:
                            h, w = np_img.shape[:2]
                            channels = [np_img]
                            for a_in in alpha_list:
                                a_i = b_idx if a_in.shape[0] > b_idx else 0
                                a   = np.clip(a_in[a_i].cpu().numpy() * 255, 0, 255).astype(np.uint8)
                                if a.ndim == 3 and a.shape[-1] >= 3:
                                    a = np.dot(a[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)
                                elif a.ndim == 3:
                                    a = a.squeeze(-1)
                                if a.shape != (h, w):
                                    a = np.array(Image.fromarray(a, "L").resize((w, h), Image.BILINEAR))
                                channels.append(a[..., np.newaxis])
                            final   = np.concatenate(channels, axis=-1)
                            n_extra = final.shape[-1] - 3
                            comp    = tiff_compression if tiff_compression != "none" else None
                            kw      = {"photometric": "rgb"}
                            if comp:        kw["compression"]  = comp
                            if n_extra > 0: kw["extrasamples"] = [0] * n_extra
                            tifffile.imwrite(fpath, final, **kw)
                        else:
                            print("⚠️ [SuperSaver] tifffile non installé — fallback PIL.")
                            pil.save(fpath)

                    # Strip workflow (PNG uniquement, chunk par chunk)
                    if strip_workflow and image_format == "PNG":
                        _strip_png_workflow(fpath)

                    # caption_image → .txt même nom que l'image
                    if caption_image and str(caption_image).strip():
                        cap_path = os.path.splitext(fpath)[0] + ".txt"
                        with open(cap_path, "w", encoding="utf-8") as cf:
                            cf.write(str(caption_image).strip())

                    img_path = fpath
                    print(f"✅ [SuperSaver] Image → {fpath}")

            except Exception as e:
                import traceback
                print(f"❌ [SuperSaver] Image : {e}")
                traceback.print_exc()

        # ── TEXT ─────────────────────────────────────────────────────────────
        if text_enable and txt is not None and str(txt).strip():
            try:
                ext     = text_extension.strip().lstrip(".") or "txt"
                out_dir = _make_dir(self.output_dir, text_sub_folder)
                fpath   = _build_path(text_prefix, timestamp_mode, counter_padding,
                                      ext, out_dir, overwrite)
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(str(txt))
                txt_path = fpath
                print(f"✅ [SuperSaver] Text → {fpath}")
            except Exception as e:
                print(f"❌ [SuperSaver] Text : {e}")

        # ── Résumé ───────────────────────────────────────────────────────────
        saved   = [p for p in [img_path, txt_path] if p]
        summary = ("Saved " + " | ".join(os.path.basename(p) for p in saved)) \
                  if saved else "Nothing saved."
        print(f"📦 [SuperSaver] {summary}")

        return {
            "ui":     {"text": [summary]},
            "result": (img_path, txt_path),
        }


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS        = {"PyCodeMax_SuperSaver": PyCodeMax_SuperSaver}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_SuperSaver": "💾 Super Saver"}

# --- END OF FILE super_saver.py ---