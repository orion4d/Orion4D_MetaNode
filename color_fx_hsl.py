# --- START OF FILE color_fx_hsl.py ---
#
# Hue / Saturation / Lightness FX — équivalent Photoshop "Teinte/Saturation".
#
# Mode global (Master) ou ciblé par famille de teintes (Reds, Yellows, Greens,
# Cyans, Blues, Magentas), avec transition douce gaussienne entre familles.
# Mode Colorize aussi (monochrome teinté).
#
# Mode hybride : input/output IMAGE optionnels en plus de la sortie fx.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_HSLFX:
    """
    Ajustement Teinte / Saturation / Luminosité (TSL) façon Photoshop.

    Trois modes d'emploi :

    1. Master  → ajuste hue/sat/light sur toute l'image (équivalent Photoshop
                 "Master" ou "Édition: Toutes les couleurs").

    2. Reds, Yellows, Greens, Cyans, Blues, Magentas → cible UNE famille de
       teintes via un masque gaussien doux (centré sur le pic de la famille).
       Permet par exemple de désaturer juste les rouges sans toucher au reste,
       ou de décaler les bleus du ciel vers le cyan.

    3. Colorize → désature à 0 puis applique une teinte+saturation fixes
       (les contrôles colorize_hue / colorize_saturation). Le slider lightness
       reste actif pour la luminosité globale.

    Mode standalone : si une image est branchée sur image_in, l'effet est
    appliqué directement et ressort sur la sortie image. Mode chaîne :
    sortie fx vers un Color Pro Receiver.
    """

    @classmethod
    def INPUT_TYPES(cls):
        targets = ["Master", "Reds", "Yellows", "Greens", "Cyans", "Blues", "Magentas"]
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Hue/Sat/Light"}),
                "target":  (targets, {"default": "Master"}),
                "hue":        ("FLOAT", {"default": 0.0, "min": -180.0, "max": 180.0, "step": 1.0}),
                "saturation": ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "lightness":  ("FLOAT", {"default": 0.0, "min": -100.0, "max": 100.0, "step": 1.0}),
                "colorize":            ("BOOLEAN", {"default": False, "label_on": "Colorize ON", "label_off": "Colorize OFF"}),
                "colorize_hue":        ("FLOAT", {"default":  0.0, "min":   0.0, "max": 360.0, "step": 1.0}),
                "colorize_saturation": ("FLOAT", {"default": 25.0, "min":   0.0, "max": 100.0, "step": 1.0}),
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
        target,
        hue,
        saturation,
        lightness,
        colorize,
        colorize_hue,
        colorize_saturation,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="hsl",
            enabled=enabled,
            label=label,
            params={
                "target":              target,
                "hue":                 hue,
                "saturation":          saturation,
                "lightness":           lightness,
                "colorize":            colorize,
                "colorize_hue":        colorize_hue,
                "colorize_saturation": colorize_saturation,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_HSLFX": PyCodeMax_HSLFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_HSLFX": "🎨 Hue/Sat/Light FX"}

# --- END OF FILE color_fx_hsl.py ---
