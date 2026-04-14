# --- START OF FILE color_fx_css_filters.py ---
#
# CSS Filters FX — node émetteur de la chaîne Color Pro.
#
# Reproduit les filtres CSS standard du navigateur (filter: blur(),
# brightness(), contrast(), grayscale(), sepia(), hue-rotate(), saturate(),
# invert()) dans un seul FX modulaire.
#
# Pas d'input image — émet uniquement un dict COLOR_FX consommé en aval
# par un Color Pro Receiver.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_CSSFiltersFX:
    """
    Émetteur CSS Filters pour la chaîne Color Pro.

    Combine 8 filtres équivalents aux filtres CSS standard. Les valeurs par
    défaut sont les neutres CSS : 100% pour brightness/contrast/saturate
    (= identité) et 0 pour les autres (= pas d'effet). Donc un FX fraîchement
    créé sans aucun ajustement passe l'image telle quelle.

    Mode standalone : si une image est branchée sur image_in, l'effet est
    appliqué directement et ressort sur la sortie image. Mode chaîne :
    sortie fx vers un Color Pro Receiver.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "CSS Filters"}),
                # Filtres simples (PIL-friendly)
                "blur":       ("FLOAT", {"default":   0.0, "min":    0.0, "max":   20.0, "step": 0.1}),
                "brightness": ("FLOAT", {"default": 100.0, "min":    0.0, "max":  300.0, "step": 1.0}),
                "contrast":   ("FLOAT", {"default": 100.0, "min":    0.0, "max":  300.0, "step": 1.0}),
                "saturate":   ("FLOAT", {"default": 100.0, "min":    0.0, "max":  300.0, "step": 1.0}),
                # Filtres matriciels
                "grayscale":  ("FLOAT", {"default":   0.0, "min":    0.0, "max":  100.0, "step": 1.0}),
                "sepia":      ("FLOAT", {"default":   0.0, "min":    0.0, "max":  100.0, "step": 1.0}),
                "hue_rotate": ("FLOAT", {"default":   0.0, "min": -180.0, "max":  180.0, "step": 1.0}),
                "invert":     ("FLOAT", {"default":   0.0, "min":    0.0, "max":  100.0, "step": 1.0}),
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
        blur,
        brightness,
        contrast,
        saturate,
        grayscale,
        sepia,
        hue_rotate,
        invert,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="css_filters",
            enabled=enabled,
            label=label,
            params={
                "blur":       blur,
                "brightness": brightness,
                "contrast":   contrast,
                "saturate":   saturate,
                "grayscale":  grayscale,
                "sepia":      sepia,
                "hue_rotate": hue_rotate,
                "invert":     invert,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_CSSFiltersFX": PyCodeMax_CSSFiltersFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_CSSFiltersFX": "🎨 CSS Filters FX"}

# --- END OF FILE color_fx_css_filters.py ---
