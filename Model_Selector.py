# --- START OF FILE Model_Selector.py ---
#
# Model Selector v3 — option B (widget STRING + select HTML custom JS)
#
# - category : combo natif standard avec les vrais sous-dossiers
# - file_name : widget STRING piloté par un <select> HTML côté JS
# - VALIDATE_INPUTS vérifie que (category, file_name) existe sur disque
#   et bloque le path traversal.

import os
import folder_paths
from server import PromptServer
from aiohttp import web

ALLOWED_EXTS = {".safetensors", ".gguf", ".pth", ".bin", ".ckpt", ".pt"}


def _scan_models():
    """Retourne (categories, files_by_cat).

    Pour file_name, on retourne le chemin RELATIF À LA CATÉGORIE (sans le
    préfixe de catégorie), pour que l'utilisateur voie juste 'realistic.safetensors'
    et pas 'checkpoints/realistic.safetensors' dans le combo.
    """
    models_dir = folder_paths.models_dir
    categories = []
    files_by_cat: dict[str, list[str]] = {}

    if not os.path.isdir(models_dir):
        return [], {}

    for entry in sorted(os.listdir(models_dir)):
        cat_path = os.path.join(models_dir, entry)
        if not os.path.isdir(cat_path):
            continue
        cat_files = []
        for root, _dirs, files in os.walk(cat_path):
            for f in files:
                if os.path.splitext(f)[1].lower() in ALLOWED_EXTS:
                    # Chemin relatif à la catégorie (pas à models/)
                    rel = os.path.relpath(os.path.join(root, f), cat_path)
                    rel = rel.replace(os.sep, "/")
                    cat_files.append(rel)
        if cat_files:
            cat_files.sort()
            categories.append(entry)
            files_by_cat[entry] = cat_files

    return categories, files_by_cat


@PromptServer.instance.routes.get("/orion4d/get_models")
async def get_models(request):
    categories, files_by_cat = _scan_models()
    return web.json_response({
        "categories": categories,
        "files_by_category": files_by_cat,
    })


class PyCodeMax_ModelSelector:
    @classmethod
    def INPUT_TYPES(cls):
        categories, _ = _scan_models()
        if not categories:
            categories = ["(aucun)"]
        return {
            "required": {
                "category":  (categories,),
                "file_name": ("STRING", {"default": "", "multiline": False}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "*", "*",)
    RETURN_NAMES = ("absolute_path", "relative_path", "filename_only", "any_path", "any_filename",)
    FUNCTION = "get_path"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    @classmethod
    def VALIDATE_INPUTS(cls, category, file_name):
        if not file_name:
            return True  # pas encore sélectionné, on laisse passer
        if category == "(aucun)":
            return True
        _categories, files_by_cat = _scan_models()
        if category not in files_by_cat:
            return f"Catégorie inconnue : '{category}'"
        if file_name not in files_by_cat[category]:
            return f"Fichier '{file_name}' introuvable dans '{category}'"
        # Anti path-traversal de ceinture-bretelles
        models_dir = folder_paths.models_dir
        full = os.path.abspath(os.path.join(models_dir, category, file_name))
        if not full.startswith(os.path.abspath(models_dir) + os.sep):
            return f"Chemin refusé : {file_name}"
        if not os.path.isfile(full):
            return f"Fichier introuvable sur disque : {file_name}"
        return True

    def get_path(self, category, file_name):
        if not file_name or category == "(aucun)":
            return ("", "", "", "", "")
        # Le chemin relatif "ComfyUI standard" inclut la catégorie
        relative_path = f"{category}/{file_name}"
        absolute_path = os.path.join(folder_paths.models_dir, category, file_name)
        filename_only = os.path.basename(file_name)
        return (
            absolute_path,
            relative_path,
            filename_only,
            relative_path,
            filename_only,
        )


NODE_CLASS_MAPPINGS = {"PyCodeMax_ModelSelector": PyCodeMax_ModelSelector}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ModelSelector": "📂 Model Selector"}

# --- END OF FILE Model_Selector.py ---
