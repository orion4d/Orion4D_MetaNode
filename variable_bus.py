# --- START OF FILE variable_bus.py ---
# v2 : fix cache BusGet + libération VRAM à chaque remplacement.
from collections import OrderedDict

_ORION_BUS: "OrderedDict[str, object]" = OrderedDict()
_BUS_MAX_ENTRIES = 64
_BUS_SEQ = 0

try:
    from comfy_execution.graph import ExecutionBlocker
    _HAS_BLOCKER = True
except ImportError:
    _HAS_BLOCKER = False


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
        old = _ORION_BUS[name]
        _ORION_BUS.move_to_end(name)
        del old
        _empty_cuda_cache()
    _ORION_BUS[name] = value
    _BUS_SEQ += 1
    while len(_ORION_BUS) > _BUS_MAX_ENTRIES:
        k, _ = _ORION_BUS.popitem(last=False)
        print(f"🚌 [Bus] Éviction FIFO de '{k}'")
        _empty_cuda_cache()


class PyCodeMax_BusSet:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"input": ("*",), "variable_name": ("STRING", {"default": "my_var"})}}
    RETURN_TYPES = ("*", "INT")
    RETURN_NAMES = ("passthrough", "sync")
    FUNCTION = "bus_set"
    CATEGORY = "Orion4D_MetaNode/Bus"
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def bus_set(self, input, variable_name):
        _bus_set(variable_name, input)
        print(f"🚌 [Bus SET] '{variable_name}' <= {type(input).__name__} (seq={_BUS_SEQ})")
        return {"ui": {}, "result": (input, _BUS_SEQ)}


class PyCodeMax_BusGet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"variable_name": ("STRING", {"default": "my_var"})},
            "optional": {"dependency": ("INT", {"forceInput": True})}
        }
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("output",)
    FUNCTION = "bus_get"
    CATEGORY = "Orion4D_MetaNode/Bus"

    @classmethod
    def IS_CHANGED(cls, variable_name, dependency=None, **kwargs):
        return float("nan")

    def bus_get(self, variable_name, dependency=None):
        value = _ORION_BUS.get(variable_name, None)
        if value is None:
            print(f"⚠️ [Bus GET] '{variable_name}' introuvable")
            if _HAS_BLOCKER:
                return (ExecutionBlocker(f"[Variable Bus] '{variable_name}' non défini."),)
            raise ValueError(f"[Variable Bus] '{variable_name}' introuvable.")
        _ORION_BUS.move_to_end(variable_name)
        print(f"🚌 [Bus GET] '{variable_name}' => {type(value).__name__} (seq={_BUS_SEQ})")
        return (value,)


class PyCodeMax_BusClear:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (["all", "single", "all_except"], {"default": "all"}),
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

    def bus_clear(self, mode, variable_name, trigger=None):
        global _BUS_SEQ
        before = len(_ORION_BUS)
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
        after = len(_ORION_BUS)
        _BUS_SEQ += 1
        print(f"🧹 [Bus CLEAR] mode={mode} — {before} → {after} (seq={_BUS_SEQ})")
        _empty_cuda_cache()
        return {"ui": {}, "result": (after,)}


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