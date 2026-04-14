# --- START OF FILE text_input.py ---
class PyCodeMax_TextInput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": "Your text here..."}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "get_text"
    CATEGORY = "Orion4D_MetaNode/UI Widgets"

    def get_text(self, text):
        return (text,)

NODE_CLASS_MAPPINGS = {"PyCodeMax_TextInput": PyCodeMax_TextInput}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_TextInput": "📝 Text Input"}
# --- END OF FILE text_input.py ---