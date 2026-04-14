# --- START OF FILE color_fx_color_balance.py ---
#
# Color Balance FX — équivalent Photoshop "Balance des couleurs".
#
# Un seul mode actif par node (shadows / midtones / highlights). Pour
# balancer les 3 zones en cascade, chaîner 3 nodes dans le Color Pro
# Receiver. Mode hybride comme les autres FX.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_ColorBalanceFX:
    """
    Balance des couleurs façon Photoshop.

    Affecte une seule zone tonale par node : shadows, midtones ou highlights.
    Trois sliders couplés inversément :
      - cyan_red      (-100 = cyan, +100 = rouge)
      - magenta_green (-100 = magenta, +100 = vert)
      - yellow_blue   (-100 = jaune, +100 = bleu)

    Pour corriger les 3 zones d'une image, empiler 3 nodes Color Balance
    dans le Receiver.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Color Balance"}),
                "adjust_type": (["shadows", "midtones", "highlights"], {"default": "midtones"}),
                "cyan_red":      ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "magenta_green": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "yellow_blue":   ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "preserve_luminosity": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "image_in": ("IMAGE",),
            },
        }

    RETURN_TYPES = (COLOR_FX_TYPE, "IMAGE",)
    RETURN_NAMES = ("fx", "image",)
    FUNCTION = "emit"
    CATEGORY = "Orion4D_MetaNode/ColorGrading"

    def emit(
        self,
        enabled,
        label,
        adjust_type,
        cyan_red,
        magenta_green,
        yellow_blue,
        preserve_luminosity,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="color_balance",
            enabled=enabled,
            label=label,
            params={
                "adjust_type":         adjust_type,
                "cyan_red":            cyan_red,
                "magenta_green":       magenta_green,
                "yellow_blue":         yellow_blue,
                "preserve_luminosity": preserve_luminosity,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_ColorBalanceFX": PyCodeMax_ColorBalanceFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ColorBalanceFX": "🎨 Color Balance FX"}

# --- END OF FILE color_fx_color_balance.py ---
