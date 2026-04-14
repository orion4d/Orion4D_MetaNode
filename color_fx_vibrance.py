# --- START OF FILE color_fx_vibrance.py ---
#
# Vibrance FX — saturation sélective avec protection des tons chair.
#
# Boost prioritairement les couleurs peu saturées (évite d'écrêter les
# couleurs déjà vives) et protège les teintes chair (0-30° et 330-360°)
# pour ne pas surchauffer les portraits.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_VibranceFX:
    """
    Vibrance et saturation façon Lightroom/Photoshop.

    Deux sliders :
      - vibrance   : ajustement sélectif qui booste en priorité les couleurs
                     peu saturées, laisse tranquille les couleurs déjà vives.
                     Idéal pour du punch sans écrêtage.
      - saturation : ajustement global, multiplicateur uniforme.

    Options :
      - protect_skin_tones : réduit l'effet sur les teintes 0-30° et 330-360°,
                             préserve les peaux dans les portraits.
      - strength           : intensité globale des deux ajustements (0.0 à 2.0)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Vibrance"}),
                "vibrance":   ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "saturation": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "protect_skin_tones": ("BOOLEAN", {"default": True}),
                "strength":   ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
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
        vibrance,
        saturation,
        protect_skin_tones,
        strength,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="vibrance",
            enabled=enabled,
            label=label,
            params={
                "vibrance":           vibrance,
                "saturation":         saturation,
                "protect_skin_tones": protect_skin_tones,
                "strength":           strength,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_VibranceFX": PyCodeMax_VibranceFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_VibranceFX": "🎨 Vibrance FX"}

# --- END OF FILE color_fx_vibrance.py ---
