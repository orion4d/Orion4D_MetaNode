# --- START OF FILE PyCodeMax.py ---

import os
import math
import json
import hashlib
import threading
import traceback
import io
import time
from contextlib import redirect_stdout

import torch
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Dossier des scripts .py externes
# ---------------------------------------------------------------------------
PY_SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pyscripts")
if not os.path.exists(PY_SCRIPTS_DIR):
    os.makedirs(PY_SCRIPTS_DIR)

# ---------------------------------------------------------------------------
# Gestion de la Sécurité (Mode Développeur)
# ---------------------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
DEFAULT_CONFIG = {"developer_mode": False}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[PyCodeMax] Erreur de lecture du config.json : {e}")
        return DEFAULT_CONFIG

# Snapshot des scripts présents au démarrage — sert à refuser l'exécution
# de fichiers déposés après-coup (par exemple via une autre faille).
# Un utilisateur qui veut ajouter un script doit redémarrer ComfyUI.
_INITIAL_SCRIPTS = set()
try:
    if os.path.isdir(PY_SCRIPTS_DIR):
        _INITIAL_SCRIPTS = {
            f for f in os.listdir(PY_SCRIPTS_DIR) if f.endswith(".py")
        }
except Exception:
    pass

# Warning visible au chargement si developer_mode est actif
_startup_cfg = load_config()
if _startup_cfg.get("developer_mode", False):
    print("\n\033[33m" + "═" * 68)
    print("⚠️  [PyCodeMax] DEVELOPER MODE ACTIF")
    print("   L'exécution de code Python arbitraire via 'text_input' est")
    print("   autorisée. N'exécutez JAMAIS un workflow partagé dont vous ne")
    print("   comprenez pas chaque node PyCodeMax avant de le lancer.")
    print("   Pour désactiver : config.json → \"developer_mode\": false")
    print("═" * 68 + "\033[0m\n")

class PyCodeMax:
    # SHARED_STATE indexé par unique_id du noeud (persistant dans l'interface)
    # Plafonné pour éviter l'accumulation après suppression de nodes.
    from collections import OrderedDict as _OD
    SHARED_STATE: "_OD[str, dict]" = _OD()
    _STATE_MAX_ENTRIES = 128

    @classmethod
    def _state_touch(cls, key):
        """Accès LRU : marque la clé comme récente et évince si plafond atteint."""
        if key in cls.SHARED_STATE:
            cls.SHARED_STATE.move_to_end(key)
        while len(cls.SHARED_STATE) > cls._STATE_MAX_ENTRIES:
            evicted, _ = cls.SHARED_STATE.popitem(last=False)
            print(f"[PyCodeMax] Éviction LRU du STATE '{evicted}'")

    INPUT_CONFIG = [
        ("txt_in",   "STRING",      4, {"forceInput": True}),
        ("int_in",   "INT",         2, {"forceInput": True, "default": 0}),
        ("float_in", "FLOAT",       2, {"forceInput": True, "default": 0.0}),
        ("img_in",   "IMAGE",       2, {}),
        ("mask_in",  "MASK",        1, {}),
        ("latent_in","LATENT",      1, {}),
        ("positive", "CONDITIONING",1, {}),
        ("negative", "CONDITIONING",1, {}),
        ("model",    "MODEL",       1, {}),
        ("clip",     "CLIP",        1, {}),
        ("vae",      "VAE",         1, {}),
        ("audio_in", "*",           1, {}),
        ("video_in", "*",           1, {}),
        ("custom_in","*",           2, {}),
    ]

    OUTPUT_CONFIG = [
        ("txt_out",   "STRING",      4),
        ("int_out",   "INT",         2),
        ("float_out", "FLOAT",       2),
        ("img_out",   "IMAGE",       2),
        ("mask_out",  "MASK",        1),
        ("latent_out","LATENT",      1),
        ("positive",  "CONDITIONING",1),
        ("negative",  "CONDITIONING",1),
        ("model",     "MODEL",       1),
        ("clip",      "CLIP",        1),
        ("vae",       "VAE",         1),
        ("audio_out", "*",           1),
        ("video_out", "*",           1),
        ("custom_out","*",           2),
    ]

    RETURN_TYPES = []
    RETURN_NAMES = []
    for _prefix, _ctype, _count in OUTPUT_CONFIG:
        if _count == 1:
            RETURN_NAMES.append(_prefix)
            RETURN_TYPES.append(_ctype)
        else:
            for _i in range(1, _count + 1):
                RETURN_NAMES.append(f"{_prefix}_{_i}")
                RETURN_TYPES.append(_ctype)
    RETURN_TYPES += ("STRING",)
    RETURN_NAMES += ("Console",)
    RETURN_TYPES = tuple(RETURN_TYPES)
    RETURN_NAMES = tuple(RETURN_NAMES)

    FUNCTION = "execute_code"
    CATEGORY = "Orion4D_MetaNode/Brain"

    # ------------------------------------------------------------------
    # Cache intelligent : On laisse ComfyUI tracker les variables dynamiques 
    # (Tensors, INT, float) et on ne gère ici que le cas du Fichier Externe.
    # ------------------------------------------------------------------
    @classmethod
    def IS_CHANGED(cls, source, code, script_file, clear_state=False, **kwargs):
        # Si on est en mode "file", on invalide le cache SEULEMENT SI 
        # le fichier a été modifié sur le disque dur.
        if source == 'file' and script_file != "None":
            filepath = os.path.join(PY_SCRIPTS_DIR, script_file)
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
        
        # Pour les autres modes (text_input), on renvoie une constante ("").
        # ComfyUI va alors vérifier naturellement si une entrée a changé 
        # (ex: Seed fixé vs Seed random, Image différente, texte modifié).
        return ""

    def __init__(self):
        # Fallback au cas où l'unique_id n'est pas transmis
        self.instance_id = str(id(self))

    @classmethod
    def INPUT_TYPES(cls):
        script_files = ["None"] + [
            f for f in os.listdir(PY_SCRIPTS_DIR) if f.endswith(".py")
        ]
        inputs = {
            "required": {
                "source":      (["text_input", "file"],),
                "code":        ("STRING", {
                    "multiline": True,
                    "default": '# Your Python code is here, important: enable developer mode in config.json and set it to "true"\n',
                }),
                "script_file": (script_files,),
                "timeout_sec": ("INT", {
                    "default": 120,
                    "min": 5,
                    "max": 600,
                    "step": 5,
                    "display": "slider",
                }),
                "clear_state": ("BOOLEAN", {"default": False, "label_on": "Yes", "label_off": "No"}),
            },
            "optional": {},
            # Demande à ComfyUI de nous fournir l'ID constant du noeud
            "hidden": {"unique_id": "UNIQUE_ID"} 
        }
        for prefix, comfy_type, count, opts in cls.INPUT_CONFIG:
            if count == 1:
                inputs["optional"][prefix] = (comfy_type, opts)
            else:
                for i in range(1, count + 1):
                    inputs["optional"][f"{prefix}_{i}"] = (comfy_type, opts)
        inputs["optional"]["trigger"] = ("*",)
        return inputs

    # ------------------------------------------------------------------
    # Conversion PIL ↔ Tensor  (RGB et RGBA préservés)
    # ------------------------------------------------------------------
    def _tensor_to_pil(self, tensor):
        if tensor is None:
            return None
        images = []
        for t in tensor:
            arr = np.clip(255.0 * t.cpu().numpy(), 0, 255).astype(np.uint8)
            mode = 'RGBA' if (arr.ndim == 3 and arr.shape[2] == 4) else 'RGB'
            images.append(Image.fromarray(arr, mode=mode))
        # Renvoie toujours une liste
        return images 

    def _pil_to_tensor(self, pil_data):
        if pil_data is None:
            return None
        if not isinstance(pil_data, list):
            pil_data = [pil_data]
        tensors = []
        for img in pil_data:
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA' if 'A' in img.mode else 'RGB')
            tensors.append(torch.from_numpy(
                np.array(img).astype(np.float32) / 255.0
            ))
        return torch.stack(tensors)

    # ------------------------------------------------------------------
    # Exécution avec timeout (protection contre les boucles infinies)
    # ------------------------------------------------------------------
    def _run_with_timeout(self, user_code, execution_scope, stdout_capture, timeout=30):
        exception_holder = []

        def target():
            try:
                with redirect_stdout(stdout_capture):
                    exec(user_code, execution_scope)
            except Exception:
                exception_holder.append(traceback.format_exc())

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            stdout_capture.write(
                f"\n--- TIMEOUT ({timeout}s) : exécution abandonnée ---\n"
                "Vérifiez votre code pour une boucle infinie.\n"
            )
            return False

        if exception_holder:
            stdout_capture.write("\n--- EXECUTION FAILED ---\n")
            stdout_capture.write(exception_holder[0])
            print("\n--- EXECUTION FAILED IN PYCODEMAX ---")
            print(exception_holder[0])

        return True

    # ------------------------------------------------------------------
    # Point d'entrée principal
    # ------------------------------------------------------------------
    def execute_code(self, source, code, script_file, timeout_sec=120,
                     clear_state=False, trigger=None, unique_id=None, **kwargs):

        config = load_config()

        # --- VÉRIFICATION DE SÉCURITÉ ---
        if source == 'text_input' and not config.get("developer_mode", False):
            error_msg = (
                "SÉCURITÉ: L'exécution via 'text_input' est bloquée.\n"
                "Pour éviter l'exécution de code malveillant issu de workflows partagés, "
                "le mode texte est désactivé par défaut.\n"
                "Action requise : Ouvrez le fichier config.json dans le dossier du custom node "
                "et passez 'developer_mode' à true."
            )
            print(f"\n[PyCodeMax] 🚨 {error_msg}\n")
            raise RuntimeError(error_msg)

        console_lines = []

        # Résolution du code source
        if source == 'text_input':
            user_code = code
        elif source == 'file' and script_file != "None":
            # SÉCURITÉ : refuser tout script qui n'était pas présent au démarrage
            # sauf si developer_mode est actif. Empêche l'exécution d'un fichier
            # déposé après-coup par un workflow partagé ou une autre faille.
            if script_file not in _INITIAL_SCRIPTS and not config.get("developer_mode", False):
                error_msg = (
                    f"SÉCURITÉ: Le script '{script_file}' n'existait pas au démarrage.\n"
                    "Pour exécuter de nouveaux scripts, redémarrez ComfyUI, ou activez "
                    "developer_mode dans config.json."
                )
                print(f"\n[PyCodeMax] 🚨 {error_msg}\n")
                raise RuntimeError(error_msg)

            filepath = os.path.join(PY_SCRIPTS_DIR, script_file)
            # Anti path-traversal : le fichier résolu doit rester sous PY_SCRIPTS_DIR
            filepath_abs = os.path.abspath(filepath)
            if not filepath_abs.startswith(os.path.abspath(PY_SCRIPTS_DIR) + os.sep):
                raise RuntimeError(f"SÉCURITÉ: chemin refusé: {script_file}")
            if os.path.exists(filepath_abs):
                with open(filepath_abs, 'r', encoding='utf-8') as f:
                    user_code = f.read()
            else:
                empty = tuple(None for _ in self.RETURN_NAMES[:-1])
                return (*empty, f"ERROR: File not found: {filepath_abs}")
        else:
            user_code = ""

        # --- Auto-extraction de la documentation du script ---
        if source == 'file' and user_code:
            doc_lines = []
            for line in user_code.split('\n'):
                if line.startswith('#'):
                    doc_lines.append(line)
                elif not line.strip(): 
                    continue
                else:
                    break 
            
            if doc_lines:
                console_lines.append("=== 📖 DOCUMENTATION DU SCRIPT ===")
                console_lines.extend(doc_lines)
                console_lines.append("==================================")
                console_lines.append("")

        # Construction du dict IN
        IN = {}
        for key, value in kwargs.items():
            IN[key] = self._tensor_to_pil(value) if key.startswith('img_in') else value

        # Auto-doc des inputs dans la console
        console_lines.append("=== Inputs connectés ===")
        if IN:
            for k, v in IN.items():
                t = type(v).__name__
                if isinstance(v, list):
                    extra = f" length={len(v)}"
                else:
                    extra = f" size={v.size}" if hasattr(v, 'size') and not callable(v.size) else ""
                console_lines.append(f"  {k}: {t}{extra}")
        else:
            console_lines.append("  (aucun)")
        console_lines.append("")

        OUT = {}

        # --- Gestion stable du STATE basée sur le noeud physique ---
        state_key = unique_id if unique_id is not None else self.instance_id
        if state_key not in PyCodeMax.SHARED_STATE or clear_state:
            if clear_state:
                console_lines.append("🧹 STATE réinitialisé (clear_state = True)\n")
            PyCodeMax.SHARED_STATE[state_key] = {}
        PyCodeMax._state_touch(state_key)

        execution_scope = {
            'IN':    IN,
            'OUT':   OUT,
            'STATE': PyCodeMax.SHARED_STATE[state_key],
            'torch': torch,
            'np':    np,
            'Image': Image,
            'math':  math,
            'json':  json,
            'os':    os,
            'time':  time,
        }

        stdout_capture = io.StringIO()
        t_start = time.perf_counter()

        self._run_with_timeout(user_code, execution_scope, stdout_capture, timeout=timeout_sec)

        elapsed = time.perf_counter() - t_start

        # Warnings sur les sorties non renseignées
        output_names = self.RETURN_NAMES[:-1]
        missing = []
        for name in output_names:
            if name.startswith('txt_out') and name not in OUT:
                pass 
            elif name.startswith(('img_out', 'mask_out', 'latent_out')) and name in OUT and OUT[name] is None:
                missing.append(name)
        if missing:
            console_lines.append(f"⚠ Sorties à None : {', '.join(missing)}")

        # Entête Console
        header = (
            f"[PyCodeMax | {elapsed * 1000:.1f} ms]\n"
            + "─" * 40 + "\n"
            + "\n".join(console_lines) + "\n"
        )
        final_stdout = header + stdout_capture.getvalue()

        # Construction du tuple de retour — robuste aux mauvais types user
        results = []
        conv_errors = []
        for name in output_names:
            value = OUT.get(name)
            try:
                if name.startswith('txt_out'):
                    results.append(str(value) if value is not None else "")
                elif name.startswith('int_out'):
                    results.append(int(value) if value is not None else 0)
                elif name.startswith('float_out'):
                    results.append(float(value) if value is not None else 0.0)
                elif name.startswith('img_out'):
                    results.append(self._pil_to_tensor(value))
                else:
                    results.append(value)
            except (TypeError, ValueError) as e:
                conv_errors.append(f"  {name}: {type(value).__name__} → {e}")
                # Fallback safe
                if name.startswith('int_out'):
                    results.append(0)
                elif name.startswith('float_out'):
                    results.append(0.0)
                elif name.startswith('txt_out'):
                    results.append("")
                else:
                    results.append(None)

        if conv_errors:
            final_stdout += "\n⚠ Erreurs de conversion des sorties :\n" + "\n".join(conv_errors)

        results.append(final_stdout)
        return tuple(results)


NODE_CLASS_MAPPINGS = {"PyCodeMax": PyCodeMax}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax": "PyCode Max"}

# --- END OF FILE PyCodeMax.py ---