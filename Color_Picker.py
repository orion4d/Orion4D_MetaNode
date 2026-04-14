# --- START OF FILE Color_Picker.py ---
#
# Color Picker v2
#
# Nouveautés :
#   - Widgets width / height (par défaut 64×64) pour générer une image
#     uniforme de la couleur sélectionnée.
#   - Sortie IMAGE (tensor) — un rectangle uni width×height en RGB.
#   - Aperçu visuel de la couleur dans le node (géré côté JS).
#
# La sortie image est toujours produite, même si rien n'est connecté en aval :
# ComfyUI ignore simplement les sorties non utilisées, donc pas de risque
# de plantage.

import torch
import numpy as np


class PyCodeMax_ColorPicker:
    """
    Sélecteur de couleur visuel.
    Renvoie l'Hexa, le format 'R, G, B', les canaux séparés, et une image
    uniforme de la couleur (taille paramétrable).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "color_hex": ("STRING", {"default": "#F54927"}),
                "width":     ("INT", {"default": 64, "min": 1, "max": 8192, "step": 1}),
                "height":    ("INT", {"default": 64, "min": 1, "max": 8192, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "INT", "IMAGE",)
    RETURN_NAMES = ("hex_value", "rgb_string", "r", "g", "b", "image",)
    FUNCTION = "get_color"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    def get_color(self, color_hex, width, height):
        # 1. Nettoyage et formatage de l'hex
        color_hex = (color_hex or "").strip().upper()
        if not color_hex.startswith("#"):
            color_hex = "#" + color_hex

        # 2. Conversion Hex vers RGB avec fallback safe
        try:
            hex_clean = color_hex.lstrip("#")
            # Tolérance : on accepte aussi le format court #RGB → #RRGGBB
            if len(hex_clean) == 3:
                hex_clean = "".join(c * 2 for c in hex_clean)
            if len(hex_clean) != 6:
                raise ValueError(f"longueur invalide: {len(hex_clean)}")
            r, g, b = tuple(int(hex_clean[i:i + 2], 16) for i in (0, 2, 4))
            color_hex = f"#{hex_clean}"
        except Exception:
            r, g, b = 255, 255, 255
            color_hex = "#FFFFFF"

        rgb_string = f"{r}, {g}, {b}"

        # 3. Génération du tensor image (1, H, W, 3) en float32 [0..1]
        # Format attendu par ComfyUI : batch en première dimension
        w = max(1, int(width))
        h = max(1, int(height))
        rgb_norm = np.array([r, g, b], dtype=np.float32) / 255.0
        # Broadcasting : on crée un (h, w, 3) rempli avec rgb_norm
        img_np = np.tile(rgb_norm, (h, w, 1))
        image_tensor = torch.from_numpy(img_np).unsqueeze(0)  # (1, h, w, 3)

        return (color_hex, rgb_string, r, g, b, image_tensor,)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_ColorPicker": PyCodeMax_ColorPicker}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ColorPicker": "🎨 Color Picker"}

# --- END OF FILE Color_Picker.py ---
