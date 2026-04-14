# --- START OF FILE color_pro_receiver.py ---
#
# Color Pro Receiver — node récepteur de la chaîne Color Pro.
#
# Reçoit une IMAGE + des slots dynamiques fx_1, fx_2, ... de type COLOR_FX,
# et applique les effets dans l'ordre numérique des slots.
#
# Les slots dynamiques sont gérés côté JS (color_pro_receiver.js) qui ajoute
# automatiquement un fx_N+1 quand un fx_N vient d'être connecté, comme le
# pattern déjà utilisé dans Packers.

from .color_fx_common import (
    COLOR_FX_TYPE,
    apply_fx_chain,
    collect_fx_from_kwargs,
)


class PyCodeMax_ColorProReceiver:
    """
    Applique une chaîne d'effets de colorimétrie sur une image.

    Les effets sont fournis par des nodes émetteurs (Channel Mixer FX,
    CSS Filters FX, etc.) branchés sur les slots dynamiques fx_1, fx_2, ...
    L'ordre d'application = l'ordre numérique des slots (fx_1 puis fx_2 puis ...).

    Pour désactiver un effet sans débrancher, utilisez le widget "enabled"
    du node émetteur.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                # fx_1 déclaré d'office — le JS ajoutera fx_2, fx_3, ...
                # quand l'utilisateur connectera quelque chose
                "fx_1": (COLOR_FX_TYPE,),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING",)
    RETURN_NAMES = ("image", "log",)
    FUNCTION = "process"
    CATEGORY = "Orion4D_MetaNode/ColorGrading"

    def process(self, image, **kwargs):
        fx_list = collect_fx_from_kwargs(kwargs)

        # Construction du log
        log_lines = [f"=== 🎨 Color Pro Receiver ==="]
        if not fx_list:
            log_lines.append("Aucun effet branché — image passée telle quelle.")
        else:
            for i, fx in enumerate(fx_list, 1):
                if not isinstance(fx, dict):
                    log_lines.append(f"  {i}. ⚠ slot non-dict ({type(fx).__name__})")
                    continue
                status = "✓" if fx.get("enabled", True) else "✗"
                label  = fx.get("label") or fx.get("type", "?")
                ftype  = fx.get("type", "?")
                log_lines.append(f"  {i}. {status} [{ftype}] {label}")

        # Application
        try:
            result = apply_fx_chain(image, fx_list)
        except Exception as e:
            log_lines.append(f"❌ Erreur application chaîne : {e}")
            return (image, "\n".join(log_lines))

        active_count = sum(1 for fx in fx_list if isinstance(fx, dict) and fx.get("enabled", True))
        log_lines.append(f"→ {active_count} effet(s) actif(s) sur {len(fx_list)} branché(s)")

        return (result, "\n".join(log_lines))


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_ColorProReceiver": PyCodeMax_ColorProReceiver}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ColorProReceiver": "🎨 Color Pro Receiver"}

# --- END OF FILE color_pro_receiver.py ---
