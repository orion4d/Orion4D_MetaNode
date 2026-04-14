# --- START OF FILE text_road.py ---
# Variante texte-only du Dynamic Road.
# Plusieurs entrées STRING, chacune avec memo / active toggle / prefix / suffix.
# Toutes les entrées actives sont concaténées en une seule sortie STRING.
# Pas d'entrées déclarées côté Python : le JS gère 100% des slots via addInput()
# (même pattern que PyCodeMax_DynamicRoad).

import json


class PyCodeMax_TextRoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                # Séparateur entre les blocs actifs. Supporte \n et \t.
                "separator":   ("STRING", {"default": "\\n"}),
                # JSON injecté par le JS : [{enabled, prefix, suffix}, ...]
                "config_json": ("STRING", {"default": "[]"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text_out",)
    FUNCTION     = "execute"
    CATEGORY     = "Orion4D_MetaNode/UI Widgets/Dynamic Widgets"

    def execute(self, separator, config_json, **kwargs):
        # Résolution des séquences d'échappement courantes
        sep = separator.replace("\\n", "\n").replace("\\t", "\t")

        try:
            configs = json.loads(config_json)
        except Exception:
            configs = []

        parts = []
        for i, cfg in enumerate(configs):
            if not cfg.get("enabled", True):
                continue
            key = f"txt_{i + 1}"
            val = str(kwargs.get(key) or "")
            prefix = str(cfg.get("prefix", ""))
            suffix = str(cfg.get("suffix", ""))
            parts.append(f"{prefix}{val}{suffix}")

        return (sep.join(parts),)


NODE_CLASS_MAPPINGS        = {"PyCodeMax_TextRoad": PyCodeMax_TextRoad}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_TextRoad": "📝 Text Road"}
# --- END OF FILE text_road.py ---
