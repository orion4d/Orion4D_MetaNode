# --- START OF FILE PyCodeMax.py ---

import os
import math
import json
import hashlib
import threading
import traceback
import io
import time
import base64
from contextlib import redirect_stdout

import torch
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Dépendances optionnelles pour les helpers LLM / GPU
# ---------------------------------------------------------------------------
# requests : présent par défaut dans ComfyUI (dépendance transitive).
try:
    import requests as _requests
    _REQUESTS_OK = True
except Exception:
    _requests = None
    _REQUESTS_OK = False

# pynvml (package PyPI : nvidia-ml-py) : optionnel, pour la lecture VRAM
# globale tous-processus (utile car Ollama tourne dans son propre process et
# n'est donc pas visible via torch.cuda.memory_allocated()).
#
# Installation utilisateur : pip install nvidia-ml-py
# Si absent, gpu["vram"]() renvoie {"available": False, ...}.
try:
    import pynvml as _pynvml
    _pynvml.nvmlInit()
    _NVML_OK = True
except Exception:
    _pynvml = None
    _NVML_OK = False

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

# Log de disponibilité des helpers optionnels (une seule fois au chargement)
if _NVML_OK:
    print("\033[34m[PyCodeMax]\033[0m pynvml détecté — gpu['vram']() disponible.")
else:
    print("\033[90m[PyCodeMax] pynvml absent — gpu['vram']() renverra {'available': False}. "
          "Pour l'activer : pip install nvidia-ml-py\033[0m")


# ===========================================================================
# Helpers LLM / GPU injectés dans execution_scope
# ---------------------------------------------------------------------------
# Conçus pour être appelés depuis un script user via :
#   llm["generate"](prompt, model="gemma4:e4b", ...)
#   llm["list"]()
#   llm["unload"](model)
#   gpu["vram"]()
#
# Choix de design :
# - requests est utilisé en direct plutôt que la lib `ollama` officielle
#   pour garder zéro dépendance supplémentaire et un accès raw aux réponses.
# - La session HTTP est persistée dans STATE (par-node) pour profiter du
#   keep-alive et éviter de recréer un socket à chaque exécution.
# - Les defaults de sampling suivent les recommandations officielles Gemma 4
#   (temperature=1.0, top_p=0.95, top_k=64). Override libre via options.
# - Le flag `think` active/désactive le mode reasoning de Gemma 4 en
#   injectant le token <|think|> au début du system prompt.
# ===========================================================================

OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"

def _build_llm_helpers(state_dict, default_timeout):
    """Construit le dict `llm` à injecter dans execution_scope.

    Args:
        state_dict: le STATE du node courant (pour y stocker la Session
                    requests persistante).
        default_timeout: timeout HTTP par défaut, aligné sur timeout_sec
                         du node pour éviter que la requête survive au node.
    """
    if not _REQUESTS_OK:
        def _no_requests(*_a, **_kw):
            return "[LLM ERROR] La librairie 'requests' est indisponible."
        return {
            "generate": _no_requests,
            "list":     _no_requests,
            "unload":   _no_requests,
            "chat":     _no_requests,
        }

    def _get_session():
        sess = state_dict.get("_ollama_session")
        if sess is None:
            sess = _requests.Session()
            state_dict["_ollama_session"] = sess
        return sess

    def generate(prompt, model="gemma4:e4b", system="", images=None,
                 think=False, stream=False, host=None, timeout=None,
                 **options):
        """Appelle POST /api/generate sur Ollama et renvoie la string de réponse.

        Args:
            prompt:    texte utilisateur.
            model:     nom du modèle Ollama (ex: "gemma4:e4b", "qwen2.5vl:7b").
            system:    prompt système (optionnel).
            images:    liste de PIL.Image OU liste de str base64 OU None.
                       Conversion PIL → base64 PNG automatique.
            think:     True pour activer le mode reasoning de Gemma 4
                       (ajoute <|think|> au début du system prompt).
            stream:    False = réponse complète en un bloc (par défaut).
                       True = renvoie un itérateur de chunks (avancé).
            host:      override de l'URL Ollama (défaut: 127.0.0.1:11434).
            timeout:   override du timeout HTTP (défaut: timeout_sec du node).
            **options: temperature, top_p, top_k, seed, num_ctx,
                       num_predict, etc. — passés tels quels à Ollama.

        Returns:
            str : la réponse du modèle (ou "[LLM ERROR] ..." en cas d'échec).
                  Si stream=True, renvoie un générateur de chunks string.
        """
        url = (host or OLLAMA_DEFAULT_URL).rstrip("/") + "/api/generate"
        to  = timeout if timeout is not None else default_timeout

        # Defaults Gemma 4 officiels (surchargeables via **options)
        opts = {
            "temperature": options.pop("temperature", 1.0),
            "top_p":       options.pop("top_p", 0.95),
            "top_k":       options.pop("top_k", 64),
        }
        opts.update(options)  # seed, num_ctx, num_predict, etc.

        # Mode thinking via injection du token <|think|> en tête du system
        sys_prompt = system or ""
        if think and not sys_prompt.startswith("<|think|>"):
            sys_prompt = "<|think|>" + sys_prompt

        payload = {
            "model":   model,
            "prompt":  prompt,
            "system":  sys_prompt,
            "stream":  bool(stream),
            "options": opts,
        }

        # Conversion éventuelle des images PIL → base64
        if images:
            if not isinstance(images, list):
                images = [images]
            b64_list = []
            for img in images:
                if isinstance(img, str):
                    b64_list.append(img)  # déjà en base64
                else:
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    b64_list.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
            payload["images"] = b64_list

        try:
            sess = _get_session()
            if stream:
                # Mode streaming : renvoie un générateur de chunks
                def _stream_iter():
                    with sess.post(url, json=payload, timeout=to, stream=True) as r:
                        r.raise_for_status()
                        for line in r.iter_lines():
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line.decode("utf-8"))
                                if "response" in chunk:
                                    yield chunk["response"]
                                if chunk.get("done"):
                                    break
                            except Exception:
                                continue
                return _stream_iter()
            else:
                r = sess.post(url, json=payload, timeout=to)
                r.raise_for_status()
                return r.json().get("response", "").strip()
        except Exception as e:
            return f"[LLM ERROR] {e}"

    def chat(messages, model="gemma4:e4b", think=False, stream=False,
             host=None, timeout=None, **options):
        """Appelle POST /api/chat (format conversationnel multi-tours).

        Args:
            messages: liste de dicts {"role": "user|assistant|system",
                                       "content": "...",
                                       "images": [...] (optionnel)}.
            Autres args : voir generate().

        Returns:
            str : le contenu du message assistant.
        """
        url = (host or OLLAMA_DEFAULT_URL).rstrip("/") + "/api/chat"
        to  = timeout if timeout is not None else default_timeout

        opts = {
            "temperature": options.pop("temperature", 1.0),
            "top_p":       options.pop("top_p", 0.95),
            "top_k":       options.pop("top_k", 64),
        }
        opts.update(options)

        # Si think=True et qu'il y a un message system, on préfixe
        msgs = [dict(m) for m in messages]  # shallow copy
        if think:
            has_system = any(m.get("role") == "system" for m in msgs)
            if has_system:
                for m in msgs:
                    if m.get("role") == "system" and not m.get("content", "").startswith("<|think|>"):
                        m["content"] = "<|think|>" + m.get("content", "")
                        break
            else:
                msgs.insert(0, {"role": "system", "content": "<|think|>"})

        payload = {
            "model":    model,
            "messages": msgs,
            "stream":   bool(stream),
            "options":  opts,
        }

        try:
            sess = _get_session()
            r = sess.post(url, json=payload, timeout=to)
            r.raise_for_status()
            data = r.json()
            return (data.get("message", {}) or {}).get("content", "").strip()
        except Exception as e:
            return f"[LLM ERROR] {e}"

    def list_models(host=None, timeout=10):
        """Renvoie la liste des modèles locaux (via GET /api/tags).

        Returns:
            list[dict] : chaque dict contient au minimum 'name' et 'size'.
                         En cas d'erreur, renvoie [].
        """
        url = (host or OLLAMA_DEFAULT_URL).rstrip("/") + "/api/tags"
        try:
            sess = _get_session()
            r = sess.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json().get("models", [])
        except Exception as e:
            print(f"[LLM ERROR] list: {e}")
            return []

    def unload(model, host=None, timeout=10):
        """Décharge un modèle de la VRAM (keep_alive=0).

        Utile avant une étape ComfyUI lourde pour libérer la VRAM.
        Returns True en cas de succès, False sinon.
        """
        url = (host or OLLAMA_DEFAULT_URL).rstrip("/") + "/api/generate"
        payload = {"model": model, "keep_alive": 0}
        try:
            sess = _get_session()
            r = sess.post(url, json=payload, timeout=timeout)
            r.raise_for_status()
            return True
        except Exception as e:
            print(f"[LLM ERROR] unload: {e}")
            return False

    def ps(host=None, timeout=10):
        """Liste les modèles actuellement chargés en VRAM (GET /api/ps)."""
        url = (host or OLLAMA_DEFAULT_URL).rstrip("/") + "/api/ps"
        try:
            sess = _get_session()
            r = sess.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json().get("models", [])
        except Exception as e:
            print(f"[LLM ERROR] ps: {e}")
            return []

    return {
        "generate": generate,
        "chat":     chat,
        "list":     list_models,
        "unload":   unload,
        "ps":       ps,
    }


def _build_gpu_helpers():
    """Construit le dict `gpu` à injecter dans execution_scope.

    Expose :
        gpu["vram"](device=0) -> dict avec {available, used_gb, free_gb,
                                             total_gb, percent_used}
                                 (used_gb mesure TOUS les process, y compris
                                  Ollama — contrairement à torch.cuda).
        gpu["torch_vram"]() -> dict avec la VRAM allouée par PyTorch
                               dans CE process uniquement.
        gpu["info"]() -> dict avec nom GPU, driver, etc.
    """

    def vram(device=0):
        """VRAM globale (tous processus) via NVML."""
        if not _NVML_OK:
            return {
                "available":   False,
                "reason":      "pynvml non installé (pip install nvidia-ml-py)",
                "used_gb":     0.0,
                "free_gb":     0.0,
                "total_gb":    0.0,
                "percent_used": 0.0,
            }
        try:
            h = _pynvml.nvmlDeviceGetHandleByIndex(device)
            info = _pynvml.nvmlDeviceGetMemoryInfo(h)
            total = info.total / 1e9
            used  = info.used / 1e9
            free  = info.free / 1e9
            return {
                "available":    True,
                "used_gb":      used,
                "free_gb":      free,
                "total_gb":     total,
                "percent_used": (info.used / info.total * 100.0) if info.total else 0.0,
            }
        except Exception as e:
            return {
                "available": False,
                "reason":    f"NVML error: {e}",
                "used_gb":   0.0, "free_gb": 0.0, "total_gb": 0.0,
                "percent_used": 0.0,
            }

    def torch_vram():
        """VRAM allouée par PyTorch dans CE process (pour debug ComfyUI)."""
        try:
            if torch.cuda.is_available():
                return {
                    "available":   True,
                    "allocated_gb": torch.cuda.memory_allocated() / 1e9,
                    "reserved_gb":  torch.cuda.memory_reserved() / 1e9,
                    "total_gb":     torch.cuda.get_device_properties(0).total_memory / 1e9,
                }
        except Exception as e:
            return {"available": False, "reason": str(e)}
        return {"available": False, "reason": "CUDA indisponible"}

    def info(device=0):
        """Infos statiques sur le GPU (nom, driver, compute capability)."""
        out = {"cuda_available": torch.cuda.is_available()}
        try:
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(device)
                out["name"] = props.name
                out["total_gb"] = props.total_memory / 1e9
                out["compute_capability"] = f"{props.major}.{props.minor}"
        except Exception:
            pass
        if _NVML_OK:
            try:
                h = _pynvml.nvmlDeviceGetHandleByIndex(device)
                drv = _pynvml.nvmlSystemGetDriverVersion()
                out["driver"] = drv if isinstance(drv, str) else drv.decode("utf-8", errors="replace")
                out["nvml"] = True
            except Exception:
                out["nvml"] = False
        else:
            out["nvml"] = False
        return out

    return {
        "vram":       vram,
        "torch_vram": torch_vram,
        "info":       info,
    }


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
                # À la réinitialisation, on ferme proprement la session HTTP
                # s'il y en avait une pour éviter de fuiter des sockets.
                old = PyCodeMax.SHARED_STATE.get(state_key, {})
                old_sess = old.get("_ollama_session") if isinstance(old, dict) else None
                if old_sess is not None:
                    try:
                        old_sess.close()
                    except Exception:
                        pass
                console_lines.append("🧹 STATE réinitialisé (clear_state = True)\n")
            PyCodeMax.SHARED_STATE[state_key] = {}
        PyCodeMax._state_touch(state_key)

        # Helpers LLM / GPU construits par-node (la session HTTP vit dans STATE,
        # les fonctions gpu sont stateless donc partageables mais on les
        # reconstruit pour la lisibilité).
        _state = PyCodeMax.SHARED_STATE[state_key]
        llm_helpers = _build_llm_helpers(_state, default_timeout=timeout_sec)
        gpu_helpers = _build_gpu_helpers()

        execution_scope = {
            # Core
            'IN':    IN,
            'OUT':   OUT,
            'STATE': _state,
            # Modules scientifiques
            'torch': torch,
            'np':    np,
            'Image': Image,
            'math':  math,
            'json':  json,
            'os':    os,
            'time':  time,
            # Nouveautés V2
            'llm':   llm_helpers,
            'gpu':   gpu_helpers,
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
