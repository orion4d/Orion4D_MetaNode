# --- START OF FILE Master_ComboBox.py ---
#
# Master Combo Box v3 — option B (widget STRING + select HTML custom JS)
#
# Plus de hack AnyStringList, plus de préfixage visible.

import os
import json
from server import PromptServer
from aiohttp import web

DROPDOWNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dropdowns")
if not os.path.exists(DROPDOWNS_DIR):
    os.makedirs(DROPDOWNS_DIR)


def _scan_dropdowns():
    categories = []
    options_by_cat: dict[str, list[str]] = {}
    try:
        files = sorted(f for f in os.listdir(DROPDOWNS_DIR) if f.endswith(".json"))
    except OSError:
        return [], {}
    for filename in files:
        cat_name = filename[:-5]
        filepath = os.path.join(DROPDOWNS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                options = json.load(f)
        except Exception:
            continue
        if not isinstance(options, list):
            continue
        clean = [str(o) for o in options if isinstance(o, (str, int, float))]
        if clean:
            categories.append(cat_name)
            options_by_cat[cat_name] = clean
    return categories, options_by_cat


@PromptServer.instance.routes.get("/orion4d/get_dropdowns")
async def get_dropdowns(request):
    categories, options_by_cat = _scan_dropdowns()
    return web.json_response({
        "categories": categories,
        "options_by_category": options_by_cat,
    })


class PyCodeMax_MasterCombo:
    @classmethod
    def INPUT_TYPES(cls):
        categories, _ = _scan_dropdowns()
        if not categories:
            categories = ["(aucun_fichier)"]
        return {
            "required": {
                "category": (categories,),
                "value":    ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("selected_text",)
    FUNCTION = "get_selection"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    @classmethod
    def VALIDATE_INPUTS(cls, category, value):
        if not value:
            return True
        if category == "(aucun_fichier)":
            return True
        _categories, options_by_cat = _scan_dropdowns()
        if category not in options_by_cat:
            return f"Catégorie inconnue : '{category}'"
        if value not in options_by_cat[category]:
            return f"Valeur '{value}' introuvable dans la catégorie '{category}'"
        return True

    def get_selection(self, category, value):
        return (str(value or ""),)


NODE_CLASS_MAPPINGS = {"PyCodeMax_MasterCombo": PyCodeMax_MasterCombo}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_MasterCombo": "🔽 Master Combo Box"}

# --- END OF FILE Master_ComboBox.py ---
