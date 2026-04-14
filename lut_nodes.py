# --- START OF FILE lut_nodes.py ---
# LUT nodes for Orion4D_MetaNode pack  v7
#
# LUTGenerator :
#   • Nouveau widget "save_lut" (BOOLEAN) — si False, génère la LUT en mémoire
#     sans écrire sur disque. lut_path retourne "" dans ce cas.
#
# LUTManager :
#   • Images de calibration dans lut_files/images_calibration/
#   • Route /orion4d/lut/calibration_images → liste + b64 de chaque image
#   • image_base.png reste le défaut si présente dans lut_files/

import numpy as np
import torch
import cv2
import os
import base64
from pathlib import Path
from typing import Optional
from PIL import Image as PILImage
from server import PromptServer  # type: ignore
from aiohttp import web
from io import BytesIO
import time

try:
    from scipy.interpolate import griddata
    from scipy.spatial import cKDTree
    _SCIPY = True
except ImportError:
    _SCIPY = False
    print("[LUTNodes] scipy non disponible")

try:
    from scipy.ndimage import gaussian_filter
    _GAUSSIAN = True
except ImportError:
    _GAUSSIAN = False

# ---------------------------------------------------------------------------
# Répertoires
# ---------------------------------------------------------------------------
NODE_DIR      = os.path.dirname(os.path.abspath(__file__))
LUT_DIR       = os.path.join(NODE_DIR, "lut_files")
CALIB_DIR     = os.path.join(LUT_DIR, "images_calibration")   # nouveau
BASE_IMG_NAME = "image_base"
os.makedirs(LUT_DIR,   exist_ok=True)
os.makedirs(CALIB_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Limites & sécurité pour les routes HTTP
# ---------------------------------------------------------------------------
_LUT_DIR_ABS      = os.path.abspath(LUT_DIR)
MAX_B64_PAYLOAD   = 20 * 1024 * 1024   # 20 MB
MAX_IMAGE_PIXELS  = 50_000_000         # 50 Mpx

def _lut_path_is_safe(path: str) -> bool:
    """Accepte uniquement des .cube sous LUT_DIR (pas d'échappement ..)."""
    if not path:
        return False
    try:
        abs_p = os.path.abspath(os.path.expanduser(str(path)))
    except Exception:
        return False
    if not abs_p.lower().endswith(".cube"):
        return False
    return abs_p == _LUT_DIR_ABS or abs_p.startswith(_LUT_DIR_ABS + os.sep)

def _decode_b64_image_lut(b64: str):
    if not b64 or len(b64) > MAX_B64_PAYLOAD:
        raise ValueError(f"Payload trop volumineux (> {MAX_B64_PAYLOAD // (1024*1024)} MB)")
    try:
        raw = base64.b64decode(b64, validate=False)
    except Exception as e:
        raise ValueError(f"Base64 invalide: {e}")
    img = PILImage.open(BytesIO(raw))
    w, h = img.size
    if w * h > MAX_IMAGE_PIXELS:
        raise ValueError(f"Image trop grande: {w}x{h}")
    return img.convert("RGB")

IMG_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"]


def _find_base_image() -> Optional[str]:
    """image_base.png dans lut_files/ — fallback par défaut."""
    for ext in IMG_EXTS:
        p = os.path.join(LUT_DIR, BASE_IMG_NAME + ext)
        if os.path.exists(p):
            return p
    return None


def _image_to_b64(path: str) -> str:
    """Pleine résolution PNG base64."""
    try:
        img = PILImage.open(path).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def _list_calib_images() -> list:
    """
    Liste les images dans images_calibration/.
    Retourne [{"name": stem, "b64": ...}, ...]
    L'image image_base.png de lut_files/ est ajoutée en tête si elle existe.
    """
    results = []

    # Défaut : image_base depuis lut_files/
    base_path = _find_base_image()
    if base_path:
        b64 = _image_to_b64(base_path)
        if b64:
            results.append({
                "name":    BASE_IMG_NAME,   # "image_base"
                "b64":     b64,
                "default": True,
            })

    # Images dans images_calibration/
    if os.path.isdir(CALIB_DIR):
        for fname in sorted(os.listdir(CALIB_DIR)):
            if Path(fname).suffix.lower() in IMG_EXTS:
                stem = Path(fname).stem
                b64  = _image_to_b64(os.path.join(CALIB_DIR, fname))
                if b64:
                    results.append({
                        "name":    stem,
                        "b64":     b64,
                        "default": False,
                    })
    return results


def _list_presets():
    names = ["None"]
    if os.path.isdir(LUT_DIR):
        names += sorted(
            Path(f).stem for f in os.listdir(LUT_DIR)
            if f.lower().endswith(".cube")
        )
    return names


def _load_image_any(path: str) -> Optional[np.ndarray]:
    path = path.strip().strip('"').strip("'")
    if not path or not os.path.exists(path):
        return None
    try:
        return np.array(PILImage.open(path).convert("RGB"), dtype=np.float32) / 255.0
    except Exception as e:
        print(f"[LUTGenerator] Erreur chargement {path}: {e}")
        return None


def _np_to_tensor(arr: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(arr).unsqueeze(0)


# ---------------------------------------------------------------------------
# Chargement .cube
# ---------------------------------------------------------------------------

def load_cube_file(file_path: str, table_order: str = "BGR") -> Optional[np.ndarray]:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        lut_size = 33; domain_min = [0.,0.,0.]; domain_max = [1.,1.,1.]; lut_data = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            if line.startswith("LUT_3D_SIZE"):  lut_size   = int(line.split()[-1]); continue
            if line.startswith("DOMAIN_MIN"):   domain_min = [float(x) for x in line.split()[1:4]]; continue
            if line.startswith("DOMAIN_MAX"):   domain_max = [float(x) for x in line.split()[1:4]]; continue
            parts = line.split()
            if len(parts) == 3:
                try:
                    r, g, b = map(float, parts)
                    lut_data.append([b, g, r] if table_order == "BGR" else [r, g, b])
                except ValueError:
                    pass
        expected = lut_size ** 3
        if len(lut_data) != expected:
            print(f"[LUT] Taille incorrecte: attendu {expected}, reçu {len(lut_data)}")
            return None
        arr = np.array(lut_data, dtype=np.float32)
        d_min = np.array(domain_min, dtype=np.float32); d_max = np.array(domain_max, dtype=np.float32)
        d_rng = d_max - d_min
        if not np.allclose(d_min, 0) or not np.allclose(d_max, 1):
            arr = (arr - d_min) / np.where(d_rng != 0, d_rng, 1)
        return np.clip(arr, 0., 1.).reshape(lut_size, lut_size, lut_size, 3)
    except Exception as e:
        print(f"[LUT] Erreur chargement {file_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------

def trilinear_apply(lut_3d: np.ndarray, img_np: np.ndarray) -> np.ndarray:
    n = lut_3d.shape[0]; img = np.clip(img_np, 0., 1.)
    r_idx=img[:,:,0]*(n-1); g_idx=img[:,:,1]*(n-1); b_idx=img[:,:,2]*(n-1)
    r0=np.floor(r_idx).astype(np.int32); r1=np.minimum(r0+1,n-1)
    g0=np.floor(g_idx).astype(np.int32); g1=np.minimum(g0+1,n-1)
    b0=np.floor(b_idx).astype(np.int32); b1=np.minimum(b0+1,n-1)
    dr=(r_idx-r0)[...,np.newaxis]; dg=(g_idx-g0)[...,np.newaxis]; db=(b_idx-b0)[...,np.newaxis]
    c000=lut_3d[r0,g0,b0]; c100=lut_3d[r1,g0,b0]; c010=lut_3d[r0,g1,b0]; c110=lut_3d[r1,g1,b0]
    c001=lut_3d[r0,g0,b1]; c101=lut_3d[r1,g0,b1]; c011=lut_3d[r0,g1,b1]; c111=lut_3d[r1,g1,b1]
    c00=c000*(1-dr)+c100*dr; c01=c001*(1-dr)+c101*dr
    c10=c010*(1-dr)+c110*dr; c11=c011*(1-dr)+c111*dr
    c0=c00*(1-dg)+c10*dg;    c1=c01*(1-dg)+c11*dg
    return np.clip(c0*(1-db)+c1*db, 0., 1.)


def apply_lut_full(img_rgb: np.ndarray, lut_3d: np.ndarray,
                   intensity: float = 1.0, data_order: str = "BGR") -> np.ndarray:
    orig = img_rgb
    work = img_rgb[:,:,::-1].copy() if data_order == "BGR" else img_rgb
    result = trilinear_apply(lut_3d, work)
    if data_order == "BGR":
        result = result[:,:,::-1].copy()
    if intensity != 1.0:
        t = min(max(intensity, 0.), 1.)
        result = orig*(1-t) + result*t
    return np.clip(result, 0., 1.)


# ---------------------------------------------------------------------------
# Routes API
# ---------------------------------------------------------------------------

@PromptServer.instance.routes.get("/orion4d/lut/calibration_images")
async def _api_calib_images(request):
    """
    Retourne la liste des images de calibration disponibles.
    Réponse : { images: [ { name, b64, default }, ... ] }
    L'image image_base (lut_files/) est toujours en tête si elle existe.
    """
    return web.json_response({"images": _list_calib_images()})


@PromptServer.instance.routes.get("/orion4d/lut/list")
async def _api_lut_list(request):
    presets = []
    if os.path.isdir(LUT_DIR):
        for fname in sorted(os.listdir(LUT_DIR)):
            if fname.lower().endswith(".cube"):
                presets.append({"name": Path(fname).stem})
    return web.json_response({"presets": presets})


@PromptServer.instance.routes.get("/orion4d/lut/resolve")
async def _api_lut_resolve(request):
    name = request.rel_url.query.get("name", "").strip()
    # Refuser toute forme de traversal ou de chemin composé : on veut un nom
    # de preset simple (alphanum, tiret, underscore, point, espace).
    if name and "/" not in name and "\\" not in name and ".." not in name:
        p = os.path.join(LUT_DIR, f"{name}.cube")
        if _lut_path_is_safe(p) and os.path.exists(p):
            return web.json_response({"path": p})
    return web.json_response({"path": ""})


@PromptServer.instance.routes.post("/orion4d/lut/apply")
async def _api_apply_lut(request):
    try:
        data        = await request.json()
        b64         = data.get("base_data_b64", "")
        lut_path    = data.get("lut_path", "").strip().strip('"').strip("'")
        intensity   = float(data.get("intensity",   1.0))
        data_order  = data.get("data_order",  "BGR")
        table_order = data.get("table_order", "BGR")
        if not b64:
            return web.json_response({"error": "base_data_b64 manquant"}, status=400)
        # SÉCURITÉ : lut_path doit être sous LUT_DIR et finir par .cube
        if not _lut_path_is_safe(lut_path):
            return web.json_response(
                {"error": f"Chemin LUT refusé (doit être sous {_LUT_DIR_ABS})"},
                status=403,
            )
        if not os.path.exists(lut_path):
            return web.json_response({"error": f"Fichier introuvable: {lut_path}"}, status=404)
        try:
            pil_img = _decode_b64_image_lut(b64)
        except ValueError as e:
            return web.json_response({"error": str(e)}, status=400)
        img_np = np.array(pil_img, dtype=np.float32) / 255.0
        lut_3d = load_cube_file(lut_path, table_order)
        if lut_3d is None:
            return web.json_response({"error": "Échec chargement LUT"}, status=500)
        result  = apply_lut_full(img_np, lut_3d, intensity, data_order)
        out_pil = PILImage.fromarray((result * 255).astype(np.uint8))
        buf = BytesIO(); out_pil.save(buf, format="PNG")
        return web.json_response({"adjusted_image_data": base64.b64encode(buf.getvalue()).decode()})
    except Exception as e:
        import traceback; traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


# ============================================================================
#  NŒUD 1 : PyCodeMax_LUTGenerator  v3
# ============================================================================
class PyCodeMax_LUTGenerator:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_before":         ("IMAGE",),
                "lut_size":             ("INT",   {"default": 17, "min": 9,    "max": 65,    "step": 2}),
                "sample_count":         ("INT",   {"default": 5000, "min": 1000, "max": 50000, "step": 1000}),
                "processing_scale":     ("FLOAT", {"default": 0.5, "min": 0.1, "max": 1.0,   "step": 0.1}),
                "interpolation_method": (["linear", "nearest", "cubic"], {"default": "linear"}),
                "smoothing_factor":     ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0,   "step": 0.1}),
                "anchor_strength":      ("FLOAT", {"default": 0.15, "min": 0.0, "max": 1.0,  "step": 0.05}),
                # Si False : LUT calculée mais non sauvegardée sur disque
                # lut_path retourne "" — utile pour tester sans polluer lut_files/
                "save_lut":             ("BOOLEAN", {"default": True}),
                "export_format":        (["cube", "3dl", "csp"], {"default": "cube"}),
                "export_path":          ("STRING", {"default": "./lut_files", "multiline": False}),
                "lut_name":             ("STRING", {"default": "generated_lut", "multiline": False}),
            },
            "optional": {
                "image_after":          ("IMAGE",),
                "image_after_path":     ("STRING", {"default": "", "multiline": False, "forceInput": True}),
                "test_image":           ("IMAGE",),
            }
        }

    RETURN_TYPES  = ("IMAGE", "IMAGE", "STRING")
    RETURN_NAMES  = ("preview_image", "tested_image", "lut_path")
    FUNCTION      = "generate_lut"
    CATEGORY      = "Orion4D_MetaNode/LUT"

    def generate_lut(self, image_before, lut_size, sample_count, processing_scale,
                     interpolation_method, smoothing_factor, anchor_strength, save_lut,
                     export_format, export_path, lut_name,
                     image_after=None, image_after_path=None, test_image=None):

        print(f"🔧 [LUTGenerator] {lut_size}³ – {sample_count} échantillons" +
              (" (sans sauvegarde)" if not save_lut else ""))
        t0 = time.time()

        def to_np(t):
            return (t[0] if len(t.shape) == 4 else t).cpu().numpy().astype(np.float32)

        img_b = to_np(image_before)

        # ── Résolution image_after ────────────────────────────────────────────
        img_a = None
        if image_after_path:
            raw = image_after_path.strip().strip('"').strip("'")
            if raw:
                img_a = _load_image_any(raw)
                if img_a is not None:
                    print(f"  📂 image_after depuis : {raw}")
        if img_a is None and image_after is not None:
            img_a = to_np(image_after)
        if img_a is None:
            raise ValueError("[LUTGenerator] image_after manquante")

        # ── Alignement + redimensionnement ───────────────────────────────────
        if img_b.shape != img_a.shape:
            h, w = img_b.shape[:2]
            img_a = cv2.resize(img_a, (w, h), interpolation=cv2.INTER_LINEAR)
        if processing_scale < 1.0:
            h, w = img_b.shape[:2]
            nh, nw = max(1, int(h * processing_scale)), max(1, int(w * processing_scale))
            img_b = cv2.resize(img_b, (nw, nh), interpolation=cv2.INTER_LINEAR)
            img_a = cv2.resize(img_a, (nw, nh), interpolation=cv2.INTER_LINEAR)

        # ── Génération LUT ────────────────────────────────────────────────────
        lut_3d = self._build_lut(img_b, img_a, lut_size, sample_count,
                                  interpolation_method, smoothing_factor, anchor_strength)

        # ── Sauvegarde conditionnelle ─────────────────────────────────────────
        if save_lut:
            lut_path = self._export(lut_3d, export_format, export_path, lut_name, lut_size)
            print(f"✅ [LUTGenerator] {time.time()-t0:.2f}s → {lut_path}")
        else:
            lut_path = ""
            print(f"✅ [LUTGenerator] {time.time()-t0:.2f}s (non sauvegardée)")

        # ── Sorties ───────────────────────────────────────────────────────────
        preview   = self._make_preview(lut_3d)
        src       = to_np(test_image) if test_image is not None else to_np(image_before)
        tested_np = apply_lut_full(src, lut_3d, intensity=1.0, data_order="RGB")
        tested    = _np_to_tensor(tested_np.astype(np.float32))

        return (preview, tested, lut_path)

    # ── Construction LUT ──────────────────────────────────────────────────────
    def _build_lut(self, img_b, img_a, n, count, method, smooth, anchor_strength=0.15):
        h, w = img_b.shape[:2]
        if count >= h * w:
            src = img_b.reshape(-1, 3); tgt = img_a.reshape(-1, 3)
        else:
            idx = self._strat_sample(img_b, count)
            src = img_b.reshape(-1, 3)[idx]; tgt = img_a.reshape(-1, 3)[idx]

        # Points d'ancrage identity sur grille 5×5×5
        ac = np.linspace(0, 1, 5)
        ax, ay, az = np.meshgrid(ac, ac, ac, indexing="ij")
        anchors = np.column_stack([ax.ravel(), ay.ravel(), az.ravel()]).astype(np.float32)
        n_repeat = max(1, int(anchor_strength * count / 4)) if anchor_strength > 0 else 0
        if n_repeat > 0:
            anchors_rep = np.tile(anchors, (n_repeat, 1))
            src = np.vstack([src, anchors_rep]).astype(np.float32)
            tgt = np.vstack([tgt, anchors_rep]).astype(np.float32)

        print(f"  📊 {count} réels + {n_repeat}×{len(anchors)} anchors = {len(src)} pts")
        coords = np.linspace(0, 1, n)
        R, G, B = np.meshgrid(coords, coords, coords, indexing="ij")
        grid = np.column_stack([R.ravel(), G.ravel(), B.ravel()])
        return np.clip(self._interpolate(src, tgt, grid, method, smooth).reshape(n, n, n, 3), 0, 1)

    def _strat_sample(self, image, count):
        h, w = image.shape[:2]; total = h * w
        grid = max(1, int(np.sqrt(count / 10)))
        sh, sw = max(1, h // grid), max(1, w // grid)
        per = max(1, count // (grid * grid))
        rng = np.random.default_rng(); idx = []
        for i in range(0, h, sh):
            for j in range(0, w, sw):
                rh = min(sh, h-i); rw = min(sw, w-j); n_ = min(per, rh*rw)
                ri = rng.integers(i, min(i+rh, h), size=n_)
                rj = rng.integers(j, min(j+rw, w), size=n_)
                idx.extend((ri * w + rj).tolist())
        while len(idx) < count:
            idx.append(int(rng.integers(0, total)))
        return np.array(idx[:count])

    def _interpolate(self, src, tgt, grid, method, smooth):
        if not _SCIPY:
            from scipy.spatial import cKDTree as KD; _, ii = KD(src).query(grid, k=1)
            return tgt[ii].astype(np.float32)
        tree = cKDTree(src); used, uniq = set(), []
        for i in range(len(src)):
            if i not in used:
                nb = tree.query_ball_point(src[i], 1e-6); uniq.append(i); used.update(nb)
        if len(uniq) < len(src):
            src = src[np.array(uniq)]; tgt = tgt[np.array(uniq)]
        try:
            result = griddata(src, tgt, grid, method=method, fill_value=np.nan, rescale=True)
            nm = np.isnan(result).any(axis=1)
            if np.any(nm):
                result[nm] = griddata(src, tgt, grid[nm], method="nearest", rescale=True)
            if smooth > 0 and _GAUSSIAN:
                n_ = int(round(len(grid) ** (1/3))); vol = result.reshape(n_, n_, n_, 3)
                for c in range(3): vol[:,:,:,c] = gaussian_filter(vol[:,:,:,c], sigma=smooth*2)
                result = vol.reshape(-1, 3)
            return result.astype(np.float32)
        except Exception as e:
            print(f"  ❌ {e} – fallback nearest")
            return griddata(src, tgt, grid, method="nearest", rescale=True).astype(np.float32)

    # ── Export ────────────────────────────────────────────────────────────────
    def _export(self, lut_3d, fmt, path_str, name, n):
        p = Path(path_str.strip())
        if not p.is_absolute(): p = Path(NODE_DIR) / p
        p.mkdir(parents=True, exist_ok=True)
        ext = {"cube": ".cube", "3dl": ".3dl", "csp": ".csp"}[fmt]
        fp = p / f"{name}{ext}"
        getattr(self, f"_write_{fmt}")(lut_3d, fp, n)
        return str(fp)

    def _write_cube(self, lut, fp, n):
        with open(fp, "w") as f:
            f.write("# Generated by Orion4D_MetaNode LUT Generator\n")
            f.write(f"LUT_3D_SIZE {n}\nDOMAIN_MIN 0.0 0.0 0.0\nDOMAIN_MAX 1.0 1.0 1.0\n\n")
            for b in range(n):
                for g in range(n):
                    for r in range(n):
                        v = lut[r, g, b]; f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

    def _write_3dl(self, lut, fp, n):
        with open(fp, "w") as f:
            for b in range(n):
                for g in range(n):
                    for r in range(n):
                        v = (lut[r, g, b] * 4095).astype(int)
                        f.write(f"{v[0]} {v[1]} {v[2]}\n")

    def _write_csp(self, lut, fp, n):
        with open(fp, "w") as f:
            f.write(f"CSPLUTV100\n3D\n{n}\n")
            for r in range(n):
                for g in range(n):
                    for b in range(n):
                        v = lut[r, g, b]; f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

    def _make_preview(self, lut_3d):
        sz = 256
        X, Y = np.meshgrid(np.linspace(0, 1, sz), np.linspace(0, 1, sz))
        img  = np.stack([X, Y, (X + Y) / 2], axis=2).astype(np.float32)
        return _np_to_tensor(trilinear_apply(lut_3d, img))


# ============================================================================
#  NŒUD 2 : PyCodeMax_LUTManager  (inchangé côté Python)
# ============================================================================
class PyCodeMax_LUTManager:

    _cache: dict = {}

    @classmethod
    def _resolve(cls, lut_path: str, lut_preset: str) -> str:
        path = lut_path.strip().strip('"').strip("'")
        if path and os.path.exists(path): return path
        if lut_preset and lut_preset != "None":
            c = os.path.join(LUT_DIR, f"{lut_preset}.cube")
            if os.path.exists(c): return c
        return ""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image":       ("IMAGE",),
                "lut_path":    ("STRING", {"default": "", "multiline": False}),
                "lut_preset":  (_list_presets(), {"default": "None"}),
                "intensity":   ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.05}),
                "opacity":     ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.05}),
                "data_order":  (["BGR", "RGB"], {"default": "BGR"}),
                "table_order": (["BGR", "RGB"], {"default": "BGR"}),
            },
        }

    RETURN_TYPES  = ("IMAGE", "STRING")
    RETURN_NAMES  = ("image", "lut_path")
    FUNCTION      = "apply_lut"
    CATEGORY      = "Orion4D_MetaNode/LUT"

    @classmethod
    def IS_CHANGED(cls, image, lut_path, lut_preset, intensity, opacity, data_order, table_order):
        import hashlib; h = hashlib.md5()
        resolved = cls._resolve(lut_path, lut_preset)
        if resolved and os.path.exists(resolved):
            h.update(resolved.encode()); h.update(str(os.path.getmtime(resolved)).encode())
        for v in (intensity, opacity, data_order, table_order): h.update(str(v).encode())
        return h.hexdigest()

    def apply_lut(self, image, lut_path, lut_preset, intensity, opacity, data_order, table_order):
        resolved = self._resolve(lut_path, lut_preset)
        if len(image.shape) == 4:
            frames = [image[i].cpu().numpy().astype(np.float32) for i in range(image.shape[0])]
        else:
            frames = [image.cpu().numpy().astype(np.float32)]
        if not resolved:
            print("[LUTManager] Aucune LUT")
            return (torch.from_numpy(np.stack(frames, axis=0)), "No LUT applied")
        key = (resolved, table_order)
        if key not in self._cache:
            lut = load_cube_file(resolved, table_order)
            if lut is None:
                return (torch.from_numpy(np.stack(frames, axis=0)), "LUT loading failed")
            self._cache[key] = lut
            print(f"[LUTManager] ✅ {os.path.basename(resolved)}")
        lut_3d = self._cache[key]
        results = []
        for orig in frames:
            res = apply_lut_full(orig, lut_3d, intensity, data_order)
            if opacity < 1.0: res = orig * (1 - opacity) + res * opacity
            results.append(np.clip(res, 0., 1.))
        return (torch.from_numpy(np.stack(results, axis=0)), resolved)


# ============================================================================
#  ENREGISTREMENT
# ============================================================================
NODE_CLASS_MAPPINGS = {
    "PyCodeMax_LUTGenerator": PyCodeMax_LUTGenerator,
    "PyCodeMax_LUTManager":   PyCodeMax_LUTManager,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_LUTGenerator": "🎨 LUT Generator",
    "PyCodeMax_LUTManager":   "🎬 LUT Manager",
}

# --- END OF FILE lut_nodes.py ---
