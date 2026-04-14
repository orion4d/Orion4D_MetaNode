# --- START OF FILE dynamic_splitter.py ---
#
# Orion Dynamic Splitter
# 1 entrée → N sorties dynamiques gérées par le JS.
# Broadcast : même donnée sur toutes les sorties actives.
# Sorties inactives → ExecutionBlocker(None).
#
# IMPORTANT : les RETURN_TYPES sont gérés dynamiquement par le JS
# via addOutput/removeOutput. Python utilise un maximum de sécurité.

import json as _json

try:
    from comfy_execution.graph import ExecutionBlocker
    _HAS_BLOCKER = True
except ImportError:
    _HAS_BLOCKER = False

MAX_OUTPUTS = 32


class PyCodeMax_DynamicSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":       ("*",),
                "config_json": ("STRING", {"default": "[]", "multiline": False}),
            }
        }

    # Python déclare MAX_OUTPUTS sorties fixes — le JS en cache le surplus
    RETURN_TYPES = tuple(["*"] * MAX_OUTPUTS) + ("STRING",)
    RETURN_NAMES = tuple([f"out_{i+1}" for i in range(MAX_OUTPUTS)]) + ("log",)
    FUNCTION     = "split"
    CATEGORY     = "Orion4D_MetaNode/Routing"

    def split(self, input, config_json, **kwargs):
        try:
            configs = _json.loads(config_json)
        except Exception:
            configs = []

        inactive = ExecutionBlocker(None) if _HAS_BLOCKER else None

        outputs      = []
        active_names = []

        for i in range(MAX_OUTPUTS):
            if i < len(configs):
                cfg     = configs[i]
                enabled = cfg.get("enabled", True)
                label   = cfg.get("label", "") or f"out_{i+1}"
                if enabled:
                    outputs.append(input)
                    active_names.append(label)
                else:
                    outputs.append(inactive)
            else:
                # Au-delà de la config → toujours bloquer
                outputs.append(inactive)

        if active_names:
            log = f"✅ {len(active_names)} active(s) : " + ", ".join(active_names)
        else:
            log = "⚠️ Aucune sortie active."

        return tuple(outputs) + (log,)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS        = {"PyCodeMax_DynamicSplitter": PyCodeMax_DynamicSplitter}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_DynamicSplitter": "🔀 Dynamic Splitter"}
# --- END OF FILE dynamic_splitter.py ---
