# --- START OF FILE variable_bus.py ---
# v3 : data_type + execution_phase + tick par variable.
from collections import OrderedDict

_ORION_BUS: "OrderedDict[str, tuple]" = OrderedDict()  # name -> (value, tick)
_BUS_MAX_ENTRIES = 64
_BUS_SEQ = 0

try:
    from comfy_execution.graph import ExecutionBlocker
    _HAS_BLOCKER = True
except ImportError:
    _HAS_BLOCKER = False


DATA_TYPES = [
    "*", "IMAGE", "LATENT", "MASK", "STRING", "INT", "FLOAT",
    "MODEL", "CONDITIONING", "CLIP", "VAE", "LIST",
]
EXECUTION_PHASES = ["1", "2", "3", "4", "5", "6", "7", "8"]


def _empty_cuda_cache():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _bus_set(name, value):
    global _BUS_SEQ
    if name in _ORION_BUS:
        old, _ = _ORION_BUS[name]
        _ORION_BUS.move_to_end(name)
        del old
        _empty_cuda_cache()
    _BUS_SEQ += 1
    _ORION_BUS[name] = (value, _BUS_SEQ)
    while len(_ORION_BUS) > _BUS_MAX_ENTRIES:
        k, _ = _ORION_BUS.popitem(last=False)
        print(f"🚌 [Bus] Éviction FIFO de '{k}'")
        _empty_cuda_cache()


def _bus_get_tick(name):
    entry = _ORION_BUS.get(name)
    return entry[1] if entry else 0


class PyCodeMax_BusSet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": ("*",),
                "variable_name": ("STRING", {"default": "my_var"}),
                "data_type": (DATA_TYPES, {"default": "*"}),
                "execution_phase": (EXECUTION_PHASES, {"default": "1"}),
            }
        }
    RETURN_TYPES = ("*", "INT")
    RETURN_NAMES = ("passthrough", "sync")
    FUNCTION = "bus_set"
    CATEGORY = "Orion4D_MetaNode/Bus"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def bus_set(self, input, variable_name, data_type, execution_phase):
        _bus_set(variable_name, input)
        tick = _bus_get_tick(variable_name)
        print(f"🚌 [Bus SET] '{variable_name}' ({data_type} phase {execution_phase}) "
              f"<= {type(input).__name__} (tick={tick})")
        return {"ui": {}, "result": (input, tick)}


class PyCodeMax_BusGet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "variable_name": ("STRING", {"default": "my_var"}),
                "data_type": (DATA_TYPES, {"default": "*"}),
                "execution_phase": (EXECUTION_PHASES, {"default": "1"}),
            },
            "optional": {
                "dependency": ("INT", {"forceInput": True}),
            }
        }
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "bus_get"
    CATEGORY = "Orion4D_MetaNode/Bus"

    @classmethod
    def IS_CHANGED(cls, variable_name, data_type, execution_phase, dependency=None, **kwargs):
        # `dependency` est le tick (sync) émis par le BusSet en amont. Comme BusSet
        # a IS_CHANGED=NaN, il tourne à chaque run et émet un tick neuf → cette
        # valeur change → BusGet se réinvalide ET ComfyUI sait qu'il doit attendre
        # le Set avant de tourner (ordre garanti par le lien dependency).
        # On inclut aussi variable_name/data_type/phase pour invalider sur changement
        # de widget côté Get.
        return (variable_name, data_type, execution_phase, dependency)

    def bus_get(self, variable_name, data_type, execution_phase, dependency=None):
        entry = _ORION_BUS.get(variable_name)
        if entry is None:
            print(f"⚠️ [Bus GET] '{variable_name}' introuvable")
            if _HAS_BLOCKER:
                return (ExecutionBlocker(f"[Variable Bus] '{variable_name}' non défini."),)
            raise ValueError(f"[Variable Bus] '{variable_name}' introuvable.")
        value, tick = entry
        _ORION_BUS.move_to_end(variable_name)
        print(f"🚌 [Bus GET] '{variable_name}' ({data_type} phase {execution_phase}) "
              f"=> {type(value).__name__} (tick={tick})")
        return (value,)


class PyCodeMax_BusClear:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "show_bus_links": ("BOOLEAN", {"default": False, "label_on": "visible", "label_off": "hidden"}),
                "clear_mode": (["none", "all", "single", "all_except"], {"default": "none"}),
                "variable_name": ("STRING", {"default": ""}),
            },
            "optional": {"trigger": ("*",)}
        }
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("done",)
    FUNCTION = "bus_clear"
    CATEGORY = "Orion4D_MetaNode/Bus"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def bus_clear(self, show_bus_links, clear_mode, variable_name, trigger=None):
        # show_bus_links est purement visuel (géré côté JS), pas de logique côté Python.
        before = len(_ORION_BUS)
        _do_clear(clear_mode, variable_name)
        after = len(_ORION_BUS)
        print(f"🧹 [Bus CLEAR] mode={clear_mode} — {before} → {after} (seq={_BUS_SEQ})")
        return {"ui": {}, "result": (after,)}


def _do_clear(mode, variable_name):
    """Logique de clear partagée entre le node et la route HTTP."""
    global _BUS_SEQ
    if mode == "none":
        return  # no-op : le BusClear sert juste de contrôleur visuel
    if mode == "all":
        _ORION_BUS.clear()
    elif mode == "single":
        _ORION_BUS.pop(variable_name, None)
    elif mode == "all_except":
        if variable_name in _ORION_BUS:
            kept = _ORION_BUS[variable_name]
            _ORION_BUS.clear()
            _ORION_BUS[variable_name] = kept
        else:
            _ORION_BUS.clear()
    _BUS_SEQ += 1
    _empty_cuda_cache()


# ──────────────────────────────────────────────────────────────
# Route HTTP : permet au bouton "Clear now" du JS de déclencher
# le clear immédiatement, sans avoir à lancer le workflow.
# ──────────────────────────────────────────────────────────────
try:
    from server import PromptServer
    from aiohttp import web

    @PromptServer.instance.routes.post("/orion4d/bus/clear")
    async def _route_bus_clear(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        mode = data.get("mode", "all")
        variable_name = data.get("variable_name", "")
        before = len(_ORION_BUS)
        _do_clear(mode, variable_name)
        after = len(_ORION_BUS)
        print(f"🧹 [Bus CLEAR via UI] mode={mode} — {before} → {after} (seq={_BUS_SEQ})")
        return web.json_response({"ok": True, "before": before, "after": after, "seq": _BUS_SEQ})
except Exception as _e:
    print(f"⚠️ [Variable Bus] Route HTTP non enregistrée : {_e}")


NODE_CLASS_MAPPINGS = {
    "PyCodeMax_BusSet": PyCodeMax_BusSet,
    "PyCodeMax_BusGet": PyCodeMax_BusGet,
    "PyCodeMax_BusClear": PyCodeMax_BusClear,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "PyCodeMax_BusSet": "🚌 Variable Bus (Set)",
    "PyCodeMax_BusGet": "🚌 Variable Bus (Get)",
    "PyCodeMax_BusClear": "🧹 Variable Bus (Clear)",
}
# --- END OF FILE variable_bus.py ---