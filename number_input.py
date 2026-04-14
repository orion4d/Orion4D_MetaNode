# --- START OF FILE number_input.py ---
class PyCodeMax_NumberInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "number": ("FLOAT", {"default": 1.0, "min": -999999.0, "max": 999999.0, "step": 0.01, "display": "number"}),
            }
        }

    RETURN_TYPES = ("FLOAT", "INT",)
    RETURN_NAMES = ("float_val", "int_val",)
    FUNCTION = "get_number"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    def get_number(self, number):
        return (number, int(number),)

NODE_CLASS_MAPPINGS = {"PyCodeMax_NumberInput": PyCodeMax_NumberInput}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_NumberInput": "🔢 Number Input"}
# --- END OF FILE number_input.py ---