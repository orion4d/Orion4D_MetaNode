# --- START OF FILE color_fx_channel_mixer.py ---
#
# Channel Mixer FX — node émetteur de la chaîne Color Pro.
#
# Ce node ne reçoit pas d'image. Il produit un dict COLOR_FX qui contient
# la configuration Channel Mixer et sera consommé par un ColorProReceiver
# branché en aval.

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_ChannelMixerFX:
    """
    Émetteur Channel Mixer pour la chaîne Color Pro.

    Mixe les canaux R/G/B pour reconstruire un canal de sortie, avec option
    monochrome et préservation de luminosité. Équivalent du Channel Mixer
    de Photoshop.

    Mode standalone : si une image est branchée sur image_in, l'effet est
    appliqué directement et ressort sur la sortie image. Ça permet d'utiliser
    le node sans Color Pro Receiver pour des effets isolés.

    Mode chaîne : la sortie fx (COLOR_FX) se branche sur un slot fx_N d'un
    Color Pro Receiver pour empiler plusieurs effets. Les deux modes peuvent
    être utilisés simultanément.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label":   ("STRING",  {"default": "Channel Mixer"}),
                "output_channel": (["Red", "Green", "Blue"], {"default": "Red"}),
                "red_source":   ("FLOAT", {"default": 100.0, "min": -200.0, "max": 200.0, "step": 1.0}),
                "green_source": ("FLOAT", {"default":   0.0, "min": -200.0, "max": 200.0, "step": 1.0}),
                "blue_source":  ("FLOAT", {"default":   0.0, "min": -200.0, "max": 200.0, "step": 1.0}),
                "constant":     ("FLOAT", {"default":   0.0, "min": -200.0, "max": 200.0, "step": 1.0}),
                "monochrome":          ("BOOLEAN", {"default": False}),
                "preserve_luminosity": ("BOOLEAN", {"default": False}),
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
        output_channel,
        red_source,
        green_source,
        blue_source,
        constant,
        monochrome,
        preserve_luminosity,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="channel_mixer",
            enabled=enabled,
            label=label,
            params={
                "output_channel":      output_channel,
                "red_source":          red_source,
                "green_source":        green_source,
                "blue_source":         blue_source,
                "constant":            constant,
                "monochrome":          monochrome,
                "preserve_luminosity": preserve_luminosity,
            },
        )
        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_ChannelMixerFX": PyCodeMax_ChannelMixerFX}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ChannelMixerFX": "🎨 Channel Mixer FX"}

# --- END OF FILE color_fx_channel_mixer.py ---
