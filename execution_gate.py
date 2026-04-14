# --- START OF FILE execution_gate.py ---

try:
    from comfy_execution.graph import ExecutionBlocker
    _HAS_BLOCKER = True
except ImportError:
    _HAS_BLOCKER = False


class PyCodeMax_ExecutionGate:
    """
    Laisse passer ou bloque l'exécution d'un flux selon un booléen.
    - continue = True  → la donnée passe
    - continue = False → ExecutionBlocker (le flux en aval est stoppé)

    Accepte n'importe quel type en entrée (universel).
    Compatible avec la sortie 'boolean' du Boolean Switch.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input":    ("*",),
                "continue": ("BOOLEAN", {
                    "default": True,
                    "label_on":  "Open  ✅",
                    "label_off": "Blocked 🚫",
                }),
            }
        }

    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION     = "gate"
    CATEGORY     = "Orion4D_MetaNode/Routing"

    def gate(self, input, **kwargs):
        open_gate = kwargs.get("continue", True)
        if open_gate:
            return (input,)
        else:
            blocker = ExecutionBlocker(None) if _HAS_BLOCKER else None
            return (blocker,)


NODE_CLASS_MAPPINGS        = {"PyCodeMax_ExecutionGate": PyCodeMax_ExecutionGate}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ExecutionGate": "🚦 Execution Gate"}

# --- END OF FILE execution_gate.py ---
