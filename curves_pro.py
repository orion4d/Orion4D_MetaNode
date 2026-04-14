# --- START OF FILE curves_pro.py ---
# Curves Pro - Orion4d-coder pack  v6 (uniformisé avec Color Pro FX)
#
# Deux nœuds :
#
#   PyCodeMax_CurvesPro      → Éditeur de courbes + émetteur FX.
#                              Nouveau : mode hybride comme les autres FX.
#                              Inputs:  image_in (optionnel)
#                              Outputs: fx (COLOR_FX), image (IMAGE), curves_json (STRING)
#                              Preset via le système unifié fx_setup/curves/
#
#   PyCodeMax_CurvesProImage → Chargeur d'image style Load Image avec onglets
#                              [Original / Modifié], reçoit curves_json et
#                              renvoie l'image traitée.
#                              Inputs:  image (widget upload), curves_json (opt), mask (opt)
#                              Outputs: image, mask, log

import os
import json
import hashlib
import base64
from io import BytesIO

import torch
import numpy as np
from PIL import Image, ImageOps
from aiohttp import web
import folder_paths               # type: ignore
from server import PromptServer   # type: ignore

# Helpers partagés avec le reste du pack Color Pro
from .color_fx_common import (
    COLOR_FX_TYPE,
    build_fx_output,
    apply_single_fx_inline,
    LINEAR,
    DEFAULT_CURVES,
    process_image_pil,
    calc_histogram_pil,
)

DEFAULT_CURVES_STR = json.dumps(DEFAULT_CURVES)


def _pil_to_tensor(pil_rgb):
    """PIL RGB → tensor (1, H, W, 3) float32 [0..1]."""
    return torch.from_numpy(np.array(pil_rgb).astype(np.float32) / 255.0)[None, ]


def _tensor_to_pil(image: torch.Tensor) -> Image.Image:
    """Tensor (B,H,W,C) ou (H,W,C) → PIL RGB (premier du batch)."""
    if image.ndim == 4:
        image = image[0]
    arr = (image.cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    if arr.ndim == 2:
        return Image.fromarray(arr, mode="L").convert("RGB")
    if arr.shape[2] == 4:
        return Image.fromarray(arr, mode="RGBA").convert("RGB")
    return Image.fromarray(arr, mode="RGB")


# ============================================================================
#  NŒUD 1 : PyCodeMax_CurvesPro  (éditeur de courbes + émetteur FX)
# ============================================================================
class PyCodeMax_CurvesPro:
    """
    Éditeur de courbes façon Photoshop avec canvas interactif.

    Trois modes d'emploi :
      1. Standalone  : brancher une image sur image_in → l'image traitée
                       ressort sur la sortie image.
      2. Chaîne      : la sortie fx (COLOR_FX) se branche sur un slot fx_N
                       d'un Color Pro Receiver.
      3. Legacy      : la sortie curves_json (STRING) se branche sur un
                       Curves Pro Image pour visualiser sur une image
                       chargée en drag-drop.

    Presets : système unifié fx_setup/curves/, gérés via les widgets
    preset/Save/Delete/Refresh/Reset ajoutés automatiquement par
    color_fx_presets.js.
    """

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Toujours recalculer : le canvas peut avoir modifié all_curves_json
        return float("NaN")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Curves"}),
                "channel": (["RGB", "Red", "Green", "Blue"], {"default": "RGB"}),
                "all_curves_json": ("STRING", {
                    "default":   DEFAULT_CURVES_STR,
                    "multiline": True,
                }),
            },
            "optional": {
                "image_in": ("IMAGE",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES  = (COLOR_FX_TYPE, "IMAGE", "STRING",)
    RETURN_NAMES  = ("fx", "image", "curves_json",)
    FUNCTION      = "execute"
    CATEGORY      = "Orion4D_MetaNode/ColorGrading"

    def execute(
        self,
        enabled,
        label,
        channel,
        all_curves_json,
        image_in=None,
        unique_id=None,
    ):
        # Parsing defensive des courbes
        try:
            curves = json.loads(all_curves_json)
            if not isinstance(curves, dict):
                curves = DEFAULT_CURVES
        except Exception:
            curves = DEFAULT_CURVES

        curves_json_clean = json.dumps(curves)

        # Construction du dict FX (format COLOR_FX standard)
        fx = build_fx_output(
            fx_type="curves",
            enabled=enabled,
            label=label,
            params={
                "all_curves_json": curves_json_clean,
            },
        )

        # Mode hybride : si une image est branchée, on applique les courbes
        # directement via le pipeline FX central.
        image_out = apply_single_fx_inline(image_in, fx)

        # Envoi WebSocket pour le preview live côté canvas.
        # En mode standalone, l'image_in fournie sert de source pour que le
        # canvas puisse faire ses previews /apply sans dépendre de
        # Curves Pro Image en aval.
        if image_in is not None and unique_id:
            try:
                pil_src = _tensor_to_pil(image_in)
                pil_src.thumbnail((768, 768), Image.LANCZOS)
                buf = BytesIO()
                pil_src.save(buf, format="PNG")
                PromptServer.instance.send_sync(
                    "orion4d.curves_pro_preview",
                    {"node_id": unique_id, "image_data": base64.b64encode(buf.getvalue()).decode()},
                )
            except Exception as e:
                print(f"[CurvesPro] preview WS error: {e}")

        return (fx, image_out, curves_json_clean)


# ============================================================================
#  NŒUD 2 : PyCodeMax_CurvesProImage  (load image + courbes → résultat)
# ============================================================================
def _image_list():
    try:
        d = folder_paths.get_input_directory()
        files = [f for f in os.listdir(d)
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"))]
        return sorted(files) or ["(aucune image)"]
    except Exception:
        return ["(aucune image)"]


class PyCodeMax_CurvesProImage:
    """
    Load Image avec application de courbes. UI en 2 onglets
    (Original / Modifié) gérée côté JS.

    L'image source est toujours envoyée au canvas Curves Pro source (s'il
    est branché) via WebSocket pour permettre les previews live.
    """

    @classmethod
    def IS_CHANGED(cls, image, curves_json="", **kwargs):
        h = hashlib.md5()
        try:
            path = os.path.join(folder_paths.get_input_directory(), image)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    h.update(f.read())
        except Exception:
            pass
        h.update((curves_json or "").encode())
        return h.hexdigest()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": (_image_list(), {"image_upload": True}),
            },
            "optional": {
                "curves_json": ("STRING",  {"forceInput": True}),
                "mask":        ("MASK",),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES  = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES  = ("image", "mask", "log")
    FUNCTION      = "execute"
    CATEGORY      = "Orion4D_MetaNode/ColorGrading"

    def execute(self, image, curves_json=None, mask=None, unique_id=None):
        img_path = os.path.join(folder_paths.get_input_directory(), image)
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"[CurvesProImage] Image introuvable : {img_path}")

        pil_src = ImageOps.exif_transpose(Image.open(img_path)).convert("RGB")

        # Parsing courbes
        curves = DEFAULT_CURVES
        if curves_json:
            try:
                parsed = json.loads(curves_json)
                if isinstance(parsed, dict):
                    curves = parsed
            except Exception as e:
                print(f"[CurvesProImage] curves_json parse error: {e}")

        # Application
        pil_result = process_image_pil(pil_src, curves)
        img_tensor = _pil_to_tensor(pil_result)

        # Mask passthrough
        mask_out = mask if mask is not None else torch.zeros((1, pil_src.height, pil_src.width))

        # Log JSON
        w, h = pil_src.size
        curves_serializable = {}
        for k, pts in curves.items():
            if pts and isinstance(pts[0], dict):
                curves_serializable[k] = [[p["x"], p["y"]] for p in pts]
            else:
                curves_serializable[k] = [list(p) for p in pts]
        log_data = {
            "node":   "CurvesProImage",
            "image":  image,
            "size":   {"w": w, "h": h},
            "curves": curves_serializable,
        }
        log = json.dumps(log_data, ensure_ascii=False)

        # Preview WebSocket vers le node CurvesPro source (pour canvas live)
        if unique_id:
            try:
                preview = pil_src.copy()
                preview.thumbnail((768, 768), Image.LANCZOS)
                buf = BytesIO()
                preview.save(buf, format="PNG")
                PromptServer.instance.send_sync(
                    "orion4d.curves_pro_preview",
                    {"node_id": unique_id, "image_data": base64.b64encode(buf.getvalue()).decode()},
                )
            except Exception as e:
                print(f"[CurvesProImage] preview WS error: {e}")

        return (img_tensor, mask_out, log)


# ============================================================================
#  ROUTES API — histogramme et apply live (toujours utilisées par le canvas)
# ============================================================================
# Les routes de preset ont été retirées : elles sont maintenant gérées par
# /orion4d/fx_presets/* dans color_fx_presets.py. Le canvas Curves Pro
# utilise le système unifié.

def _decode_b64_image_safe(b64_str: str, max_bytes: int = 20 * 1024 * 1024,
                           max_pixels: int = 50_000_000) -> Image.Image:
    """Décode un base64 en PIL Image avec garde-fous taille/pixels."""
    if not isinstance(b64_str, str):
        raise ValueError("base64 absent")
    # Nettoyage des éventuels préfixes data:image/...;base64,
    if b64_str.startswith("data:"):
        _, _, b64_str = b64_str.partition(",")
    if len(b64_str) > max_bytes * 4 // 3 + 16:  # marge pour le padding
        raise ValueError("image trop lourde")
    try:
        raw = base64.b64decode(b64_str, validate=False)
    except Exception as e:
        raise ValueError(f"base64 invalide: {e}")
    if len(raw) > max_bytes:
        raise ValueError("image trop lourde")
    img = Image.open(BytesIO(raw))
    if img.width * img.height > max_pixels:
        raise ValueError(f"image trop grande ({img.width}x{img.height})")
    return img.convert("RGB")


@PromptServer.instance.routes.post("/orion4d/curves_pro/get_histogram")
async def _get_histogram(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    b64 = data.get("base_data_b64")
    ch  = data.get("channel_mode", "RGB")
    if not b64:
        return web.json_response({"error": "Données manquantes."}, status=400)
    try:
        img = _decode_b64_image_safe(b64)
        hist = calc_histogram_pil(img, ch)
        return web.json_response({"histogram": hist})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


@PromptServer.instance.routes.post("/orion4d/curves_pro/apply")
async def _apply(request):
    """Applique des courbes à une image base64 pour le preview live côté canvas."""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    b64 = data.get("base_data_b64")
    cj  = data.get("all_curves_json")
    if not b64 or not cj:
        return web.json_response({"error": "Données manquantes."}, status=400)
    try:
        img    = _decode_b64_image_safe(b64)
        curves = json.loads(cj)
        result = process_image_pil(img, curves)
        buf = BytesIO()
        result.save(buf, format="PNG")
        return web.json_response({"adjusted_image_data": base64.b64encode(buf.getvalue()).decode()})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=400)


# ============================================================================
#  ENREGISTREMENT
# ============================================================================
NODE_CLASS_MAPPINGS = {
    "PyCodeMax_CurvesPro":      PyCodeMax_CurvesPro,
    "PyCodeMax_CurvesProImage": PyCodeMax_CurvesProImage,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_CurvesPro":      "📈 Curves Pro",
    "PyCodeMax_CurvesProImage": "🖼️ Curves Pro Image",
}

# --- END OF FILE curves_pro.py ---
