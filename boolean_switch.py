# --- START OF FILE boolean_switch.py ---
class PyCodeMax_BooleanSwitch:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "toggle": ("BOOLEAN", {"default": False, "label_on": "Road B", "label_off": "Road A"}),
            },
            "optional": {
                "road_A": ("*",),
                "road_B": ("*",),
            }
        }

    RETURN_TYPES = ("BOOLEAN", "*",)
    RETURN_NAMES = ("boolean", "selected_item",)
    FUNCTION = "execute_switch"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    def execute_switch(self, toggle, road_A=None, road_B=None):
        selected = road_B if toggle else road_A
        return (toggle, selected,)

NODE_CLASS_MAPPINGS = {"PyCodeMax_BooleanSwitch": PyCodeMax_BooleanSwitch}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_BooleanSwitch": "🔀 Boolean Switch"}
# --- END OF FILE boolean_switch.py ---