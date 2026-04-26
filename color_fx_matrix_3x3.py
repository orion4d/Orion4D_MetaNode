# color_fx_matrix_3x3.py
#
# Matrix 3x3 FX — transformation RGB par matrice complète.
#
# Les looks prédéfinis sont volontairement gérés par le système de presets JSON
# unifié : fx_setup/matrix_3x3/*.json
# Il n’y a donc pas de second menu de presets dans ce node.
#
# Mode hybride :
#   - sortie fx pour Color Pro Receiver
#   - sortie image si image_in est branchée

from .color_fx_common import COLOR_FX_TYPE, build_fx_output, apply_single_fx_inline


class PyCodeMax_Matrix3x3FX:
    """
    Matrix 3x3 FX.

    Applique une matrice RGB complète :

        R' = R*m00 + G*m01 + B*m02 + offset_r
        G' = R*m10 + G*m11 + B*m12 + offset_g
        B' = R*m20 + G*m21 + B*m22 + offset_b

    Les presets créatifs sont des fichiers JSON chargés via le système
    unifié du pack Color FX.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "enabled": ("BOOLEAN", {"default": True, "label_on": "ON", "label_off": "OFF"}),
                "label": ("STRING", {"default": "Matrix 3x3"}),

                "m00": ("FLOAT", {"default": 1.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m01": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m02": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),

                "m10": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m11": ("FLOAT", {"default": 1.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m12": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),

                "m20": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m21": ("FLOAT", {"default": 0.0, "min": -3.0, "max": 3.0, "step": 0.001}),
                "m22": ("FLOAT", {"default": 1.0, "min": -3.0, "max": 3.0, "step": 0.001}),

                "offset_r": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "offset_g": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),
                "offset_b": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.001}),

                "strength": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.01}),
                "preserve_luminosity": ("BOOLEAN", {"default": False}),
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
        m00, m01, m02,
        m10, m11, m12,
        m20, m21, m22,
        offset_r, offset_g, offset_b,
        strength,
        preserve_luminosity,
        clamp_output,
        image_in=None,
    ):
        fx = build_fx_output(
            fx_type="matrix_3x3",
            enabled=enabled,
            label=label,
            params={
                "m00": m00, "m01": m01, "m02": m02,
                "m10": m10, "m11": m11, "m12": m12,
                "m20": m20, "m21": m21, "m22": m22,

                "offset_r": offset_r,
                "offset_g": offset_g,
                "offset_b": offset_b,

                "strength": strength,
                "preserve_luminosity": preserve_luminosity,
                "clamp_output": clamp_output,
            },
        )

        image_out = apply_single_fx_inline(image_in, fx)
        return (fx, image_out)


NODE_CLASS_MAPPINGS = {
    "PyCodeMax_Matrix3x3FX": PyCodeMax_Matrix3x3FX,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_Matrix3x3FX": "🎨 Matrix 3x3 FX",
}
