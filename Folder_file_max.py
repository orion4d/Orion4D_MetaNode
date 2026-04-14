# --- START OF FILE Folder_file_max.py ---
import os
import io
import re
import sys
import json
import random
import subprocess
import datetime
import hashlib
import time
import asyncio
import torch
import numpy as np
from PIL import Image, ImageOps
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

from aiohttp import web
from server import PromptServer

SUPPORTED_IMAGE_EXT = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".svg"]
SUPPORTED_VIDEO_EXT = [".mp4", ".webm", ".mov", ".mkv", ".avi"]
SUPPORTED_AUDIO_EXT = [".mp3", ".wav", ".ogg", ".flac"]

ALL_SUPPORTED_EXT = set(SUPPORTED_IMAGE_EXT + SUPPORTED_VIDEO_EXT + SUPPORTED_AUDIO_EXT)

# ---------------------------------------------------------------------------
# SÉCURITÉ : allow-list des racines accessibles via les routes HTTP
# ---------------------------------------------------------------------------
def _build_allowed_roots():
    roots = []
    try:
        import folder_paths  # type: ignore
        builtin = (
            ("{COMFY}/input",  "get_input_directory"),
            ("{COMFY}/output", "get_output_directory"),
            ("{COMFY}/temp",   "get_temp_directory"),
        )
        for label, fn in builtin:
            try:
                p = getattr(folder_paths, fn)()
                if p:
                    roots.append((label, os.path.abspath(p)))
            except Exception:
                pass
        try:
            roots.append(("{COMFY}/models", os.path.abspath(folder_paths.models_dir)))
        except Exception:
            pass
    except Exception:
        pass

    extra = os.environ.get("ORION4D_FOLDER_ROOTS", "")
    if extra:
        for part in extra.split(os.pathsep):
            part = part.strip().strip('"')
            if part:
                abs_p = os.path.abspath(os.path.expanduser(part))
                roots.append((abs_p, abs_p))

    seen = set()
    unique = []
    for label, p in roots:
        if p and p not in seen and os.path.isdir(p):
            seen.add(p)
            unique.append({"label": label, "path": p})
    return unique

_ALLOWED_ROOTS = _build_allowed_roots()
_ALLOWED_ROOT_PATHS = [r["path"] for r in _ALLOWED_ROOTS]
print(f"[FolderFileMax] Racines autorisées ({len(_ALLOWED_ROOTS)}) :")
for r in _ALLOWED_ROOTS:
    print(f"  {r['label']:30s} → {r['path']}")


def _is_safe_path(path: str, root_constraint: str = "") -> bool:
    if not path:
        return False
    try:
        abs_path = os.path.abspath(os.path.expanduser(str(path)))
    except Exception:
        return False

    if root_constraint:
        try:
            abs_root = os.path.abspath(os.path.expanduser(str(root_constraint)))
        except Exception:
            return False
        if abs_root not in _ALLOWED_ROOT_PATHS:
            return False
        return abs_path == abs_root or abs_path.startswith(abs_root + os.sep)

    for root in _ALLOWED_ROOT_PATHS:
        try:
            if abs_path == root or abs_path.startswith(root + os.sep):
                return True
        except Exception:
            continue
    return False


def _safe_ext(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ALL_SUPPORTED_EXT

def classify_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg": return "svg"
    if ext in SUPPORTED_IMAGE_EXT: return "image"
    if ext in SUPPORTED_VIDEO_EXT: return "video"
    if ext in SUPPORTED_AUDIO_EXT: return "audio"
    return "other"

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(NODE_DIR, "folder_file_max.config.json")

def _load_cfg():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception: pass
    return {}

def _save_cfg(data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception: pass

class FInfo:
    def __init__(self, name, path, size, mtime):
        self.name = name
        self.path = path
        self.size = size
        self.mtime = mtime

def _norm_exts(exts: str):
    if not exts: return []
    raw = exts.replace(";", ",").split(",")
    out = []
    for r in raw:
        r = r.strip().lower()
        if not r: continue
        if not r.startswith("."): r = "." + r
        out.append(r)
    return list(dict.fromkeys(out))

def _list_files_current_dir(directory: str, extensions):
    directory = os.path.expanduser(str(directory)).strip().strip('"')
    if not os.path.isdir(directory): return []
    results = []
    try:
        for fn in os.listdir(directory):
            full = os.path.join(directory, fn)
            if not os.path.isfile(full) or fn.startswith("."): continue
            if extensions and (os.path.splitext(fn)[1].lower() not in extensions): continue
            try:
                st = os.stat(full)
                results.append(FInfo(fn, os.path.abspath(full), int(st.st_size), float(st.st_mtime)))
            except Exception: continue
    except Exception: return []
    # sécurité perf : limite à 5000 fichiers
    if len(results) > 5000:
        print(f"[FolderFileMax] Dossier trop grand ({len(results)} fichiers), tronqué à 5000")
        results = results[:5000]
    return results

def _apply_regex(files, pattern: str, mode: str, ignore_case: bool):
    pat = (pattern or "").strip()
    if not pat: return files
    flags = re.IGNORECASE if ignore_case else 0
    try: rx = re.compile(pat, flags)
    except re.error: return files
    include = (mode or "include").lower() != "exclude"
    if include: return [f for f in files if rx.search(f.name)]
    return [f for f in files if not rx.search(f.name)]

def _sort_files(files, sort_by: str, descending: bool):
    sb = (sort_by or "name").lower()
    if sb == "name": key = lambda f: (f.name.lower(), f.path)
    elif sb == "mtime": key = lambda f: (f.mtime, f.name.lower(), f.path)
    else: key = lambda f: (f.size, f.name.lower(), f.path)
    return sorted(files, key=key, reverse=bool(descending))

def _iso(ts: float):
    try: return datetime.datetime.fromtimestamp(ts).isoformat(timespec="seconds")
    except Exception: return ""

def _get_file_info(path: str):
    info = {"name": os.path.basename(path), "path": os.path.abspath(path)}
    try:
        st = os.stat(path)
        info["size_bytes"] = int(st.st_size)
        info["created"] = st.st_ctime
        info["modified"] = st.st_mtime
    except Exception:
        info["size_bytes"] = -1
    info["type"] = classify_type(path)
    return info

def _open_in_explorer(target: str) -> None:
    if os.name == "nt":
        if os.path.isfile(target):
            try:
                subprocess.Popen(["explorer", "/select,", target], close_fds=True)
                return
            except Exception:
                pass
        os.startfile(target)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", target], close_fds=True)
    else:
        subprocess.Popen(["xdg-open", target], close_fds=True)

# ---------------------------------------------------------------------------
# CACHE THUMBNAILS - PERFORMANCE
# ---------------------------------------------------------------------------
THUMB_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "orion4d", "thumbs")
os.makedirs(THUMB_CACHE, exist_ok=True)
_executor = ThreadPoolExecutor(max_workers=2)

@lru_cache(maxsize=512)
def _thumb_key(path: str) -> str:
    try:
        st = os.stat(path)
        raw = f"{path}|{st.st_mtime}|{st.st_size}".encode()
    except:
        raw = path.encode()
    return hashlib.sha1(raw).hexdigest()

def _thumb_path(key: str) -> str:
    return os.path.join(THUMB_CACHE, f"{key}.webp")

async def _make_thumb(src: str, dst: str, size: int = 320):
    def work():
        with Image.open(src) as im:
            # draft réduit le décodage JPEG
            try:
                im.draft('RGB', (size*2, size*2))
            except Exception:
                pass
            im = ImageOps.exif_transpose(im)
            has_alpha = (im.mode in ("RGBA", "LA")) or (im.mode == "P" and "transparency" in im.info)
            im = im.convert("RGBA") if has_alpha else im.convert("RGB")
            im.thumbnail((size, size), Image.LANCZOS)
            im.save(dst, 'WEBP', quality=82, method=6)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, work)

# nettoyage cache >30 jours au démarrage
try:
    now = time.time()
    for f in os.listdir(THUMB_CACHE):
        fp = os.path.join(THUMB_CACHE, f)
        if now - os.path.getmtime(fp) > 30*86400:
            try: os.remove(fp)
            except: pass
except Exception:
    pass

# --- API ROUTES ---

@PromptServer.instance.routes.get("/folder_file_max/roots")
async def http_roots(request):
    return web.json_response({"roots": _ALLOWED_ROOTS})


@PromptServer.instance.routes.get("/folder_file_max/current_index")
async def http_current_index(request):
    uid = request.rel_url.query.get("node_id", "default")
    idx = PyCodeMax_FolderFileMax._state.get(str(uid), None)
    return web.json_response({"index": idx})

@PromptServer.instance.routes.post("/folder_file_max/set_index")
async def http_set_index(request):
    """Définit l'index courant pour un node donné. Appelé par le JS quand
    l'utilisateur clique sur une carte dans la grille — sert de point de
    départ pour le prochain run en mode increment/decrement.
    En mode increment, on stocke index-1 pour que le prochain (+1) tombe
    sur la carte cliquée. En mode decrement, on stocke index+1.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}
    uid = str(data.get("node_id", "default"))[:64]
    try:
        idx = int(data.get("index", 0))
    except Exception:
        idx = 0
    mode = str(data.get("seed_mode", "manual")).lower()
    try:
        n = int(data.get("count", 0))
    except Exception:
        n = 0
    if n < 1:
        n = 1

    if len(PyCodeMax_FolderFileMax._state) > 512 and uid not in PyCodeMax_FolderFileMax._state:
        return web.json_response({"ok": False, "error": "state full"}, status=429)

    if mode == "increment":
        PyCodeMax_FolderFileMax._state[uid] = (idx - 1) % n
    elif mode == "decrement":
        PyCodeMax_FolderFileMax._state[uid] = (idx + 1) % n
    else:
        PyCodeMax_FolderFileMax._state[uid] = idx
    return web.json_response({"ok": True, "stored": PyCodeMax_FolderFileMax._state[uid]})

@PromptServer.instance.routes.get("/folder_file_max/list")
async def http_list(request):
    q = request.rel_url.query
    directory = q.get("directory", "")
    root_param = q.get("root", "")
    root_abs = os.path.abspath(os.path.expanduser(root_param)) if root_param else ""
    exts_q = q.get("exts", "")
    regex = q.get("regex", "")
    regex_mode = q.get("regex_mode", "include")
    regex_ic = q.get("regex_ic", "true").lower() in ("1","true","yes")
    sort_by = q.get("sort_by", "name")
    descending = q.get("descending", "false").lower() in ("1","true","yes")

    if root_abs and root_abs not in _ALLOWED_ROOT_PATHS:
        return web.json_response({"error": "root forbidden"}, status=403)

    directory_abs = os.path.abspath(os.path.expanduser(directory))
    if not os.path.isdir(directory_abs):
        return web.json_response({"error": "Directory not found.", "current_directory": directory_abs}, status=404)

    if not _is_safe_path(directory_abs, root_constraint=root_abs):
        return web.json_response({"error": f"Chemin hors de la racine autorisée ({root_abs})"}, status=403)

    cfg = _load_cfg()
    cfg["last_path"] = directory_abs
    cfg["last_root"] = root_abs
    _save_cfg(cfg)

    dirs = []
    try:
        for name in os.listdir(directory_abs):
            p = os.path.join(directory_abs, name)
            if os.path.isdir(p) and _is_safe_path(p, root_constraint=root_abs):
                dirs.append({"name": name, "path": p})
        dirs.sort(key=lambda d: (d["name"].lower(), d["path"]), reverse=descending)
    except Exception:
        pass

    extensions = _norm_exts(exts_q)
    files = _list_files_current_dir(directory_abs, extensions)
    files = _apply_regex(files, regex, regex_mode, regex_ic)
    files = _sort_files(files, sort_by, descending)

    visible = [{"name": f.name, "path": f.path, "type": classify_type(f.path), "ext": os.path.splitext(f.path)[1].lower()} for f in files]

    if directory_abs == root_abs:
        parent = None
    else:
        candidate = os.path.dirname(directory_abs)
        parent = candidate if candidate and _is_safe_path(candidate, root_constraint=root_abs) else None

    # prefetch thumbs en arrière-plan pour les 30 premiers
    try:
        for f in files[:30]:
            if classify_type(f.path) == "image":
                key = _thumb_key(f.path)
                dst = _thumb_path(key)
                if not os.path.exists(dst):
                    asyncio.create_task(_make_thumb(f.path, dst))
    except Exception:
        pass

    return web.json_response({
        "current_directory": directory_abs,
        "parent_directory": parent,
        "current_root": root_abs,
        "dirs": dirs,
        "files": visible,
        "total_count": len(files),
    })

@PromptServer.instance.routes.get("/folder_file_max/resolve_index")
async def http_resolve_index(request):
    q = request.rel_url.query
    directory = q.get("directory", "")
    root_param = q.get("root", "")
    root_abs = os.path.abspath(os.path.expanduser(root_param)) if root_param else ""
    if root_abs and root_abs not in _ALLOWED_ROOT_PATHS:
        return web.json_response({"error": "forbidden", "index": -1, "count": 0}, status=403)
    if not _is_safe_path(directory, root_constraint=root_abs):
        return web.json_response({"error": "forbidden", "index": -1, "count": 0}, status=403)
    tgt = os.path.abspath(q.get("path", ""))
    if tgt and not _is_safe_path(tgt, root_constraint=root_abs):
        return web.json_response({"error": "forbidden", "index": -1, "count": 0}, status=403)
    files = _sort_files(_apply_regex(_list_files_current_dir(directory, _norm_exts(q.get("exts", ""))), q.get("regex", ""), q.get("regex_mode", "include"), q.get("regex_ic", "true").lower() in ("1", "true")), q.get("sort_by", "name"), q.get("descending", "false").lower() in ("1", "true"))
    
    idx = next((i for i, f in enumerate(files) if os.path.abspath(f.path) == tgt), -1)
    return web.json_response({"index": idx, "count": len(files)})

@PromptServer.instance.routes.get("/folder_file_max/get_last_path")
async def http_get_last_path(request):
    cfg = _load_cfg()
    last_path = cfg.get("last_path", "")
    last_root = cfg.get("last_root", "")
    if last_root and last_root not in _ALLOWED_ROOT_PATHS:
        last_root = ""
        last_path = ""
    return web.json_response({"last_path": last_path, "last_root": last_root})

@PromptServer.instance.routes.get("/folder_file_max/thumbnail")
async def http_thumbnail(request):
    filepath = request.query.get("filepath", "")
    size = int(request.query.get("size", "320"))
    size = max(64, min(size, 512))
    if not filepath or not _is_safe_path(filepath) or not _safe_ext(filepath):
        return web.Response(status=403)
    if not os.path.isfile(filepath):
        return web.Response(status=404)
    if classify_type(filepath) != "image":
        return web.Response(status=415)

    key = _thumb_key(filepath) + f"_{size}"
    cache_file = _thumb_path(key)

    if not os.path.exists(cache_file) or os.path.getmtime(cache_file) < os.path.getmtime(filepath):
        try:
            await _make_thumb(filepath, cache_file, size=size)
        except Exception as e:
            print(f"[FolderFileMax] thumb error: {e}")
            return web.Response(status=500)

    return web.FileResponse(cache_file, headers={"Cache-Control": "public, max-age=86400", "Content-Type": "image/webp"})

@PromptServer.instance.routes.get("/folder_file_max/view")
async def http_view(request):
    filepath = request.query.get("filepath", "")
    if not filepath or not _is_safe_path(filepath) or not _safe_ext(filepath):
        return web.Response(status=403)
    if not os.path.isfile(filepath):
        return web.Response(status=404)
    return web.FileResponse(filepath)

# ---------------------------------------------------------------------------
# Route open_explorer SUPPRIMÉE pour raisons de sécurité.
# ---------------------------------------------------------------------------

# --- COMFYUI NODE ---
class PyCodeMax_FolderFileMax:
    _state = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory": ("STRING", {"default": "input"}),
                "extensions": ("STRING", {"default": ""}),
                "name_regex": ("STRING", {"default": ""}),
                "regex_mode": (["include", "exclude"], {"default": "include"}),
                "regex_ignore_case": ("BOOLEAN", {"default": True}),
                "sort_by": (["name", "mtime", "size"], {"default": "name"}),
                "descending": ("BOOLEAN", {"default": False}),
                "seed_mode": (["manual", "fixed", "increment", "decrement", "randomize"], {"default": "manual"}),
                "index": ("INT", {"default": 0, "min": 0, "max": 1_000_000_000}),
                "load_image": ("BOOLEAN", {"default": False}),
                "image_mode": (["RGB", "RGBA", "preview 512px"], {"default": "RGB"}),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "IMAGE", "INT",)
    RETURN_NAMES = ("file_path", "filename", "dir_used", "files_json", "file_info", "IMAGE", "index_out",)
    FUNCTION = "pick"
    CATEGORY = "Orion4D_MetaNode/Loaders"
    OUTPUT_NODE = False

    @classmethod
    def IS_CHANGED(cls, seed_mode, index, load_image, image_mode, **kwargs):
        sm = (seed_mode or "manual").lower()
        if sm in ("increment", "decrement", "randomize"):
            # Retourne un timestamp pour forcer la réévaluation à chaque run
            # float('nan') peut être optimisé par certaines versions de ComfyUI
            return time.time()
        # Pour les modes statiques, on hash les paramètres qui affectent la sortie
        return f"{index}_{load_image}_{image_mode}_{seed_mode}" 

    def pick(self, directory, extensions, name_regex, regex_mode, regex_ignore_case, sort_by, descending, seed_mode, index, load_image=False, image_mode="RGB", unique_id=None):
        dir_used = os.path.abspath(os.path.expanduser(str(directory))).strip('"')
        empty_tensor = torch.zeros((1, 1, 1, 3), dtype=torch.float32)

        if not _is_safe_path(dir_used):
            print(f"[FolderFileMax] Chemin refusé (hors allow-list) : {dir_used}")
            return ("", "", dir_used, "[]", "{}", empty_tensor, 0)

        files = _sort_files(_apply_regex(_list_files_current_dir(directory, _norm_exts(extensions)), name_regex, regex_mode, regex_ignore_case), sort_by, descending)

        if not files:
            PyCodeMax_FolderFileMax._state.pop(str(unique_id), None)
            return ("", "", dir_used, "[]", "{}", empty_tensor, 0)

        n = len(files)
        sm = (seed_mode or "manual").lower()
        uid = str(unique_id) if unique_id else "default"

        if sm in ("manual", "fixed"):
            sel = max(0, min(int(index), n - 1))
            PyCodeMax_FolderFileMax._state[uid] = sel
        elif sm == "randomize":
            sel = random.randrange(n)
            PyCodeMax_FolderFileMax._state[uid] = sel
        elif sm == "increment":
            prev = PyCodeMax_FolderFileMax._state.get(uid, int(index))
            sel = (prev + 1) % n
            PyCodeMax_FolderFileMax._state[uid] = sel
        elif sm == "decrement":
            prev = PyCodeMax_FolderFileMax._state.get(uid, int(index))
            sel = (prev - 1) % n
            PyCodeMax_FolderFileMax._state[uid] = sel
        else:
            sel = max(0, min(int(index), n - 1))

        chosen = files[sel]
        info = _get_file_info(chosen.path)
        
        # CHARGEMENT CONDITIONNEL DE L'IMAGE
        image_tensor = empty_tensor
        if load_image and info["type"] == "image":
            try:
                with Image.open(chosen.path) as img:
                    img = ImageOps.exif_transpose(img)
                    if image_mode == "preview 512px":
                        img.thumbnail((512, 512), Image.LANCZOS)
                    if img.mode == 'I':
                        img = img.point(lambda i: i * (1./256)).convert('L')
                    if img.mode not in ['RGB', 'RGBA', 'L']:
                        img = img.convert('RGB')
                    if image_mode == "RGBA" and img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    elif image_mode != "RGBA" and img.mode == 'RGBA':
                        img = img.convert('RGB')
                    np_img = np.array(img, dtype=np.float32) / 255.0
                    # garantir 3 ou 4 canaux
                    if np_img.ndim == 2:
                        np_img = np.stack([np_img]*3, axis=-1)
                    image_tensor = torch.from_numpy(np_img)[None,]
            except Exception as e:
                print(f"[Folder File Max] Erreur chargement image : {e}")

        files_json = json.dumps([{"name": f.name, "path": f.path, "size": f.size, "mtime": f.mtime} for f in files], ensure_ascii=False)
        return (chosen.path, chosen.name, dir_used, files_json, json.dumps(info, ensure_ascii=False), image_tensor, sel,)

# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {"PyCodeMax_FolderFileMax": PyCodeMax_FolderFileMax}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_FolderFileMax": "📂 Folder File Max"}
# --- END OF FILE Folder_file_max.py ---
