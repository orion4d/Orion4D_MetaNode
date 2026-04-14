# --- START OF FILE color_fx_presets.py ---
#
# Système de presets pour les nodes Color FX (Channel Mixer, CSS Filters,
# HSL, et tous les futurs FX du pack).
#
# Architecture :
#   - Dossier racine : <pack_root>/fx_setup/
#   - Sous-dossiers par type de FX : fx_setup/channel_mixer/, fx_setup/css_filters/, fx_setup/hsl/
#   - Un preset = un fichier JSON contenant uniquement les params métier
#     (ni enabled, ni label, ni image_in)
#
# Routes API exposées (toutes utilisées par color_fx_presets.js) :
#   - GET  /orion4d/fx_presets/list?fx_type=<type>
#   - GET  /orion4d/fx_presets/load?fx_type=<type>&name=<name>
#   - POST /orion4d/fx_presets/save    body: {fx_type, name, params}
#   - POST /orion4d/fx_presets/delete  body: {fx_type, name}
#
# Sécurité :
#   - fx_type doit être whitelisté (ALLOWED_FX_TYPES)
#   - name est sanitizé pour ne contenir que [a-zA-Z0-9_-] (pas de path
#     traversal, pas de séparateurs, pas de "..")
#   - Le chemin résolu doit rester sous fx_setup/<fx_type>/

import os
import re
import json
from server import PromptServer
from aiohttp import web

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
NODE_DIR    = os.path.dirname(os.path.abspath(__file__))
FX_SETUP_DIR = os.path.join(NODE_DIR, "fx_setup")
os.makedirs(FX_SETUP_DIR, exist_ok=True)

# Whitelist des types de FX qui peuvent avoir des presets.
# À mettre à jour quand on ajoute un nouveau FX au pack.
ALLOWED_FX_TYPES = {
    "channel_mixer",
    "css_filters",
    "hsl",
    "color_balance",
    "photo_filter",
    "vibrance",
    "curves",
}

# ---------------------------------------------------------------------------
# Migration automatique des anciens presets Curves Pro (json_curves/ → fx_setup/curves/)
# ---------------------------------------------------------------------------
# Au premier démarrage après le patch, on copie les .json de l'ancien dossier
# vers le nouveau en les wrappant dans {"all_curves_json": "..."} pour matcher
# la convention des params FX. Les fichiers existants dans fx_setup/curves/
# ne sont pas écrasés.
def _migrate_curves_presets():
    old_dir = os.path.join(NODE_DIR, "json_curves")
    new_dir = os.path.join(FX_SETUP_DIR, "curves")
    if not os.path.isdir(old_dir):
        return
    os.makedirs(new_dir, exist_ok=True)
    migrated = 0
    skipped = 0
    for fn in os.listdir(old_dir):
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        src = os.path.join(old_dir, fn)
        dst = os.path.join(new_dir, fn)
        if os.path.exists(dst):
            skipped += 1
            continue
        try:
            with open(src, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            # Ancien format : {"rgb": [...], "r": [...], "g": [...], "b": [...]}
            # Nouveau format : {"all_curves_json": "<json string>"}
            wrapped = {"all_curves_json": json.dumps(old_data)}
            with open(dst, "w", encoding="utf-8") as f:
                json.dump(wrapped, f, indent=2, ensure_ascii=False)
            migrated += 1
        except Exception as e:
            print(f"[ColorFX presets] Erreur migration '{fn}': {e}")
    if migrated or skipped:
        print(f"[ColorFX presets] Migration curves : {migrated} migré(s), {skipped} déjà présent(s)")


_migrate_curves_presets()

# Nom de fichier valide : alphanum + underscore + tiret, longueur 1..64
_NAME_RE = re.compile(r"^[a-zA-Z0-9_\- ]{1,64}$")


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------
def _is_valid_fx_type(fx_type: str) -> bool:
    return isinstance(fx_type, str) and fx_type in ALLOWED_FX_TYPES


def _is_valid_name(name: str) -> bool:
    if not isinstance(name, str):
        return False
    if not _NAME_RE.match(name):
        return False
    if ".." in name or "/" in name or "\\" in name:
        return False
    return True


def _fx_dir(fx_type: str) -> str:
    """Retourne (et crée) le dossier des presets pour un type donné."""
    d = os.path.join(FX_SETUP_DIR, fx_type)
    os.makedirs(d, exist_ok=True)
    return d


def _preset_path(fx_type: str, name: str) -> str:
    """Construit le chemin absolu d'un preset, sécurisé contre traversal."""
    d = _fx_dir(fx_type)
    fp = os.path.abspath(os.path.join(d, f"{name}.json"))
    # Garde-fou : le chemin résolu DOIT rester sous d
    if not fp.startswith(os.path.abspath(d) + os.sep):
        raise ValueError(f"chemin refusé pour preset '{name}'")
    return fp


def list_presets(fx_type: str) -> list:
    """Liste les noms (sans extension) des presets d'un type."""
    if not _is_valid_fx_type(fx_type):
        return []
    d = _fx_dir(fx_type)
    try:
        return sorted(
            f[:-5] for f in os.listdir(d)
            if f.endswith(".json") and not f.startswith(".")
        )
    except OSError:
        return []


def load_preset(fx_type: str, name: str) -> dict:
    """Charge un preset depuis le disque. Retourne {} si introuvable."""
    if not _is_valid_fx_type(fx_type) or not _is_valid_name(name):
        return {}
    try:
        fp = _preset_path(fx_type, name)
    except ValueError:
        return {}
    if not os.path.isfile(fp):
        return {}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception as e:
        print(f"[ColorFX presets] Erreur lecture '{name}': {e}")
        return {}


def save_preset(fx_type: str, name: str, params: dict) -> bool:
    """Sauvegarde un preset (params métier seulement, pas enabled/label)."""
    if not _is_valid_fx_type(fx_type) or not _is_valid_name(name):
        return False
    if not isinstance(params, dict):
        return False
    try:
        fp = _preset_path(fx_type, name)
    except ValueError:
        return False
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(params, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ColorFX presets] Erreur écriture '{name}': {e}")
        return False


def delete_preset(fx_type: str, name: str) -> bool:
    if not _is_valid_fx_type(fx_type) or not _is_valid_name(name):
        return False
    try:
        fp = _preset_path(fx_type, name)
    except ValueError:
        return False
    if not os.path.isfile(fp):
        return False
    try:
        os.remove(fp)
        return True
    except Exception as e:
        print(f"[ColorFX presets] Erreur suppression '{name}': {e}")
        return False


# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------
@PromptServer.instance.routes.get("/orion4d/fx_presets/list")
async def _api_list(request):
    fx_type = request.rel_url.query.get("fx_type", "")
    if not _is_valid_fx_type(fx_type):
        return web.json_response({"error": f"fx_type non valide : '{fx_type}'"}, status=400)
    return web.json_response({"fx_type": fx_type, "presets": list_presets(fx_type)})


@PromptServer.instance.routes.get("/orion4d/fx_presets/load")
async def _api_load(request):
    q = request.rel_url.query
    fx_type = q.get("fx_type", "")
    name    = q.get("name", "")
    if not _is_valid_fx_type(fx_type):
        return web.json_response({"error": "fx_type invalide"}, status=400)
    if not _is_valid_name(name):
        return web.json_response({"error": "nom invalide"}, status=400)
    params = load_preset(fx_type, name)
    if not params:
        return web.json_response({"error": "preset introuvable"}, status=404)
    return web.json_response({"fx_type": fx_type, "name": name, "params": params})


@PromptServer.instance.routes.post("/orion4d/fx_presets/save")
async def _api_save(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    fx_type = data.get("fx_type", "")
    name    = data.get("name", "")
    params  = data.get("params", {})
    if not _is_valid_fx_type(fx_type):
        return web.json_response({"error": "fx_type invalide"}, status=400)
    if not _is_valid_name(name):
        return web.json_response({"error": "nom invalide (alphanum, espace, _, -, max 64 car.)"}, status=400)
    if not isinstance(params, dict):
        return web.json_response({"error": "params doit être un dict"}, status=400)
    ok = save_preset(fx_type, name, params)
    if not ok:
        return web.json_response({"error": "échec écriture"}, status=500)
    return web.json_response({"ok": True, "presets": list_presets(fx_type)})


@PromptServer.instance.routes.post("/orion4d/fx_presets/delete")
async def _api_delete(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "JSON invalide"}, status=400)
    fx_type = data.get("fx_type", "")
    name    = data.get("name", "")
    if not _is_valid_fx_type(fx_type):
        return web.json_response({"error": "fx_type invalide"}, status=400)
    if not _is_valid_name(name):
        return web.json_response({"error": "nom invalide"}, status=400)
    ok = delete_preset(fx_type, name)
    if not ok:
        return web.json_response({"error": "échec suppression"}, status=500)
    return web.json_response({"ok": True, "presets": list_presets(fx_type)})


print(f"[ColorFX presets] dossier : {FX_SETUP_DIR}")

# Ce module n'expose pas de NODE_CLASS_MAPPINGS — il sert juste comme
# infrastructure. Les routes sont enregistrées au moment de l'import.

# --- END OF FILE color_fx_presets.py ---
