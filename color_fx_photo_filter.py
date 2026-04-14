# --- START OF FILE color_fx_photo_filter.py ---
#
# Photo Filter FX — équivalent Photoshop "Filtre photo".
#
# Applique une teinte colorée uniforme par-dessus l'image avec contrôle
# de densité et préservation optionnelle de la luminosité.
#
# UI custom côté JS : un swatch couleur cliquable qui ouvre le color picker
# système, même pattern que le Color Picker node du pack.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_PhotoFilterFX:
    """
    Filtre photo façon Photoshop.

    Teinte l'image uniformément avec la couleur choisie. La densité contrôle
    l'intensité de l'effet (Photoshop utilise 25% par défaut). Le toggle
    "preserve_luminosity" maintient la luminance perceptuelle d'origine.

    UI côté JS : un aperçu de la couleur courante s'affiche dans le node
    et est cliquable pour ouvrir le color picker système.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Photo Filter"}),
                "color_hex": ("STRING", {"default": "#EC8A3C"}),  # Warming (85) Photoshop
                "density":   ("FLOAT",  {"default": 25.0, "min": 0.0, "max": 100.0, "step": 1.0}),
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
        color_hex,
        density,
        preserve_luminosity,
        image_in=None,
    ):
        # Normalisation de l'hex : on force majuscules et préfixe #
        ch = (color_hex or "").strip().upper()
        if not ch.startswith("#"):
            ch = "#" + ch

        fx = build_fx_output(
            fx_type="photo_filter",
            enabled=enabled,
            label=label,
            params={
                "color_hex":           ch,
                "density":             density,
                "preserve_luminosity": preserve_luminosity,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_PhotoFilterFX": PyCodeMax_PhotoFilterFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_PhotoFilterFX": "🎨 Photo Filter FX"}

# --- END OF FILE color_fx_photo_filter.py ---
