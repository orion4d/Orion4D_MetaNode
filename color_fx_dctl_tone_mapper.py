# color_fx_dctl_tone_mapper.py
#
# DCTL Tone Mapper FX — tone mapping filmique inspiré DCTL.
#
# Mode hybride :
#   - sortie fx pour Color Pro Receiver
#   - sortie image si image_in est branchée

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_DCTLToneMapperFX:
    """
    DCTL Tone Mapper FX.

    Tone mapper créatif/technique inspiré des DCTLs Resolve.

    Modes :
      - Filmic Soft : rendu doux, polyvalent
      - Filmic Strong : compression plus marquée
      - ACES Approx : approximation look ACES fitted
      - Reinhard : compression simple et propre
      - Cineon-ish : courbe plus dense, contrastée
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label": ("STRING", {"default": "DCTL Tone Mapper"}),

                "mode": ([
                    "Filmic Soft",
                    "Filmic Strong",
                    "ACES Approx",
                    "Reinhard",
                    "Cineon-ish",
                ], {"default": "Filmic Soft"}),

                "exposure": ("FLOAT", {"default": 0.0, "min": -5.0, "max": 5.0, "step": 0.01}),
                "contrast": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.01}),
                "pivot": ("FLOAT", {"default": 0.18, "min": 0.01, "max": 1.0, "step": 0.001}),

                "highlight_rolloff": ("FLOAT", {"default": 0.65, "min": 0.0, "max": 2.0, "step": 0.01}),
                "shadow_lift": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "black_floor": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 0.25, "step": 0.001}),

                "saturation": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 3.0, "step": 0.01}),
                "preserve_luminosity": ("BOOLEAN", {"default": False}),

                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "clamp_output": ("BOOLEAN", {"default": True}),
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
        mode,
        exposure,
        contrast,
        pivot,
        highlight_rolloff,
        shadow_lift,
        black_floor,
        saturation,
        preserve_luminosity,
        strength,
        clamp_output,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="dctl_tone_mapper",
            enabled=enabled,
            label=label,
            params={
                "mode": mode,
                "exposure": exposure,
                "contrast": contrast,
                "pivot": pivot,
                "highlight_rolloff": highlight_rolloff,
                "shadow_lift": shadow_lift,
                "black_floor": black_floor,
                "saturation": saturation,
                "preserve_luminosity": preserve_luminosity,
                "strength": strength,
                "clamp_output": clamp_output,
            },
        )

        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


NODE_CLASS_MAPPINGS = {
    "PyCodeMax_DCTLToneMapperFX": PyCodeMax_DCTLToneMapperFX,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_DCTLToneMapperFX": "🎨 DCTL Tone Mapper FX",
}
