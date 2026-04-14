# --- START OF FILE image_comparer_v2.py ---
#
# Image Comparer V2 (beta) — Orion4D_MetaNode
#
# Version optimisée pour Nodes 2.0 de ComfyUI.
#
# Fonctionnalités :
#   - Mode slide : curseur vertical révèle B sur A (défaut)
#   - Mode click : un clic toggle entre A et B
#   - Bouton Swap A/B : inverse l'affichage sans rebrancher
#   - Accepte les tailles différentes (alignement auto)
#
# Approche technique :
#   - Pas de clé "ui.images" standard : on évite le rendu natif de
#     thumbnails de Nodes 2.0 qui viendrait se superposer.
#   - On utilise une clé custom "compare_images" que notre JS lit.
#   - Tout le rendu se fait via un DOM widget (canvas HTML) au-dessus
#     du node, avec compensation zoom/dpr pour rester net à tout niveau.

import os
import random
import folder_paths
import numpy as np
import torch
from PIL import Image


def _tensor_to_pil(t: torch.Tensor) -> Image.Image:
    """(H, W, C) ou (1, H, W, C) → PIL Image RGB."""
    if t.ndim == 4:
        t = t[0]
    arr = (t.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L").convert("RGB")
    if arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA").convert("RGB")
    return Image.fromarray(arr, mode="RGB")


def _align_sizes(pil_a: Image.Image, pil_b: Image.Image) -> tuple[Image.Image, Image.Image]:
    """Aligne A et B sur la plus grande des deux dimensions, mode 'fit'."""
    if pil_a.size == pil_b.size:
        return pil_a, pil_b

    target_w = max(pil_a.width, pil_b.width)
    target_h = max(pil_a.height, pil_b.height)

    def _fit(img: Image.Image) -> Image.Image:
        if img.size == (target_w, target_h):
            return img
        ratio = min(target_w / img.width, target_h / img.height)
        new_w = max(1, int(round(img.width * ratio)))
        new_h = max(1, int(round(img.height * ratio)))
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        offset = ((target_w - new_w) // 2, (target_h - new_h) // 2)
        canvas.paste(resized, offset)
        return canvas

    return _fit(pil_a), _fit(pil_b)


class Orion4D_ImageComparerV2:
    """
    Comparateur d'images V2 (beta). Node terminal — pas de sorties.

    Optimisé pour ComfyUI Nodes 2.0 : pas de clé "ui.images" standard pour
    éviter la superposition du rendu natif. On passe les URLs sous la clé
    custom "compare_images" que notre JS consomme directement.
    """

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_orion4d_compare_v2_" + "".join(
            random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(8)
        )
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "compare"
    OUTPUT_NODE = True
    CATEGORY = "Orion4D_MetaNode/Preview"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def compare(self, image_a, image_b, prompt=None, extra_pnginfo=None):
        pil_a = _tensor_to_pil(image_a[0])
        pil_b = _tensor_to_pil(image_b[0])

        orig_size_a = (pil_a.width, pil_a.height)
        orig_size_b = (pil_b.width, pil_b.height)

        pil_a_disp, pil_b_disp = _align_sizes(pil_a, pil_b)

        full_output_folder, filename, counter, subfolder, _ = \
            folder_paths.get_save_image_path(
                "compare_v2" + self.prefix_append, self.output_dir
            )

        results = []
        for label, pil_img, orig in (
            ("a", pil_a_disp, orig_size_a),
            ("b", pil_b_disp, orig_size_b),
        ):
            file = f"{filename}_{label}_{counter:05d}.png"
            filepath = os.path.join(full_output_folder, file)
            pil_img.save(filepath, compress_level=self.compress_level)
            results.append({
                "filename": file,
                "subfolder": subfolder,
                "type": "temp",
                "label": label,
                "orig_w": orig[0],
                "orig_h": orig[1],
                "disp_w": pil_img.width,
                "disp_h": pil_img.height,
            })

        # Clé CUSTOM uniquement (pas "images") : le JS lit directement
        # compare_images. Le DOM widget prend en charge l'affichage,
        # pas besoin de déclencher le pipeline natif de Nodes 2.0.
        return {
            "ui": {"compare_images": results},
        }


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"Orion4D_ImageComparerV2": Orion4D_ImageComparerV2}
NODE_DISPLAY_NAME_MAPPINGS = {"Orion4D_ImageComparerV2": "🔍 Image Comparer V2 (beta)"}

# --- END OF FILE image_comparer_v2.py ---
