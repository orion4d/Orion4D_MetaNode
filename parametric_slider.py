# --- START OF FILE parametric_slider.py ---
import os
import json
from server import PromptServer
from aiohttp import web

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(NODE_DIR, "json_slider")

# Cache module-level avec invalidation par mtime
_presets_cache = None
_presets_mtime = 0

def load_slider_presets():
    global _presets_cache, _presets_mtime

    if not os.path.exists(JSON_DIR):
        os.makedirs(JSON_DIR, exist_ok=True)
        defaults = {
            "Pixels":      {"min": 1.0,   "max": 2048.0, "step": 1.0, "default": 512.0, "label": "Résolution", "precision": 0, "unit": "px"},
            "Pourcentage": {"min": 1.0,   "max": 500.0,  "step": 1.0, "default": 100.0, "label": "Taille",     "precision": 0, "unit": "%"},
            "Plage":       {"min": -10.0, "max": 10.0,   "step": 0.1, "default": 0.0,   "label": "Force",      "precision": 1, "unit": ""},
        }
        for name, data in defaults.items():
            with open(os.path.join(JSON_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    # Vérifie si un fichier JSON a changé depuis le dernier chargement
    try:
        json_files = [f for f in os.listdir(JSON_DIR) if f.endswith(".json")]
        latest_mtime = max(
            os.path.getmtime(os.path.join(JSON_DIR, f)) for f in json_files
        ) if json_files else 0
    except (ValueError, OSError):
        latest_mtime = 0

    # Retourne le cache si encore valide
    if _presets_cache is not None and latest_mtime <= _presets_mtime:
        return _presets_cache

    # Recharge depuis le disque
    _presets_mtime = latest_mtime
    presets = {}

    for filename in os.listdir(JSON_DIR):
        if filename.endswith(".json"):
            name = filename[:-5]
            try:
                with open(os.path.join(JSON_DIR, filename), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        presets[name] = data
            except Exception as e:
                print(f"[Orion4D] Erreur chargement {filename}: {e}")

    if not presets:
        presets["Default"] = {"min": 0.0, "max": 1.0, "step": 0.1, "default": 0.5, "label": "Valeur", "precision": 1, "unit": ""}

    _presets_cache = dict(sorted(presets.items()))
    return _presets_cache


@PromptServer.instance.routes.get("/orion4d/slider_presets")
async def get_slider_presets(request):
    return web.json_response(load_slider_presets())


@PromptServer.instance.routes.post("/orion4d/reload_presets")
async def reload_presets(request):
    global _presets_cache
    _presets_cache = None
    return web.json_response(load_slider_presets())


class PyCodeMax_ParametricSlider:
    @classmethod
    def INPUT_TYPES(cls):
        presets = load_slider_presets()
        preset_names = list(presets.keys()) if presets else ["Default"]
        return {
            "required": {
                "preset":                 (preset_names,),
                "value":                  ("FLOAT", {"default": 50.0, "min": -999999.0, "max": 999999.0, "step": 0.1, "display": "slider"}),
                "control_after_generate": (["fixed", "increment", "decrement", "randomize"],),
            }
        }

    RETURN_TYPES  = ("FLOAT", "INT", "STRING", "STRING", "FLOAT", "FLOAT", "FLOAT", "STRING")
    RETURN_NAMES  = ("float_val", "int_val", "text_val", "label", "min", "max", "step", "log")
    FUNCTION      = "calculate_value"
    CATEGORY      = "Orion4D_MetaNode/UI Widgets"

    def calculate_value(self, preset, value, control_after_generate):
        presets = load_slider_presets()
        p = presets.get(preset, {})

        # Clamp défensif avec les bornes du preset
        p_min  = float(p.get("min",  -999999.0))
        p_max  = float(p.get("max",   999999.0))
        p_step = float(p.get("step",  1.0))
        p_def  = float(p.get("default", p_min))
        slider_val = max(p_min, min(p_max, float(value)))

        precision = int(p.get("precision", 1))
        unit      = str(p.get("unit", ""))[:3]
        label     = str(p.get("label", preset))

        if precision <= 0:
            val_float = float(int(round(slider_val)))
            val_int   = int(val_float)
            val_str   = f"{val_int}{unit}"
        else:
            val_float = round(slider_val, precision)
            val_int   = int(round(val_float))
            val_str   = f"{val_float:.{precision}f}{unit}"

        # Calcul position relative dans la plage (0–100 %)
        range_size   = p_max - p_min
        pct          = ((val_float - p_min) / range_size * 100) if range_size != 0 else 0.0
        bar_width    = 20
        filled       = int(round(pct / 100 * bar_width))
        bar          = "█" * filled + "░" * (bar_width - filled)

        log = (
            f"╔══ 🎚️  Parametric Slider ══════════════╗\n"
            f"║  Preset      : {preset}\n"
            f"║  Label       : {label}\n"
            f"║  Valeur      : {val_str}\n"
            f"║  [{bar}] {pct:.1f}%\n"
            f"╠════════════════════════════════════════╣\n"
            f"║  float_val   : {val_float}\n"
            f"║  int_val     : {val_int}\n"
            f"║  text_val    : {val_str}\n"
            f"╠════════════════════════════════════════╣\n"
            f"║  min         : {p_min}{unit}\n"
            f"║  max         : {p_max}{unit}\n"
            f"║  step        : {p_step}\n"
            f"║  default     : {p_def}{unit}\n"
            f"║  precision   : {precision}\n"
            f"║  control     : {control_after_generate}\n"
            f"╚════════════════════════════════════════╝"
        )

        return (val_float, val_int, val_str, label, p_min, p_max, p_step, log)


NODE_CLASS_MAPPINGS        = {"PyCodeMax_ParametricSlider": PyCodeMax_ParametricSlider}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ParametricSlider": "🎚️ Parametric Slider"}
# --- END OF FILE parametric_slider.py ---