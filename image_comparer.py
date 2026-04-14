# --- START OF FILE image_comparer.py ---
#
# Image Comparer — Orion4D_MetaNode (version Legacy / LiteGraph)
#
# Comparateur d'images interactif, optimisé pour le pipeline LiteGraph
# classique de ComfyUI. Affiche A ou B via toggle sur l'image ou sur des
# ronds indicateurs, dessiné directement dans le canvas LiteGraph.
#
#   - Reste net à tout niveau de zoom (dessin canvas natif, pas de bitmap)
#   - Accepte les tailles différentes (alignement auto sur la plus grande
#     dimension, idéal pour vérifier un upscale)
#   - Node terminal : pas de sorties. On le branche en bout de workflow.
#
# Compatibilité Nodes 2.0 (beta) : fonctionne mais le rendu natif de
# Nodes 2.0 peut se superposer à notre dessin. Pour une expérience
# parfaite en Nodes 2.0, utiliser le node "Image Comparer V2 (beta)".

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


class Orion4D_ImageComparer:
    """
    Comparateur d'images (version Legacy). Node terminal — pas de sorties.

    L'aperçu se gère côté JS via onDrawForeground. On sauvegarde A et B dans
    temp/ et on transmet les URLs via la clé standard `ui.images` pour que
    Nodes 2.0 continue à appeler nos callbacks de rendu, plus notre clé
    custom `compare_images` qui contient les métadonnées enrichies (label,
    dimensions d'origine).
    """

    def __init__(self):
        self.output_dir = folder_paths.get_temp_directory()
        self.type = "temp"
        self.prefix_append = "_orion4d_compare_" + "".join(
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
        # Toujours réévaluer pour rafraîchir l'aperçu
        return float("nan")

    def compare(self, image_a, image_b, prompt=None, extra_pnginfo=None):
        # Toujours prendre le premier de chaque batch (pas de widget index
        # pour garder l'UI minimale et cohérente avec Nodes 2.0)
        pil_a = _tensor_to_pil(image_a[0])
        pil_b = _tensor_to_pil(image_b[0])

        orig_size_a = (pil_a.width, pil_a.height)
        orig_size_b = (pil_b.width, pil_b.height)

        pil_a_disp, pil_b_disp = _align_sizes(pil_a, pil_b)

        full_output_folder, filename, counter, subfolder, _ = \
            folder_paths.get_save_image_path(
                "compare" + self.prefix_append, self.output_dir
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

        return {
            # "images" : clé standard ComfyUI, nécessaire pour que Nodes 2.0
            # continue d'appeler onDrawForeground (sinon il court-circuite
            # complètement le rendu custom du node).
            # "compare_images" : métadonnées enrichies pour notre JS.
            "ui": {"images": results, "compare_images": results},
        }


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"Orion4D_ImageComparer": Orion4D_ImageComparer}
NODE_DISPLAY_NAME_MAPPINGS = {"Orion4D_ImageComparer": "🔍 Image Comparer"}

# --- END OF FILE image_comparer.py ---
