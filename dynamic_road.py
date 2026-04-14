# --- START OF FILE dynamic_road.py ---
class PyCodeMax_DynamicRoad:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "selected_index": ("INT", {"default": 1, "min": 1, "max": 99}),
            }
        }
    
    RETURN_TYPES = ("*", "STRING", "STRING")
    RETURN_NAMES = ("selected_output", "text_out", "log_out")
    FUNCTION = "execute"
    CATEGORY = "Orion4D_MetaNode/UI Widgets/Dynamic Widgets"

    def execute(self, selected_index, **kwargs):
        valid_inputs = {k: v for k, v in kwargs.items() if k.startswith("input_")}
        target_key = f"input_{selected_index}"
        
        selected_val = None
        if target_key in valid_inputs:
            selected_val = valid_inputs[target_key]
        elif valid_inputs:
            target_key = list(valid_inputs.keys())[0]
            selected_val = valid_inputs[target_key]

        if isinstance(selected_val, str):
            text_out = selected_val
        else:
            val_type = type(selected_val).__name__ if selected_val is not None else "Vide"
            text_out = f"⚠️ Avertissement : La sortie sélectionnée ({target_key}) n'est pas du texte (Type détecté: {val_type})."

        log_lines = ["=== 🔀 DYNAMIC ROAD LOG ==="]
        log_lines.append(f"• Route active : {target_key}")
        log_lines.append(f"• Type de donnée : {type(selected_val).__name__ if selected_val is not None else 'Aucune'}")
        
        active_ports = sorted([k for k in valid_inputs.keys()])
        log_lines.append(f"• Ports connectés ({len(active_ports)}) : " + ", ".join(active_ports))
        
        if hasattr(selected_val, "shape"): 
            log_lines.append(f"• Dimensions (Shape) : {selected_val.shape}")
        elif isinstance(selected_val, list):
            log_lines.append(f"• Longueur de la liste : {len(selected_val)}")
            
        log_out = "\n".join(log_lines)

        return (selected_val, text_out, log_out)

# --- Enregistrement ---
NODE_CLASS_MAPPINGS = {"PyCodeMax_DynamicRoad": PyCodeMax_DynamicRoad}
NODE_DISPLAY_NAME_MAPPINGS = {"PyCodeMax_DynamicRoad": "🔀 Dynamic Road"}
# --- END OF FILE dynamic_road.py ---