# --- START OF FILE List_selector_max.py ---
# List Selector Max - Orion4D_MetaNode
#
# Node Python : reçoit le JSON d'état depuis le JS (sans groups_json exposé),
# concatène les sélections et retourne le résultat.

import os
import json
import random
import hashlib
import csv
from server import PromptServer
from aiohttp import web

ALLOWED_EXTS = {".txt", ".csv"}

# ---------------------------------------------------------------------------
# Racine ComfyUI (calculée une fois au chargement)
# ---------------------------------------------------------------------------
def _get_comfy_root() -> str:
    try:
        import folder_paths
        # abspath() sans realpath() : on ne suit pas les jonctions/symlinks,
        # sinon la comparaison dans _is_safe_path serait asymétrique.
        return os.path.abspath(folder_paths.base_path)
    except Exception:
        node_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.abspath(os.path.join(node_dir, "..", ".."))

_COMFY_ROOT = _get_comfy_root()

# ---------------------------------------------------------------------------
# Résolution des tokens de chemin relatif
# Tokens supportés :
#   {COMFY}  → dossier racine de ComfyUI
#   {CUSTOM} → racine personnalisée définie dans les réglages du node
#
# Exemples :
#   {COMFY}/custom_nodes/Orion4D_MetaNode/Lists/styles.txt
#   {CUSTOM}/abstract.txt
# ---------------------------------------------------------------------------
def _resolve_tokens(path: str, custom_root: str = "") -> str:
    """Remplace les tokens par leurs chemins absolus réels."""
    path = path.strip()
    if "{COMFY}" in path:
        path = path.replace("{COMFY}", _COMFY_ROOT)
    if "{CUSTOM}" in path:
        cr = custom_root.strip().strip('"') if custom_root else ""
        if cr:
            path = path.replace("{CUSTOM}", os.path.abspath(os.path.expanduser(cr)))
        else:
            # Token {CUSTOM} utilisé sans racine définie → on laisse passer
            # et _is_safe_path refusera si hors zone
            path = path.replace("{CUSTOM}", "")
    return os.path.abspath(os.path.expanduser(path))

def _tokenize_path(path: str, custom_root: str = "") -> str:
    """Remplace les préfixes de chemins absolus par leurs tokens pour l'affichage/stockage."""
    path = os.path.abspath(path)
    # {CUSTOM} en priorité (plus spécifique)
    if custom_root:
        cr = os.path.abspath(os.path.expanduser(custom_root.strip().strip('"')))
        if os.path.isdir(cr) and (path == cr or path.startswith(cr + os.sep)):
            return "{CUSTOM}" + path[len(cr):].replace("\\", "/")
    # {COMFY}
    if path == _COMFY_ROOT or path.startswith(_COMFY_ROOT + os.sep):
        return "{COMFY}" + path[len(_COMFY_ROOT):].replace("\\", "/")
    return path  # chemin absolu brut si hors zones tokenisables

def _is_safe_path(path: str, custom_root: str = "") -> bool:
    """
    Vérifie que `path` est sous une racine autorisée :
      1. Le dossier ComfyUI (toujours autorisé)
      2. Un dossier personnalisé fourni par l'utilisateur (custom_root)
    Note : on utilise abspath() sans realpath() pour ne pas résoudre
    les jonctions/symlinks Windows — un dossier jonction DANS ComfyUI
    doit rester accessible même si sa cible est sur un autre disque.
    """
    path = os.path.abspath(path)
    allowed = [_COMFY_ROOT]
    if custom_root:
        cr = os.path.abspath(os.path.expanduser(custom_root.strip().strip('"')))
        if os.path.isdir(cr):
            allowed.append(cr)
    return any(
        path == root or path.startswith(root + os.sep)
        for root in allowed
    )

# ---------------------------------------------------------------------------
# API : Exposer la racine ComfyUI et les tokens au frontend
# ---------------------------------------------------------------------------
@PromptServer.instance.routes.get("/orion4d/lsm/comfy_root")
async def lsm_comfy_root(request):
    return web.json_response({
        "root": _COMFY_ROOT,
        "tokens": ["{COMFY}", "{CUSTOM}"],
        "token_values": {"{COMFY}": _COMFY_ROOT},
    })

# ---------------------------------------------------------------------------
# API : Lister dossiers + fichiers .txt/.csv dans un chemin
# ---------------------------------------------------------------------------
@PromptServer.instance.routes.get("/orion4d/lsm/list_dir")
async def lsm_list_dir(request):
    """Retourne l'arborescence (dossiers + fichiers .txt/.csv) d'un chemin."""
    raw         = request.rel_url.query.get("path", "").strip().strip('"')
    custom_root = request.rel_url.query.get("root", "").strip()

    if not raw:
        try:
            import folder_paths
            raw = folder_paths.get_input_directory()
        except Exception:
            raw = _COMFY_ROOT

    # Résoudre les tokens AVANT validation de sécurité
    path = _resolve_tokens(raw, custom_root)

    if not _is_safe_path(path, custom_root):
        return web.json_response(
            {"error": f"Chemin hors des zones autorisées.\n"
                      f"ComfyUI : {_COMFY_ROOT}\n"
                      f"Racine personnalisée : {custom_root or '(aucune)'}"},
            status=403
        )
    if not os.path.isdir(path):
        return web.json_response({"error": "Dossier introuvable", "path": path}, status=404)

    dirs = []
    files = []
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir(follow_symlinks=False):
                dirs.append({"name": entry.name, "path": entry.path})
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in ALLOWED_EXTS:
                    files.append({"name": entry.name, "path": entry.path, "ext": ext})
    except PermissionError:
        return web.json_response({"error": "Permission refusée", "path": path}, status=403)

    parent = str(os.path.dirname(path)) if path != os.path.dirname(path) else None
    return web.json_response({
        # current et parent : chemins absolus réels pour la navigation interne
        "current":         path,
        "current_token":   _tokenize_path(path, custom_root),
        "parent":          parent,
        "dirs":  [{"name": d["name"],
                   "path": d["path"],
                   "path_token": _tokenize_path(d["path"], custom_root)} for d in dirs],
        "files": [{"name": f["name"],
                   "path": f["path"],
                   "path_token": _tokenize_path(f["path"], custom_root),
                   "ext":  f["ext"]} for f in files],
    })


# ---------------------------------------------------------------------------
# API : Lire le contenu d'un fichier .txt/.csv
# ---------------------------------------------------------------------------
@PromptServer.instance.routes.get("/orion4d/lsm/read_file")
async def lsm_read_file(request):
    """Lit un fichier et retourne ses lignes non vides."""
    raw         = request.rel_url.query.get("path", "").strip().strip('"')
    custom_root = request.rel_url.query.get("root", "").strip()
    if not raw:
        return web.json_response({"error": "Chemin vide"}, status=400)

    # Résoudre les tokens AVANT validation de sécurité
    path = _resolve_tokens(raw, custom_root)

    if not _is_safe_path(path, custom_root):
        return web.json_response(
            {"error": "Chemin hors des zones autorisées."}, status=403
        )

    ext = os.path.splitext(path)[1].lower()
    if ext not in ALLOWED_EXTS:
        return web.json_response({"error": f"Extension '{ext}' non supportée"}, status=400)
    if not os.path.isfile(path):
        return web.json_response({"error": "Fichier introuvable"}, status=404)

    # Point 4 — Fallback d'encodage : utf-8-sig → latin-1 → cp1252
    ENCODINGS = ("utf-8-sig", "latin-1", "cp1252")

    def _read_lines_txt(filepath):
        for enc in ENCODINGS:
            try:
                with open(filepath, encoding=enc) as f:
                    return [l.strip() for l in f if l.strip()]
            except UnicodeDecodeError:
                continue
        # Dernier recours : remplacer les caractères illisibles
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return [l.strip() for l in f if l.strip()]

    def _read_lines_csv(filepath):
        for enc in ENCODINGS:
            try:
                with open(filepath, newline="", encoding=enc) as f:
                    return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]
            except UnicodeDecodeError:
                continue
        with open(filepath, newline="", encoding="utf-8", errors="replace") as f:
            return [row[0].strip() for row in csv.reader(f) if row and row[0].strip()]

    lines = []
    try:
        lines = _read_lines_csv(path) if ext == ".csv" else _read_lines_txt(path)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

    return web.json_response({
        "lines":      lines,
        "count":      len(lines),
        "path_token": _tokenize_path(path, custom_root),
    })


# ---------------------------------------------------------------------------
# Node ComfyUI
# ---------------------------------------------------------------------------
class PyCodeMax_ListSelectorMax:
    """
    List Selector Max — sélectionne et concatène des lignes depuis
    plusieurs fichiers .txt/.csv avec seed indépendant par groupe.
    Le séparateur est défini par groupe.
    L'état complet est persisté via node.properties côté JS.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            # groups_json est hidden : géré en interne JS→Python via widget caché
            "required": {},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                # Transporté par le workflow, non visible dans l'UI
                "lsm_state_json": ("STRING", {"default": "{}"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT",)
    RETURN_NAMES = ("concatenated", "lines_json", "total_count",)
    FUNCTION = "process"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    @classmethod
    def IS_CHANGED(cls, lsm_state_json="", **kwargs):
        """Ne déclenche le recalcul que si les données impactant la sortie changent.
        Les changements purement UI (collapse, label de groupe…) sont ignorés."""
        try:
            state = json.loads(lsm_state_json)
            data_to_hash = {
                "override": state.get("previewOverride", ""),
                "groups": [
                    {
                        "enabled":        g.get("enabled"),
                        "seed":           g.get("seed"),
                        "mode":           g.get("seed_mode"),
                        "selected_index": g.get("selected_index"),
                        "edited_line":    g.get("edited_line"),
                        "separator":      g.get("separator"),
                        # Les lignes elles-mêmes (fichier rechargé = nouveau hash)
                        "lines_hash":     hashlib.md5(
                            json.dumps(g.get("lines", []), ensure_ascii=False).encode()
                        ).hexdigest(),
                    }
                    for g in state.get("groups", [])
                ],
            }
            return hashlib.md5(
                json.dumps(data_to_hash, sort_keys=True).encode("utf-8")
            ).hexdigest()
        except Exception:
            return float("nan")  # Force le recalcul en cas de JSON invalide

    def _resolve_parts(self, groups):
        """Résout la ligne sélectionnée de chaque groupe actif."""
        parts = []
        for group in groups:
            if not group.get("enabled", True):
                continue
            lines = group.get("lines", [])
            if not lines:
                continue
            n = len(lines)
            mode = group.get("seed_mode", "select")
            seed = int(group.get("seed", 0))
            selected_idx = int(group.get("selected_index", 0))

            if mode == "randomize":
                idx = random.Random(seed).randint(0, n - 1)
            elif mode == "increment":
                idx = seed % n
            elif mode == "decrement":
                idx = (n - 1 - (seed % n))
            else:
                idx = max(0, min(selected_idx, n - 1))

            chosen = lines[idx]
            edited = group.get("edited_line", "").strip()
            if edited:
                chosen = edited
            parts.append(chosen)
        return parts

    def process(self, lsm_state_json="{}", **kwargs):
        try:
            state = json.loads(lsm_state_json)
        except Exception:
            state = {}

        groups = state.get("groups", [])
        parts  = self._resolve_parts(groups)

        # Override manuel : l'utilisateur a édité le preview directement
        override = state.get("previewOverride", "").strip()
        if override:
            return (override, json.dumps(parts, ensure_ascii=False), len(parts))

        # Séparateurs des groupes actifs (dans l'ordre)
        active_seps = [
            g.get("separator", ", ").replace("\\n", "\n").replace("\\t", "\t")
            for g in groups
            if g.get("enabled", True) and g.get("lines", [])
        ]

        # Concaténation : part[0] + sep[0] + part[1] + sep[1] + …
        result = ""
        for i, part in enumerate(parts):
            result += part
            if i < len(parts) - 1:
                result += active_seps[i] if i < len(active_seps) else ", "

        return (result, json.dumps(parts, ensure_ascii=False), len(parts))


# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_ListSelectorMax": PyCodeMax_ListSelectorMax}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_ListSelectorMax": "📋 List Selector Max"}

# --- END OF FILE List_selector_max.py ---
