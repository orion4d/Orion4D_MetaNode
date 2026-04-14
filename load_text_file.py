# --- START OF FILE load_text_file.py ---
# Load Text File - Orion4D_MetaNode  v2
#
# Philosophie : pas de stockage, pas de menu déroulant.
# Le contenu du fichier est lu et placé dans un widget STRING multiline
# directement éditable. L'API sert uniquement à lire le fichier côté serveur
# si le client ne peut pas le lire directement (fallback).
#
# Entrée  : text_content (STRING, multiline, éditable)
# Sortie  : text (STRING)

import os
import hashlib
from server import PromptServer
from aiohttp import web

ALLOWED_EXTENSIONS = {
    ".txt", ".json", ".csv", ".py", ".js", ".ts", ".md",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
    ".sh", ".bat", ".ini", ".cfg", ".log"
}

# Plafond de taille pour éviter un DoS mémoire via upload massif
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# ---------------------------------------------------------------------------
# Route API : lit un fichier et retourne son contenu (aucun stockage)
# ---------------------------------------------------------------------------
@PromptServer.instance.routes.post("/orion4d/read_text_file")
async def read_text_file(request):
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            return web.json_response({"error": "Champ 'file' manquant"}, status=400)

        filename = field.filename or "upload.txt"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            return web.json_response(
                {"error": f"Extension '{ext}' non supportée."},
                status=400
            )

        raw = b""
        while True:
            chunk = await field.read_chunk(65536)
            if not chunk:
                break
            raw += chunk
            if len(raw) > MAX_FILE_SIZE:
                return web.json_response(
                    {"error": f"Fichier trop volumineux (> {MAX_FILE_SIZE // (1024*1024)} MB)."},
                    status=413,
                )

        content = None
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                content = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            return web.json_response({"error": "Impossible de décoder le fichier."}, status=400)

        return web.json_response({
            "filename": filename,
            "content": content,
        })

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# Node ComfyUI
# ---------------------------------------------------------------------------
class PyCodeMax_LoadTextFile:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_content": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": False,
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "passthrough"
    CATEGORY = "Orion4D_MetaNode/Loaders"

    @classmethod
    def IS_CHANGED(cls, text_content, **kwargs):
        return hashlib.md5(text_content.encode("utf-8", errors="replace")).hexdigest()

    def passthrough(self, text_content, **kwargs):
        return (text_content,)


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_LoadTextFile": PyCodeMax_LoadTextFile}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_LoadTextFile": "📄 Load Text File"}

# --- END OF FILE load_text_file.py ---
